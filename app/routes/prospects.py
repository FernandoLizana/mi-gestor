import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..extensions import db
from ..models import Cliente, Interaccion, ProspectoIA
from ..outreach import generate_outreach_draft
from ..ai import AIConfigError, generate_text, is_ai_configured
from ..instagram_profiles import (
    build_profile_url,
    fetch_profile_snapshot,
    normalize_instagram_handle,
    parse_handles_bulk,
)
from ..prospect_helpers import append_contact_log, PROSPECT_ESTADOS

bp = Blueprint("prospects", __name__)


def _analysis_prompt(p):
    return f"""Analiza este prospecto para una prospección ética y personalizada.

Nombre: {p.nombre or 'No especificado'}
Plataforma: {p.plataforma or 'No especificada'}
Perfil: {p.perfil_url or 'No especificado'}
Bio: {p.bio or 'No proporcionada'}
Publicaciones/señales: {p.publicaciones or 'No proporcionadas'}
Objetivo del contacto: {p.objetivo or 'No especificado'}
Oferta/propuesta: {p.oferta or 'No especificada'}

Devuelve en Markdown:
## Perfil resumido
## Señales de interés
## Ángulo recomendado
## Objeciones probables
## Primer mensaje sugerido
## Seguimiento recomendado

No inventes datos. Si falta información, indícalo."""


def _tarot_message_prompt(p):
    return f"""Eres copywriter especialista en venta ética de servicios espirituales para una tarotista.

Objetivo: crear un primer DM corto, cálido y personalizado para Instagram.

Datos del perfil:
- Nombre: {p.nombre or 'No especificado'}
- Perfil: {p.perfil_url or 'No especificado'}
- Bio: {p.bio or 'No especificada'}
- Señales de publicaciones recientes: {p.publicaciones or 'No disponibles'}

Datos de la oferta:
- Objetivo de contacto: {p.objetivo or 'No especificado'}
- Oferta tarotista: {p.oferta or 'Lectura de tarot personalizada'}
- Tono deseado: {p.tono or 'cercano'}

Devuelve SOLO:
1) Mensaje principal (máx. 650 caracteres)
2) Variante alternativa breve (máx. 350 caracteres)

Reglas:
- Personaliza sin inventar hechos.
- Nada de manipulación, miedo o promesas absolutas.
- Cierre con pregunta suave y CTA de respuesta."""


@bp.route("/")
def list_prospects():
    estado = request.args.get("estado")
    q = ProspectoIA.query
    if estado:
        q = q.filter_by(estado=estado)
    prospectos = q.order_by(ProspectoIA.creado.desc()).all()
    clientes_count = Cliente.query.count()
    return render_template(
        "prospects/list.html",
        prospectos=prospectos,
        estado=estado,
        clientes_count=clientes_count,
    )


@bp.route("/instagram/lote", methods=["GET", "POST"])
def import_instagram_bulk():
    if request.method == "POST":
        raw = request.form.get("handles", "")
        objetivo = request.form.get("objetivo") or "Conectar con potencial clienta para lectura de tarot"
        oferta = request.form.get("oferta") or "Lectura de tarot personalizada"
        tono = request.form.get("tono") or "cercano"
        auto_scan = bool(request.form.get("auto_scan"))

        handles = parse_handles_bulk(raw)
        if not handles:
            flash("No encontré perfiles válidos. Ingresa @usuario o URL por línea.", "error")
            return redirect(url_for("prospects.import_instagram_bulk"))

        created = 0
        scanned = 0
        failed = 0
        for handle in handles:
            p = ProspectoIA(
                nombre=f"@{handle}",
                plataforma="instagram",
                perfil_url=build_profile_url(handle),
                objetivo=objetivo,
                oferta=oferta,
                tono=tono,
            )

            if auto_scan:
                snap = fetch_profile_snapshot(handle)
                if snap.get("bio"):
                    p.bio = snap["bio"]
                if snap.get("posts"):
                    p.publicaciones = "\n".join(f"- {x}" for x in snap["posts"])
                    scanned += 1
                elif snap.get("error"):
                    p.publicaciones = f"(No se pudo extraer automáticamente: {snap['error']})"
                    failed += 1
            db.session.add(p)
            created += 1

        db.session.commit()
        flash(
            f"Importados {created} perfiles. Escaneados: {scanned}. Con error de extracción: {failed}.",
            "success",
        )
        return redirect(url_for("prospects.list_prospects"))

    return render_template("prospects/import_instagram.html")


@bp.route("/nuevo", methods=["GET", "POST"])
def new_prospect():
    if request.method == "POST":
        p = ProspectoIA(
            nombre=request.form.get("nombre") or None,
            plataforma=request.form.get("plataforma") or None,
            perfil_url=request.form.get("perfil_url") or None,
            bio=request.form.get("bio") or None,
            publicaciones=request.form.get("publicaciones") or None,
            objetivo=request.form.get("objetivo") or None,
            oferta=request.form.get("oferta") or None,
            tono=request.form.get("tono") or "cercano",
        )
        db.session.add(p)
        db.session.commit()
        flash("Prospecto creado", "success")
        return redirect(url_for("prospects.detail", pid=p.id))
    return render_template("prospects/form.html", p=None)


@bp.route("/<int:pid>")
def detail(pid):
    p = ProspectoIA.query.get_or_404(pid)
    return render_template("prospects/detail.html", p=p, ai_configured=is_ai_configured())


@bp.route("/<int:pid>/editar", methods=["GET", "POST"])
def edit_prospect(pid):
    p = ProspectoIA.query.get_or_404(pid)
    if request.method == "POST":
        for field in ("nombre", "plataforma", "perfil_url", "bio", "publicaciones", "objetivo", "oferta", "tono", "estado"):
            setattr(p, field, request.form.get(field) or None)
        if not p.tono:
            p.tono = "cercano"
        if not p.estado:
            p.estado = "nuevo"
        db.session.commit()
        flash("Prospecto actualizado", "success")
        return redirect(url_for("prospects.detail", pid=p.id))
    return render_template("prospects/form.html", p=p)


@bp.route("/<int:pid>/scan_instagram", methods=["POST"])
def scan_instagram(pid):
    p = ProspectoIA.query.get_or_404(pid)
    if (p.plataforma or "").lower() != "instagram":
        flash("Este escaneo está pensado para perfiles de Instagram.", "error")
        return redirect(url_for("prospects.detail", pid=p.id))

    handle = normalize_instagram_handle(p.perfil_url or p.nombre or "")
    if not handle:
        flash("No se pudo determinar el usuario de Instagram.", "error")
        return redirect(url_for("prospects.detail", pid=p.id))

    snap = fetch_profile_snapshot(handle)
    if snap.get("bio"):
        p.bio = snap["bio"]
    if snap.get("posts"):
        p.publicaciones = "\n".join(f"- {x}" for x in snap["posts"])
        db.session.commit()
        flash("Señales de publicaciones actualizadas.", "success")
    else:
        db.session.commit()
        flash(f"No se pudieron extraer publicaciones: {snap.get('error', 'sin detalle')}", "error")
    return redirect(url_for("prospects.detail", pid=p.id))


@bp.route("/<int:pid>/analizar", methods=["POST"])
def analyze(pid):
    p = ProspectoIA.query.get_or_404(pid)
    if not is_ai_configured():
        flash("Configura OPENROUTER_API_KEY u OPENAI_API_KEY para usar IA", "error")
        return redirect(url_for("prospects.detail", pid=p.id))
    try:
        p.analisis = generate_text(
            _analysis_prompt(p),
            system="Eres un analista senior de prospección B2B/B2C ética. Responde en español claro y accionable.",
            temperature=0.65,
            max_tokens=1400,
        )
        p.estado = "analizado"
        db.session.commit()
        flash("Análisis IA generado", "success")
    except (AIConfigError, Exception) as e:
        db.session.rollback()
        flash(f"No se pudo generar el análisis: {e}", "error")
    return redirect(url_for("prospects.detail", pid=p.id))


@bp.route("/<int:pid>/mensaje", methods=["POST"])
def draft_message(pid):
    p = ProspectoIA.query.get_or_404(pid)
    if is_ai_configured():
        try:
            p.mensaje = generate_text(
                _tarot_message_prompt(p),
                system=(
                    "Eres especialista en mensajes de prospección por Instagram para una tarotista. "
                    "Tu estilo es humano, respetuoso y orientado a conversación real."
                ),
                temperature=0.8,
                max_tokens=700,
            )
        except (AIConfigError, Exception):
            p.mensaje = generate_outreach_draft(
                nombre=p.nombre,
                plataforma=p.plataforma,
                perfil_url=p.perfil_url,
                bio=p.bio,
                publicaciones=p.publicaciones,
                objetivo=p.objetivo,
                oferta=p.oferta,
                tono=p.tono or "cercano",
            )
    else:
        p.mensaje = generate_outreach_draft(
            nombre=p.nombre,
            plataforma=p.plataforma,
            perfil_url=p.perfil_url,
            bio=p.bio,
            publicaciones=p.publicaciones,
            objetivo=p.objetivo,
            oferta=p.oferta,
            tono=p.tono or "cercano",
        )
    if p.estado in ("nuevo", "analizado"):
        p.estado = "mensaje_generado"
    append_contact_log(p, "Mensaje IA generado", p.mensaje)
    db.session.commit()
    flash("Mensaje generado", "success")
    return redirect(url_for("prospects.detail", pid=p.id))


@bp.route("/<int:pid>/convertir", methods=["POST"])
def convert_to_client(pid):
    p = ProspectoIA.query.get_or_404(pid)
    c = Cliente(
        nombre=p.nombre or "Prospecto sin nombre",
        empresa=p.nombre,
        instagram=p.perfil_url if p.plataforma == "instagram" else None,
        linkedin=p.perfil_url if p.plataforma == "linkedin" else None,
        estado="prospecto",
        estado_pipeline="Nuevo",
        tipo_registro="prospecto",
        fuente=p.plataforma or "Prospectos IA",
        notas=p.analisis,
        mensaje_sugerido=p.mensaje,
    )
    db.session.add(c)
    db.session.flush()
    if p.mensaje:
        db.session.add(Interaccion(
            cliente_id=c.id,
            canal=p.plataforma or "otro",
            resumen=f"Borrador inicial generado desde Prospectos IA:\n\n{p.mensaje}",
        ))
    p.estado = "convertido"
    db.session.commit()
    flash("Prospecto convertido a cliente", "success")
    return redirect(url_for("clients.detail", cid=c.id))


@bp.route("/<int:pid>/marcar_contactado", methods=["POST"])
def mark_contacted(pid):
    p = ProspectoIA.query.get_or_404(pid)
    nota = (request.form.get("nota") or "DM enviado manualmente").strip()
    append_contact_log(p, nota, p.mensaje)
    if p.estado in ("nuevo", "analizado", "mensaje_generado"):
        p.estado = "contactado"
    db.session.commit()
    flash("Contacto registrado.", "success")
    return redirect(url_for("prospects.detail", pid=p.id))


@bp.route("/importar/csv", methods=["GET", "POST"])
def import_csv():
    if request.method == "POST":
        f = request.files.get("archivo")
        if not f or not f.filename:
            flash("Selecciona un archivo CSV.", "error")
            return redirect(url_for("prospects.import_csv"))
        try:
            text = f.stream.read().decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            created = 0
            for row in reader:
                handle = (
                    row.get("instagram") or row.get("usuario") or row.get("handle")
                    or row.get("perfil") or row.get("url") or ""
                ).strip()
                h = normalize_instagram_handle(handle)
                if not h:
                    continue
                p = ProspectoIA(
                    nombre=f"@{h}",
                    plataforma="instagram",
                    perfil_url=build_profile_url(h),
                    objetivo=row.get("objetivo") or "Conectar para lectura de tarot",
                    oferta=row.get("oferta") or "Lectura de tarot personalizada",
                )
                db.session.add(p)
                created += 1
            db.session.commit()
            flash(f"Importados {created} prospectos desde CSV.", "success")
            return redirect(url_for("prospects.list_prospects"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error leyendo CSV: {e}", "error")
    return render_template("prospects/import_csv.html")


@bp.route("/<int:pid>/eliminar", methods=["POST"])
def delete(pid):
    p = ProspectoIA.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash("Prospecto eliminado", "info")
    return redirect(url_for("prospects.list_prospects"))
