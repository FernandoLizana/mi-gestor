from datetime import datetime, date, timedelta, time
import os
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from ..extensions import db
from ..models import Publicacion, TareaSocial, MetricaTikTok, MetricaInstagram, Proyecto
from ..ai import AIConfigError, generate_text, generate_image, save_data_url_image, is_ai_configured
from ..reference_assets import (
    list_reference_images,
    save_reference_upload,
    delete_reference,
    load_reference_as_data_url,
    resolve_reference_paths,
    REF_SUBFOLDER,
)
from ..social_publish import caption_body, full_caption, hashtags_only, platform_upload_url, platform_tips, enrich_post_from_content
from ..brand_settings import CONTENT_TEMPLATES, template_by_key, brand_signature

bp = Blueprint("social", __name__)


def _parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _content_prompt_tarot(*, tema, plataforma, tono, formato, cantidad):
    return f"""Actúa como estratega de contenidos para una tarotista.

Genera {cantidad} ideas de contenido para {plataforma} en español.
Tema central: {tema}
Tono: {tono}
Formato preferido: {formato}

Devuelve en Markdown:
## Idea 1
- Título:
- Guion breve:
- CTA:
- Hashtags:

Repite el mismo formato por cada idea.
Enfócate en contenido útil, ético, espiritual y vendible sin caer en promesas absolutas."""


def _aspect_for_formato(formato):
    if formato in ("reel", "story"):
        return "9:16"
    if formato == "carrusel":
        return "4:5"
    return "1:1"


def _tarot_image_prompt(*, tema, tono, formato, titulo=None, with_references=False):
    titulo_txt = titulo or tema
    ref_hint = (
        " Usa las fotos de referencia adjuntas como inspiración de estilo, colores, "
        "ambiente y servicios de la tarotista. No copies rostros literalmente."
        if with_references else ""
    )
    return (
        f"Imagen para Instagram de tarotista, tema: {tema}. "
        f"Título visual: {titulo_txt}. Tono {tono}, formato {formato}. "
        "Estética mística elegante: cartas de tarot, luna, velas, tonos violeta/dorado, "
        f"sin texto escrito en la imagen, alta calidad.{ref_hint}"
    )


def _reference_data_urls(reference_paths):
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    urls = []
    for rel in (reference_paths or [])[:3]:
        try:
            urls.append(load_reference_as_data_url(upload_folder, rel))
        except Exception:
            continue
    return urls


def _generate_and_save_tarot_image(*, tema, tono, formato, titulo=None, reference_paths=None):
    refs = reference_paths or []
    prompt = _tarot_image_prompt(
        tema=tema, tono=tono, formato=formato, titulo=titulo, with_references=bool(refs),
    )
    data_url = generate_image(
        prompt,
        aspect_ratio=_aspect_for_formato(formato),
        reference_data_urls=_reference_data_urls(refs),
    )
    return save_data_url_image(data_url, current_app.config["UPLOAD_FOLDER"])


@bp.route("/calendario")
def calendar():
    return render_template("social/calendar.html")


@bp.route("/calendario.json")
def calendar_json():
    pubs = Publicacion.query.filter(Publicacion.fecha_programada != None).all()
    colors = {"instagram": "#E1306C", "linkedin": "#0A66C2",
              "facebook": "#1877F2", "tiktok": "#000000"}
    out = []
    for p in pubs:
        out.append({
            "id": p.id,
            "title": f"[{p.plataforma}] {p.titulo or '(sin título)'}",
            "start": p.fecha_programada.isoformat(),
            "url": url_for("social.edit_post", pid=p.id),
            "backgroundColor": colors.get(p.plataforma, "#666"),
            "borderColor": colors.get(p.plataforma, "#666"),
            "extendedProps": {"estado": p.estado},
        })
    return out


@bp.route("/publicaciones/<int:pid>/reprogramar", methods=["POST"])
def reschedule_post(pid):
    p = Publicacion.query.get_or_404(pid)
    data = request.get_json(silent=True) or {}
    nueva = _parse_dt(data.get("start"))
    if nueva:
        p.fecha_programada = nueva
        if p.estado == "borrador":
            p.estado = "programada"
        db.session.commit()
        return {"ok": True}
    return {"ok": False}, 400


def _selected_references_from_form():
    upload_folder = current_app.config["UPLOAD_FOLDER"]
    selected = request.form.getlist("referencias")
    if request.form.get("usar_todas_referencias"):
        return [x["rel_path"] for x in list_reference_images(upload_folder)]
    return resolve_reference_paths(upload_folder, selected)


def _sort_pendientes(posts):
    def key(p):
        if p.fecha_programada and p.estado != "publicada":
            return (0, p.fecha_programada)
        return (1, p.creado or datetime.utcnow())
    return sorted(posts, key=key)


@bp.route("/")
def index():
    pubs = Publicacion.query.order_by(Publicacion.creado.desc()).all()
    pendientes = _sort_pendientes([p for p in pubs if p.estado != "publicada"])
    publicadas = [p for p in pubs if p.estado == "publicada"]
    tareas = TareaSocial.query.order_by(TareaSocial.completada,
                                        TareaSocial.fecha).all()
    refs = list_reference_images(current_app.config["UPLOAD_FOLDER"])
    hoy = date.today()
    inicio = datetime.combine(hoy, time.min)
    fin = datetime.combine(hoy, time.max)
    pubs_hoy = [p for p in pendientes if p.fecha_programada and inicio <= p.fecha_programada <= fin]

    def _platform_stats(plataforma):
        items = [p for p in pubs if p.plataforma == plataforma]
        publicadas_plat = [p for p in items if p.estado == "publicada"]
        return {
            "pendientes": len([p for p in items if p.estado != "publicada"]),
            "publicadas": len(publicadas_plat),
            "likes": sum(p.likes or 0 for p in publicadas_plat),
            "vistas": sum(p.vistas or 0 for p in publicadas_plat),
        }

    ig_metric = MetricaInstagram.query.order_by(MetricaInstagram.fecha.desc()).first()
    tt_metric = MetricaTikTok.query.order_by(MetricaTikTok.fecha.desc()).first()

    return render_template(
        "social/index.html",
        pubs=pubs,
        pendientes=pendientes,
        publicadas=publicadas,
        pubs_hoy=pubs_hoy,
        tareas=tareas,
        referencias=refs,
        plantillas=CONTENT_TEMPLATES,
        brand_signature=brand_signature(),
        ai_configured=is_ai_configured(),
        stats_instagram=_platform_stats("instagram"),
        stats_tiktok=_platform_stats("tiktok"),
        ig_metric=ig_metric,
        tt_metric=tt_metric,
    )


# ----- Publicaciones / Borradores -----
@bp.route("/publicaciones/nueva", methods=["GET", "POST"])
def new_post():
    if request.method == "POST":
        p = Publicacion(
            plataforma=request.form["plataforma"],
            titulo=request.form.get("titulo"),
            contenido=request.form.get("contenido"),
            hashtags=request.form.get("hashtags"),
            fecha_programada=_parse_dt(request.form.get("fecha_programada")),
            estado=request.form.get("estado", "borrador"),
            proyecto_id=request.form.get("proyecto_id") or None,
        )
        db.session.add(p)
        db.session.commit()
        flash("Publicación guardada", "success")
        return redirect(url_for("social.index"))
    proyectos = Proyecto.query.order_by(Proyecto.nombre).all()
    return render_template("social/post_form.html", post=None, proyectos=proyectos)


@bp.route("/publicaciones/<int:pid>", methods=["GET", "POST"])
def edit_post(pid):
    p = Publicacion.query.get_or_404(pid)
    if request.method == "POST":
        p.plataforma = request.form["plataforma"]
        p.titulo = request.form.get("titulo")
        p.contenido = request.form.get("contenido")
        p.hashtags = request.form.get("hashtags")
        p.fecha_programada = _parse_dt(request.form.get("fecha_programada"))
        p.estado = request.form.get("estado", p.estado)
        if p.fecha_programada and p.estado == "borrador":
            p.estado = "programada"
        p.proyecto_id = request.form.get("proyecto_id") or None
        for k in ("vistas", "likes", "comentarios", "compartidos"):
            v = request.form.get(k)
            if v is not None and v != "":
                setattr(p, k, int(v))
        enrich_post_from_content(p)
        db.session.commit()
        flash("Actualizado", "success")
        if request.form.get("after") == "publish" and p.estado != "publicada":
            return redirect(url_for("social.publish_workflow", pid=p.id))
        return redirect(url_for("social.index"))
    proyectos = Proyecto.query.order_by(Proyecto.nombre).all()
    refs = list_reference_images(current_app.config["UPLOAD_FOLDER"])
    return render_template("social/post_form.html", post=p, proyectos=proyectos, referencias=refs)


@bp.route("/publicaciones/<int:pid>/eliminar", methods=["POST"])
def delete_post(pid):
    p = Publicacion.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return redirect(url_for("social.index"))


@bp.route("/publicaciones/<int:pid>/marcar_publicada", methods=["POST"])
def mark_published(pid):
    p = Publicacion.query.get_or_404(pid)
    p.estado = "publicada"
    db.session.commit()
    flash("Marcado como publicado.", "success")
    next_id = request.form.get("next_id")
    if next_id:
        return redirect(url_for("social.publish_workflow", pid=int(next_id)))
    return redirect(request.referrer or url_for("social.index"))


@bp.route("/publicaciones/<int:pid>/programar", methods=["POST"])
def programar_post(pid):
    p = Publicacion.query.get_or_404(pid)
    preset = request.form.get("preset")
    if preset == "manana10":
        d = date.today() + timedelta(days=1)
        p.fecha_programada = datetime.combine(d, time(10, 0))
    elif preset == "en2h":
        p.fecha_programada = datetime.now() + timedelta(hours=2)
    else:
        p.fecha_programada = _parse_dt(request.form.get("fecha_programada"))
    if p.fecha_programada:
        p.estado = "programada"
        db.session.commit()
        flash(f"Programado para {p.fecha_programada.strftime('%d/%m/%Y %H:%M')}", "success")
    else:
        flash("Indica una fecha válida.", "error")
    nxt = request.form.get("next")
    if nxt == "publish":
        return redirect(url_for("social.publish_workflow", pid=p.id))
    return redirect(request.referrer or url_for("social.index"))


@bp.route("/publicaciones/<int:pid>/publicar")
def publish_workflow(pid):
    p = Publicacion.query.get_or_404(pid)
    pendientes = (
        Publicacion.query.filter(Publicacion.estado != "publicada", Publicacion.id != p.id)
        .order_by(Publicacion.fecha_programada.is_(None), Publicacion.fecha_programada)
        .all()
    )
    next_post = pendientes[0] if pendientes else None
    return render_template(
        "social/publicar.html",
        post=p,
        caption_body=caption_body(p.contenido),
        caption_full=full_caption(p.contenido, p.hashtags),
        caption_tags=hashtags_only(p.hashtags, p.contenido),
        upload_url=platform_upload_url(p.plataforma),
        platform_tips=platform_tips(p.plataforma),
        next_post=next_post,
        queue_count=len(pendientes) + 1,
    )


# ----- Tareas sociales (DM, contactar, etc.) -----
@bp.route("/tareas/nueva", methods=["POST"])
def new_task():
    t = TareaSocial(
        plataforma=request.form.get("plataforma"),
        tipo=request.form.get("tipo"),
        objetivo=request.form.get("objetivo"),
        mensaje=request.form.get("mensaje"),
        fecha=_parse_dt(request.form.get("fecha")),
        notas=request.form.get("notas"),
    )
    db.session.add(t)
    db.session.commit()
    flash("Tarea social creada", "success")
    return redirect(url_for("social.index"))


@bp.route("/tareas/<int:tid>/toggle", methods=["POST"])
def toggle_task(tid):
    t = TareaSocial.query.get_or_404(tid)
    t.completada = not t.completada
    db.session.commit()
    return redirect(url_for("social.index"))


@bp.route("/tareas/<int:tid>/eliminar", methods=["POST"])
def delete_task(tid):
    t = TareaSocial.query.get_or_404(tid)
    db.session.delete(t)
    db.session.commit()
    return redirect(url_for("social.index"))


# ----- Métricas Instagram -----
@bp.route("/instagram", methods=["GET", "POST"])
def instagram():
    if request.method == "POST":
        m = MetricaInstagram(
            fecha=datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()
                  if request.form.get("fecha") else date.today(),
            seguidores=int(request.form.get("seguidores") or 0),
            alcance=int(request.form.get("alcance") or 0),
            impresiones=int(request.form.get("impresiones") or 0),
            likes=int(request.form.get("likes") or 0),
            comentarios=int(request.form.get("comentarios") or 0),
            guardados=int(request.form.get("guardados") or 0),
            notas=request.form.get("notas"),
        )
        db.session.add(m)
        db.session.commit()
        flash("Métrica de Instagram registrada", "success")
        return redirect(url_for("social.instagram"))

    metricas = MetricaInstagram.query.order_by(MetricaInstagram.fecha.desc()).all()
    serie = [
        {
            "fecha": m.fecha.isoformat(),
            "seguidores": m.seguidores,
            "alcance": m.alcance,
            "likes": m.likes,
        }
        for m in reversed(metricas)
    ]
    pubs_ig = (
        Publicacion.query.filter_by(plataforma="instagram", estado="publicada")
        .order_by(Publicacion.creado.desc())
        .limit(12)
        .all()
    )
    return render_template(
        "social/instagram.html",
        metricas=metricas,
        serie=serie,
        pubs_ig=pubs_ig,
        hoy=date.today().isoformat(),
    )


@bp.route("/instagram/<int:mid>/eliminar", methods=["POST"])
def delete_instagram(mid):
    m = MetricaInstagram.query.get_or_404(mid)
    db.session.delete(m)
    db.session.commit()
    return redirect(url_for("social.instagram"))


# ----- Métricas TikTok -----
@bp.route("/tiktok", methods=["GET", "POST"])
def tiktok():
    if request.method == "POST":
        m = MetricaTikTok(
            fecha=datetime.strptime(request.form["fecha"], "%Y-%m-%d").date()
                  if request.form.get("fecha") else date.today(),
            seguidores=int(request.form.get("seguidores") or 0),
            vistas_perfil=int(request.form.get("vistas_perfil") or 0),
            vistas_videos=int(request.form.get("vistas_videos") or 0),
            likes=int(request.form.get("likes") or 0),
            comentarios=int(request.form.get("comentarios") or 0),
            compartidos=int(request.form.get("compartidos") or 0),
            notas=request.form.get("notas"),
        )
        db.session.add(m)
        db.session.commit()
        flash("Métrica registrada", "success")
        return redirect(url_for("social.tiktok"))
    metricas = MetricaTikTok.query.order_by(MetricaTikTok.fecha.desc()).all()
    serie = [
        {
            "fecha": m.fecha.isoformat(),
            "seguidores": m.seguidores,
            "vistas": m.vistas_videos,
            "likes": m.likes,
        }
        for m in reversed(metricas)
    ]
    pubs_tt = (
        Publicacion.query.filter_by(plataforma="tiktok", estado="publicada")
        .order_by(Publicacion.creado.desc())
        .limit(12)
        .all()
    )
    return render_template(
        "social/tiktok.html",
        metricas=metricas,
        serie=serie,
        pubs_tt=pubs_tt,
        hoy=date.today().isoformat(),
    )


@bp.route("/ia/generar_contenido", methods=["POST"])
def generate_content():
    if not is_ai_configured():
        flash("Configura OPENROUTER_API_KEY u OPENAI_API_KEY para generación con IA.", "error")
        return redirect(url_for("social.index"))

    tema = (request.form.get("tema") or "").strip()
    plataforma = (request.form.get("plataforma") or "instagram").strip()
    tono = (request.form.get("tono") or "cercano").strip()
    formato = (request.form.get("formato") or "reel").strip()
    modo = (request.form.get("modo") or "semiautomatico").strip()
    generar_imagen = bool(request.form.get("generar_imagen"))
    reference_paths = _selected_references_from_form() if generar_imagen else []
    try:
        cantidad = max(1, min(8, int(request.form.get("cantidad") or 3)))
    except ValueError:
        cantidad = 3

    if not tema:
        flash("Escribe un tema para generar contenido.", "error")
        return redirect(url_for("social.index"))

    try:
        raw = generate_text(
            _content_prompt_tarot(
                tema=tema,
                plataforma=plataforma,
                tono=tono,
                formato=formato,
                cantidad=cantidad,
            ),
            system=(
                "Eres social media manager senior para marca personal de tarot. "
                "Escribes ideas concretas, aplicables y fáciles de publicar."
            ),
            temperature=0.85,
            max_tokens=1600,
        )
    except (AIConfigError, Exception) as e:
        flash(f"No se pudo generar contenido: {e}", "error")
        return redirect(url_for("social.index"))

    created = 0
    images_ok = 0
    if modo == "automatico":
        blocks = [b.strip() for b in raw.split("## Idea") if b.strip()]
        for idx, block in enumerate(blocks[:cantidad], start=1):
            first_line = block.splitlines()[0].strip(" :-#") if block.splitlines() else f"Idea {idx}"
            imagen_path = None
            if generar_imagen:
                try:
                    imagen_path = _generate_and_save_tarot_image(
                        tema=tema,
                        tono=tono,
                        formato=formato,
                        titulo=first_line,
                        reference_paths=reference_paths,
                    )
                    images_ok += 1
                except Exception as e:
                    flash(f"Idea {idx}: no se pudo generar imagen ({e})", "error")
            p = Publicacion(
                plataforma=plataforma,
                titulo=first_line[:180] or f"Idea {idx} {tema[:60]}",
                contenido=f"## Idea {idx}\n{block}",
                hashtags=None,
                estado="borrador",
                imagen_path=imagen_path,
            )
            enrich_post_from_content(p)
            db.session.add(p)
            created += 1
        db.session.commit()
        msg = f"Generé {created} borradores automáticos para {plataforma}."
        if generar_imagen:
            msg += f" Imágenes creadas: {images_ok}."
        flash(msg, "success")
    else:
        imagen_path = None
        if generar_imagen:
            try:
                imagen_path = _generate_and_save_tarot_image(
                    tema=tema, tono=tono, formato=formato,
                    reference_paths=reference_paths,
                )
                images_ok = 1
            except Exception as e:
                flash(f"No se pudo generar imagen: {e}", "error")
        notas = f"Modo semiautomático · formato {formato} · tono {tono}"
        if imagen_path:
            notas += f" · imagen: /uploads/{imagen_path}"
        t = TareaSocial(
            plataforma=plataforma,
            tipo="contenido_ia",
            objetivo=f"Plan de contenido: {tema}",
            mensaje=raw[:1500],
            fecha=datetime.utcnow(),
            notas=notas,
        )
        db.session.add(t)
        db.session.commit()
        msg = "Contenido generado en modo semiautomático (guardado como tarea para edición)."
        if images_ok:
            msg += f" Imagen guardada en /uploads/{imagen_path}."
        flash(msg, "success")
    return redirect(url_for("social.index"))


@bp.route("/publicaciones/<int:pid>/generar_imagen", methods=["POST"])
def generate_post_image(pid):
    if not is_ai_configured():
        flash("Configura OPENROUTER_API_KEY para generar imágenes.", "error")
        return redirect(url_for("social.edit_post", pid=pid))

    p = Publicacion.query.get_or_404(pid)
    tema = (request.form.get("tema") or p.titulo or "tarot espiritual").strip()
    tono = (request.form.get("tono") or "místico").strip()
    formato = (request.form.get("formato") or "post").strip()
    try:
        p.imagen_path = _generate_and_save_tarot_image(
            tema=tema,
            tono=tono,
            formato=formato,
            titulo=p.titulo,
            reference_paths=_selected_references_from_form(),
        )
        db.session.commit()
        flash("Imagen generada y guardada en el borrador.", "success")
    except (AIConfigError, Exception) as e:
        db.session.rollback()
        flash(f"No se pudo generar la imagen: {e}", "error")
    return redirect(url_for("social.edit_post", pid=pid))


@bp.route("/ia/rapido", methods=["POST"])
def quick_generate():
    """1 clic: texto + imagen + borrador listo."""
    if not is_ai_configured():
        flash("Configura OPENROUTER_API_KEY para generación con IA.", "error")
        return redirect(url_for("social.index"))

    tpl = template_by_key(request.form.get("plantilla"))
    tema = (request.form.get("tema_rapido") or "").strip()
    if not tema and tpl:
        tema = tpl["tema"]
    if not tema:
        flash("Escribe un tema o elige una plantilla.", "error")
        return redirect(url_for("social.index"))

    reference_paths = _selected_references_from_form()
    tono = "místico"
    formato = request.form.get("formato") or "post"
    plataforma = (request.form.get("plataforma") or "instagram").strip()
    fecha_prog = _parse_dt(request.form.get("fecha_programada"))
    hashtags_inicial = tpl["hashtags"] if tpl else None

    try:
        raw = generate_text(
            _content_prompt_tarot(
                tema=tema, plataforma=plataforma, tono=tono, formato=formato, cantidad=1,
            ),
            system="Eres social media manager para tarotista. Respuestas cortas y publicables.",
            temperature=0.8,
            max_tokens=700,
        )
        titulo = tema[:180]
        for line in raw.splitlines():
            line = line.strip()
            if line.lower().startswith("- título:") or line.lower().startswith("título:"):
                titulo = line.split(":", 1)[-1].strip()[:180]
                break

        imagen_path = _generate_and_save_tarot_image(
            tema=tema, tono=tono, formato=formato, titulo=titulo,
            reference_paths=reference_paths,
        )
        p = Publicacion(
            plataforma=plataforma,
            titulo=titulo,
            contenido=raw,
            hashtags=hashtags_inicial,
            estado="programada" if fecha_prog else "borrador",
            fecha_programada=fecha_prog,
            imagen_path=imagen_path,
        )
        enrich_post_from_content(p)
        db.session.add(p)
        db.session.commit()
        flash("Post rápido creado: texto + imagen listos para revisar.", "success")
        return redirect(url_for("social.publish_workflow", pid=p.id))
    except (AIConfigError, Exception) as e:
        db.session.rollback()
        flash(f"Generación rápida falló: {e}", "error")
        return redirect(url_for("social.index"))


@bp.route("/imagen", methods=["GET", "POST"])
def imagen_directa():
    refs = list_reference_images(current_app.config["UPLOAD_FOLDER"])
    imagen_path = None
    prompt_usado = None

    if request.method == "POST":
        if not is_ai_configured():
            flash("Configura OPENROUTER_API_KEY para generar imágenes.", "error")
            return redirect(url_for("social.imagen_directa"))

        descripcion = (request.form.get("descripcion") or "").strip()
        formato = (request.form.get("formato") or "post").strip()
        tono = (request.form.get("tono") or "místico").strip()
        if not descripcion:
            flash("Describe qué imagen quieres crear.", "error")
            return redirect(url_for("social.imagen_directa"))

        reference_paths = _selected_references_from_form()
        prompt_usado = _tarot_image_prompt(
            tema=descripcion, tono=tono, formato=formato,
            with_references=bool(reference_paths),
        )
        try:
            imagen_path = _generate_and_save_tarot_image(
                tema=descripcion,
                tono=tono,
                formato=formato,
                reference_paths=reference_paths,
            )
            flash("Imagen creada correctamente.", "success")
        except (AIConfigError, Exception) as e:
            flash(f"No se pudo generar la imagen: {e}", "error")

    return render_template(
        "social/imagen.html",
        referencias=refs,
        imagen_path=imagen_path,
        prompt_usado=prompt_usado,
        ai_configured=is_ai_configured(),
    )


@bp.route("/imagen/guardar_borrador", methods=["POST"])
def imagen_a_borrador():
    imagen_path = (request.form.get("imagen_path") or "").strip()
    titulo = (request.form.get("titulo") or "Imagen IA").strip()[:180]
    if not imagen_path or not imagen_path.startswith("social/"):
        flash("Imagen no válida.", "error")
        return redirect(url_for("social.imagen_directa"))

    p = Publicacion(
        plataforma="instagram",
        titulo=titulo,
        contenido=None,
        estado="borrador",
        imagen_path=imagen_path,
    )
    db.session.add(p)
    db.session.commit()
    flash("Listo para publicar.", "success")
    return redirect(url_for("social.publish_workflow", pid=p.id))


@bp.route("/referencias")
def referencias():
    refs = list_reference_images(current_app.config["UPLOAD_FOLDER"])
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], REF_SUBFOLDER)
    return render_template("social/referencias.html", referencias=refs, folder_abs=folder)


@bp.route("/referencias/subir", methods=["POST"])
def upload_referencia():
    try:
        files = request.files.getlist("fotos")
        saved = 0
        for f in files:
            if not f or not f.filename:
                continue
            save_reference_upload(f, current_app.config["UPLOAD_FOLDER"])
            saved += 1
        if saved:
            flash(f"{saved} foto(s) guardada(s) en referencias.", "success")
        else:
            flash("No se recibieron archivos.", "error")
    except Exception as e:
        flash(f"No se pudo subir: {e}", "error")
    return redirect(url_for("social.referencias"))


@bp.route("/referencias/eliminar", methods=["POST"])
def delete_referencia():
    rel = (request.form.get("rel_path") or "").strip()
    try:
        delete_reference(rel, current_app.config["UPLOAD_FOLDER"])
        flash("Referencia eliminada.", "info")
    except Exception as e:
        flash(f"No se pudo eliminar: {e}", "error")
    return redirect(url_for("social.referencias"))


@bp.route("/tiktok/<int:mid>/eliminar", methods=["POST"])
def delete_tiktok(mid):
    m = MetricaTikTok.query.get_or_404(mid)
    db.session.delete(m)
    db.session.commit()
    return redirect(url_for("social.tiktok"))
