import re

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from ..ai import AIConfigError, generate_image, generate_text, is_ai_configured, save_data_url_image
from ..extensions import db
from ..material_assets import save_material_upload
from ..material_extract import extract_material_text
from ..models import MaterialPublicidad, Publicacion
from ..publicidad_batch import (
    CREATIVE_STYLES,
    creative_copy_prompt,
    creative_image_prompt,
    generate_posts_from_material,
)
from ..reference_assets import list_reference_images, load_reference_as_data_url, resolve_reference_paths
from ..social_publish import enrich_post_from_content

bp = Blueprint("publicidad", __name__)


def _reference_data_urls(reference_paths):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    urls = []
    for rel in (reference_paths or [])[:2]:
        try:
            urls.append(load_reference_as_data_url(upload_folder, rel))
        except Exception:
            continue
    return urls


def _parse_creative_copy(raw: str) -> dict:
    titulo = ""
    contenido = raw
    hashtags = ""
    idea_visual = ""

    m_titulo = re.search(r"##\s*T[ií]tulo\s*\n+(.+)", raw, re.I)
    if m_titulo:
        titulo = m_titulo.group(1).strip()

    m_copy = re.search(r"##\s*Copy\s*\n+([\s\S]*?)(?=##\s*Hashtags|##\s*Idea visual|$)", raw, re.I)
    if m_copy:
        contenido = m_copy.group(1).strip()

    m_tags = re.search(r"##\s*Hashtags\s*\n+(.+)", raw, re.I)
    if m_tags:
        hashtags = m_tags.group(1).strip()

    m_idea = re.search(r"##\s*Idea visual\s*\n+([\s\S]+)", raw, re.I)
    if m_idea:
        idea_visual = m_idea.group(1).strip()

    return {
        "titulo": titulo or "Post creativo",
        "contenido": contenido or raw,
        "hashtags": hashtags,
        "idea_visual": idea_visual,
    }


@bp.route("/")
def index():
    materiales = MaterialPublicidad.query.order_by(MaterialPublicidad.creado.desc()).limit(8).all()
    total_posts = Publicacion.query.filter(
        Publicacion.origen.in_(["campana_docs", "estudio_creativo"])
    ).count()
    return render_template(
        "publicidad/index.html",
        materiales=materiales,
        total_posts=total_posts,
        ai_configured=is_ai_configured(),
        estilos=CREATIVE_STYLES,
    )


@bp.route("/materiales")
def list_materiales():
    materiales = MaterialPublicidad.query.order_by(MaterialPublicidad.creado.desc()).all()
    return render_template("publicidad/materiales.html", materiales=materiales)


@bp.route("/materiales/subir", methods=["POST"])
def upload_material():
    archivo = request.files.get("archivo")
    titulo = (request.form.get("titulo") or "").strip()
    notas = (request.form.get("notas") or "").strip()

    if not archivo or not archivo.filename:
        flash("Selecciona un archivo PDF o imagen.", "error")
        return redirect(url_for("publicidad.list_materiales"))

    try:
        rel_path, tipo = save_material_upload(archivo, current_app.config["UPLOAD_FOLDER"])
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("publicidad.list_materiales"))

    if not titulo:
        titulo = archivo.filename.rsplit(".", 1)[0][:180]

    texto = extract_material_text(
        current_app.config["UPLOAD_FOLDER"],
        tipo_archivo=tipo,
        rel_path=rel_path,
        notas=notas,
    )

    mat = MaterialPublicidad(
        titulo=titulo,
        archivo_path=rel_path,
        tipo_archivo=tipo,
        texto_extraido=texto,
        notas=notas or None,
    )
    db.session.add(mat)
    db.session.commit()
    flash(f"Material «{titulo}» subido. Ya puedes generar publicaciones.", "success")
    return redirect(url_for("publicidad.material_detail", mid=mat.id))


@bp.route("/materiales/<int:mid>")
def material_detail(mid):
    mat = MaterialPublicidad.query.get_or_404(mid)
    posts = (
        Publicacion.query.filter_by(material_id=mid)
        .order_by(Publicacion.creado.desc())
        .all()
    )
    return render_template(
        "publicidad/material_detail.html",
        material=mat,
        posts=posts,
        ai_configured=is_ai_configured(),
    )


@bp.route("/materiales/<int:mid>/generar", methods=["POST"])
def generate_from_material(mid):
    if not is_ai_configured():
        flash("Configura OPENROUTER_API_KEY u OPENAI_API_KEY para generar con IA.", "error")
        return redirect(url_for("publicidad.material_detail", mid=mid))

    mat = MaterialPublicidad.query.get_or_404(mid)
    plataforma = (request.form.get("plataforma") or "instagram").strip()
    tono = (request.form.get("tono") or "cercano").strip()
    tema_extra = (request.form.get("tema_extra") or "").strip()
    espaciar = bool(request.form.get("espaciar_calendario"))
    generar_imagenes = bool(request.form.get("generar_imagenes"))

    try:
        cantidad = max(10, min(15, int(request.form.get("cantidad") or 12)))
    except ValueError:
        cantidad = 12

    fuente = mat.texto_extraido or mat.notas or ""
    if not fuente.strip():
        flash("El material no tiene texto. Agrega notas o sube otro archivo.", "error")
        return redirect(url_for("publicidad.material_detail", mid=mid))

    try:
        items = generate_posts_from_material(
            texto_fuente=fuente,
            plataforma=plataforma,
            tono=tono,
            cantidad=cantidad,
            tema_extra=tema_extra,
        )
    except (AIConfigError, RuntimeError, Exception) as e:
        flash(f"No se pudieron generar publicaciones: {e}", "error")
        return redirect(url_for("publicidad.material_detail", mid=mid))

    from datetime import datetime, timedelta, time

    images_ok = 0
    created = []
    base = datetime.now() + timedelta(days=1)

    for idx, item in enumerate(items):
        imagen_path = None
        if generar_imagenes and idx < 5:
            try:
                prompt = (
                    f"Imagen para Instagram de tarotista, tema: {item.get('titulo', 'tarot')}. "
                    f"Estética mística elegante, sin texto en la imagen."
                )
                data_url = generate_image(prompt, aspect_ratio="1:1")
                imagen_path = save_data_url_image(
                    data_url, current_app.config["UPLOAD_FOLDER"]
                )
                images_ok += 1
            except Exception:
                pass

        fecha = None
        if espaciar:
            fecha = datetime.combine(base.date() + timedelta(days=idx), time(10, 30))

        p = Publicacion(
            plataforma=plataforma,
            titulo=item.get("titulo") or f"Publicación {idx + 1}",
            contenido=item.get("contenido") or "",
            hashtags=item.get("hashtags") or None,
            estado="programada" if fecha else "borrador",
            fecha_programada=fecha,
            material_id=mid,
            origen="campana_docs",
            formato_creativo=item.get("formato") or item.get("angulo"),
            imagen_path=imagen_path,
        )
        enrich_post_from_content(p)
        db.session.add(p)
        created.append(p)

    mat.publicaciones_generadas = (mat.publicaciones_generadas or 0) + len(created)
    db.session.commit()

    msg = f"Se crearon {len(created)} borradores desde «{mat.titulo}»."
    if generar_imagenes:
        msg += f" Imágenes IA: {images_ok}."
    if espaciar:
        msg += " Quedaron espaciadas en el calendario."
    flash(msg, "success")
    return redirect(url_for("social.index"))


@bp.route("/materiales/<int:mid>/eliminar", methods=["POST"])
def delete_material(mid):
    mat = MaterialPublicidad.query.get_or_404(mid)
    db.session.delete(mat)
    db.session.commit()
    flash("Material eliminado.", "info")
    return redirect(url_for("publicidad.list_materiales"))


@bp.route("/estudio", methods=["GET", "POST"])
def estudio():
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    referencias = list_reference_images(upload_folder)

    if request.method == "POST":
        if not is_ai_configured():
            flash("Configura OPENROUTER_API_KEY para el estudio creativo.", "error")
            return redirect(url_for("publicidad.estudio"))

        estilo = (request.form.get("estilo") or "variacion").strip()
        tema = (request.form.get("tema") or "tarot y espiritualidad").strip()
        plataforma = (request.form.get("plataforma") or "instagram").strip()
        tono = (request.form.get("tono") or "cercano").strip()
        generar_imagen = bool(request.form.get("generar_imagen"))
        cantidad = max(1, min(5, int(request.form.get("cantidad") or 1)))

        selected = resolve_reference_paths(upload_folder, request.form.getlist("referencias"))
        if not selected and referencias:
            flash("Selecciona al menos una foto tuya para el estudio creativo.", "error")
            return redirect(url_for("publicidad.estudio"))

        reference_paths = selected
        created = []

        try:
            for n in range(cantidad):
                raw = generate_text(
                    creative_copy_prompt(
                        estilo=estilo, tema=tema, plataforma=plataforma, tono=tono,
                    )
                    + (f"\n\nVariación #{n + 1}: busca un ángulo distinto." if cantidad > 1 else ""),
                    system="Eres copywriter creativo para tarotista en redes sociales.",
                    temperature=0.9,
                    max_tokens=1200,
                )
                parsed = _parse_creative_copy(raw)
                imagen_path = None

                if generar_imagen:
                    style = CREATIVE_STYLES.get(estilo, CREATIVE_STYLES["variacion"])
                    prompt = creative_image_prompt(
                        estilo=estilo,
                        tema=tema,
                        tono=tono,
                        idea_visual=parsed.get("idea_visual") or tema,
                    )
                    data_url = generate_image(
                        prompt,
                        aspect_ratio=style["aspect"],
                        reference_data_urls=_reference_data_urls(reference_paths),
                    )
                    imagen_path = save_data_url_image(data_url, upload_folder)

                p = Publicacion(
                    plataforma=plataforma,
                    titulo=parsed["titulo"][:180],
                    contenido=parsed["contenido"],
                    hashtags=parsed.get("hashtags") or None,
                    estado="borrador",
                    origen="estudio_creativo",
                    formato_creativo=estilo,
                    imagen_path=imagen_path,
                )
                enrich_post_from_content(p)
                db.session.add(p)
                created.append(p)

            db.session.commit()
            flash(f"Estudio creativo: {len(created)} publicación(es) lista(s).", "success")
            return redirect(url_for("social.index"))

        except (AIConfigError, Exception) as e:
            db.session.rollback()
            flash(f"Error en estudio creativo: {e}", "error")
            return redirect(url_for("publicidad.estudio"))

    return render_template(
        "publicidad/estudio.html",
        referencias=referencias,
        estilos=CREATIVE_STYLES,
        ai_configured=is_ai_configured(),
    )
