"""Blueprint comercial Mi Gestor — ventas SaaS."""
import json
import os
import uuid
from datetime import date, datetime, timedelta
from io import StringIO

from flask import (
    Blueprint, Response, current_app, flash, redirect, render_template,
    request, session, url_for,
)

from ..commercial.commissions import calcular_comisiones_venta, get_config
from ..commercial.constants import (
    COMISION_ESTADOS, MENSAJE_CANALES, MENSAJE_ETAPAS, PIPELINE_COLORS,
    PIPELINE_ESTADOS, PRIORIDADES, PRODUCT_IMPORT_META, PRODUCT_IMPORT_SLUGS,
    PROPUESTA_ESTADOS, TEMPERATURAS, TIPOS_INTERACCION, VENTA_ESTADOS_PAGO,
)
from ..commercial.import_preview_store import (
    delete_import_preview, load_import_preview, save_import_preview,
)
from ..commercial.csv_import import (
    ALLOWED_IMPORT_EXTENSIONS, IMPORT_MAX_BYTES,
    parse_import_file, row_to_cliente_fields, validate_import_rows,
)
from ..commercial.messages import render_plantilla, whatsapp_url
from ..commercial.lead_enrichment import enriquecer_cliente
from ..commercial.onboarding_templates import checklist_for_product
from ..extensions import db
from ..models import (
    Cliente, ClienteMaterial, Comision, ConfigComision, Interaccion,
    MaterialComercial, Onboarding, OnboardingItem, PlantillaMensaje,
    ProductoCatalogo, PropuestaComercial, SaasCuenta, Venta,
)
from ..commercial.saas_constants import SAAS_PORTAL_LABELS, SAAS_PORTAL_SLUGS, portal_acceso_url
from ..commercial.saas_provision import (
    create_saas_cuenta,
    create_saas_cuenta_rapido,
    generate_password,
    portal_slug_from_producto,
)

bp = Blueprint("commercial", __name__)

IMPORT_PREVIEW_ID_KEY = "import_preview_id"
IMPORT_SESSION_KEY = "csv_import_preview"  # legacy — ya no guardar datos aquí


def _clear_legacy_import_session():
    """Quita datos viejos de importación que inflaban la cookie de sesión."""
    session.pop(IMPORT_SESSION_KEY, None)


def _resolve_preview_id():
    return request.form.get("preview_id") or request.args.get("preview_id") or session.get(IMPORT_PREVIEW_ID_KEY)


def _load_pending_import():
    preview_id = _resolve_preview_id()
    if not preview_id:
        return None, None
    data = load_import_preview(preview_id)
    return preview_id, data


def _vendedor():
    return session.get("crm_user") or "equipo"


def _parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(s.strip()[:10], fmt).date()
        except ValueError:
            continue
    return None


def _productos_activos():
    return ProductoCatalogo.query.filter_by(activo=True).order_by(ProductoCatalogo.nombre).all()


def _import_context(slug=None, producto_form=None):
    producto_default = PRODUCT_IMPORT_SLUGS.get(slug) if slug else producto_form
    meta = PRODUCT_IMPORT_META.get(slug, {}) if slug else {}
    return producto_default, meta.get("fuente"), meta.get("nicho_default")


# ---------- Importación CSV / Excel ----------

@bp.route("/importar")
@bp.route("/importar/<slug>")
def importar(slug=None):
    _clear_legacy_import_session()
    producto_default = PRODUCT_IMPORT_SLUGS.get(slug) if slug else None
    return render_template(
        "commercial/importar.html",
        slug=slug,
        producto_default=producto_default,
        product_slugs=PRODUCT_IMPORT_SLUGS,
    )


@bp.route("/importar/preview", methods=["POST"])
def importar_preview(slug=None):
    slug = request.form.get("slug") or slug
    producto_default, fuente_default, nicho_default = _import_context(
        slug, request.form.get("producto_default")
    )
    f = request.files.get("archivo")
    if not f or not f.filename:
        flash("Selecciona un archivo CSV o Excel.", "error")
        return redirect(url_for("commercial.importar", slug=slug))

    ext = os.path.splitext(f.filename.lower())[1]
    if ext not in ALLOWED_IMPORT_EXTENSIONS:
        flash("Solo archivos .csv o .xlsx", "error")
        return redirect(url_for("commercial.importar", slug=slug))

    raw = f.read()
    if len(raw) > IMPORT_MAX_BYTES:
        flash("Archivo demasiado grande (máx. 15 MB).", "error")
        return redirect(url_for("commercial.importar", slug=slug))

    parsed = parse_import_file(raw, f.filename, request.form.get("delimiter") or None)
    validation = validate_import_rows(
        parsed["rows"], producto_default,
        fuente_default=fuente_default,
        nicho_default=nicho_default,
    )

    _clear_legacy_import_session()
    old_id = session.pop(IMPORT_PREVIEW_ID_KEY, None)
    if old_id:
        delete_import_preview(old_id)

    preview_id = save_import_preview({
        "producto_default": producto_default,
        "fuente_default": fuente_default,
        "nicho_default": nicho_default,
        "validation": {
            "valid": [{"line": v["line"], "fields": v["fields"]} for v in validation["valid"]],
            "duplicates": [
                {"line": d["line"], "fields": d["fields"], "dup_id": d["duplicate"].id}
                for d in validation["duplicates"]
            ],
            "errors": validation["errors"],
        },
        "meta": {
            "encoding": parsed["encoding"],
            "delimiter": parsed["delimiter"],
            "headers": parsed["headers"],
            "row_count": len(parsed["rows"]),
        },
    })
    session[IMPORT_PREVIEW_ID_KEY] = preview_id

    return render_template(
        "commercial/importar_preview.html",
        meta=parsed,
        validation=validation,
        producto_default=producto_default,
        slug=slug,
        preview_id=preview_id,
    )


@bp.route("/importar/ejecutar", methods=["POST"])
def importar_ejecutar():
    preview_id, data = _load_pending_import()
    if not data:
        _clear_legacy_import_session()
        flash("No hay importación pendiente. Vuelve a subir el archivo.", "error")
        return redirect(url_for("commercial.importar"))

    policy = request.form.get("duplicate_policy", "skip")
    imported = updated = skipped = 0
    v = data["validation"]

    def _apply(fields, existing=None):
        nonlocal imported, updated
        if existing and policy == "skip":
            return
        if existing and policy == "update":
            for k, val in fields.items():
                if val is not None and hasattr(existing, k):
                    setattr(existing, k, val)
            existing.actualizado = datetime.utcnow()
            updated += 1
            return
        c = Cliente(**{k: val for k, val in fields.items() if hasattr(Cliente, k)})
        db.session.add(c)
        imported += 1

    for item in v["valid"]:
        _apply(item["fields"])

    for item in v["duplicates"]:
        if policy == "skip":
            skipped += 1
            continue
        if policy == "create":
            _apply(item["fields"])
            continue
        dup = Cliente.query.get(item["dup_id"])
        _apply(item["fields"], dup)

    db.session.commit()
    if preview_id:
        delete_import_preview(preview_id)
    session.pop(IMPORT_PREVIEW_ID_KEY, None)
    _clear_legacy_import_session()
    flash(f"Importación lista: {imported} nuevos, {updated} actualizados, {skipped} omitidos.", "success")
    return redirect(url_for("commercial.pipeline"))


@bp.route("/importar/errores.csv")
def importar_errores_csv():
    preview_id, data = _load_pending_import()
    if not data:
        flash("No hay importación pendiente.", "error")
        return redirect(url_for("commercial.importar"))
    buf = StringIO()
    buf.write("linea,error\n")
    for e in data["validation"]["errors"]:
        buf.write(f'{e["line"]},"{e["reason"]}"\n')
    return Response(buf.getvalue(), mimetype="text/csv", headers={
        "Content-Disposition": "attachment; filename=errores_importacion.csv"
    })


# ---------- Pipeline Kanban ----------

@bp.route("/pipeline")
def pipeline():
    q = Cliente.query.filter_by(activo=True)
    producto = request.args.get("producto")
    nicho = request.args.get("nicho")
    prioridad = request.args.get("prioridad")
    responsable = request.args.get("responsable")
    buscar = request.args.get("q", "").strip()

    if producto:
        q = q.filter(Cliente.producto_interes == producto)
    if nicho:
        q = q.filter(Cliente.nicho == nicho)
    if prioridad:
        q = q.filter(Cliente.prioridad == prioridad)
    if responsable:
        q = q.filter(Cliente.responsable == responsable)
    if buscar:
        like = f"%{buscar}%"
        q = q.filter(db.or_(
            Cliente.nombre.ilike(like), Cliente.empresa.ilike(like),
            Cliente.instagram.ilike(like), Cliente.whatsapp.ilike(like),
        ))

    clientes = q.order_by(Cliente.actualizado.desc()).all()
    columns = {est: [] for est in PIPELINE_ESTADOS}
    for c in clientes:
        est = c.estado_pipeline or "Nuevo"
        if est not in columns:
            est = "Nuevo"
        columns[est].append(c)

    return render_template(
        "commercial/pipeline.html",
        columns=columns,
        estados=PIPELINE_ESTADOS,
        colors=PIPELINE_COLORS,
        productos=_productos_activos(),
        prioridades=PRIORIDADES,
        filtros=request.args,
    )


@bp.route("/pipeline/mover", methods=["POST"])
def pipeline_mover():
    data = request.get_json(silent=True) or {}
    cid = data.get("cliente_id")
    estado = data.get("estado") or data.get("estado_pipeline")
    if not cid or estado not in PIPELINE_ESTADOS:
        return {"ok": False}, 400
    c = Cliente.query.get_or_404(int(cid))
    c.estado_pipeline = estado
    c.actualizado = datetime.utcnow()
    db.session.commit()
    return {"ok": True}


# ---------- Seguimientos ----------

@bp.route("/seguimientos")
def seguimientos():
    hoy = date.today()
    en_7 = hoy + timedelta(days=7)
    base = Cliente.query.filter_by(activo=True)

    vencidos = base.filter(
        Cliente.fecha_proximo_seguimiento != None,
        Cliente.fecha_proximo_seguimiento < hoy,
        ~Cliente.estado_pipeline.in_(["Cerrado ganado", "Cerrado perdido"]),
    ).order_by(Cliente.fecha_proximo_seguimiento).all()

    hoy_list = base.filter(Cliente.fecha_proximo_seguimiento == hoy).all()
    proximos = base.filter(
        Cliente.fecha_proximo_seguimiento > hoy,
        Cliente.fecha_proximo_seguimiento <= en_7,
    ).order_by(Cliente.fecha_proximo_seguimiento).all()
    sin_fecha = base.filter(
        Cliente.fecha_proximo_seguimiento == None,
        ~Cliente.estado_pipeline.in_(["Cerrado ganado", "Cerrado perdido"]),
    ).limit(30).all()

    return render_template(
        "commercial/seguimientos.html",
        vencidos=vencidos, hoy_list=hoy_list, proximos=proximos, sin_fecha=sin_fecha, hoy=hoy,
    )


@bp.route("/seguimientos/<int:cid>/hecho", methods=["POST"])
def seguimiento_hecho(cid):
    c = Cliente.query.get_or_404(cid)
    c.fecha_ultimo_contacto = datetime.utcnow()
    nueva_fecha = _parse_date(request.form.get("proxima_fecha"))
    c.fecha_proximo_seguimiento = nueva_fecha
    c.proxima_accion = request.form.get("proxima_accion") or c.proxima_accion
    i = Interaccion(
        cliente_id=c.id, tipo="seguimiento", canal="seguimiento",
        resumen=request.form.get("resumen") or "Seguimiento realizado",
        proxima_accion=c.proxima_accion, proxima_fecha=nueva_fecha,
        usuario_responsable=_vendedor(),
    )
    db.session.add(i)
    db.session.commit()
    flash("Seguimiento registrado.", "success")
    return redirect(url_for("commercial.seguimientos"))


# ---------- Mensajes ----------

@bp.route("/mensajes")
def mensajes():
    producto = request.args.get("producto")
    q = PlantillaMensaje.query.filter_by(activo=True)
    if producto:
        q = q.filter_by(producto=producto)
    plantillas = q.order_by(PlantillaMensaje.producto, PlantillaMensaje.etapa).all()
    return render_template(
        "commercial/mensajes.html",
        plantillas=plantillas,
        productos=_productos_activos(),
        etapas=MENSAJE_ETAPAS,
        canales=MENSAJE_CANALES,
        producto_filtro=producto,
    )


@bp.route("/mensajes/<int:cid>/generar")
def mensaje_generar(cid):
    c = Cliente.query.get_or_404(cid)
    etapa = request.args.get("etapa", "primer contacto")
    canal = request.args.get("canal", "WhatsApp")
    plantillas = PlantillaMensaje.query.filter_by(activo=True).order_by(
        PlantillaMensaje.producto, PlantillaMensaje.etapa
    ).all()
    tpl_id = request.args.get("plantilla_id", type=int)
    if tpl_id:
        tpl = PlantillaMensaje.query.get(tpl_id)
    else:
        tpl = PlantillaMensaje.query.filter_by(
            producto=c.producto_interes, etapa=etapa, canal=canal, activo=True,
        ).first()
        if not tpl:
            tpl = PlantillaMensaje.query.filter_by(etapa=etapa, canal=canal, activo=True).first()
    texto = render_plantilla(tpl.cuerpo, c, vendedora=_vendedor()) if tpl else ""
    wa = whatsapp_url(c, texto) if canal == "WhatsApp" else None
    return render_template(
        "commercial/mensaje_preview.html",
        cliente=c, mensaje=texto, wa_url=wa, plantilla=tpl, plantillas=plantillas,
    )


# ---------- Propuestas ----------

@bp.route("/propuestas")
def propuestas_list():
    estado = request.args.get("estado")
    q = PropuestaComercial.query
    if estado:
        q = q.filter_by(estado=estado)
    propuestas = q.order_by(PropuestaComercial.creado.desc()).all()
    return render_template(
        "commercial/propuestas_list.html",
        propuestas=propuestas,
        estados=PROPUESTA_ESTADOS,
        estado_filtro=estado,
    )


@bp.route("/propuestas/nueva/<int:cid>", methods=["GET", "POST"])
@bp.route("/propuestas/nueva/<int:cid>/<int:pid>", methods=["GET", "POST"])
def propuesta_form(cid, pid=None):
    c = Cliente.query.get_or_404(cid)
    p = PropuestaComercial.query.get(pid) if pid else None
    if request.method == "POST":
        if not p:
            p = PropuestaComercial(cliente_id=c.id)
            db.session.add(p)
        p.producto = request.form.get("producto")
        p.plan = request.form.get("plan")
        p.setup = float(request.form.get("setup") or 0)
        p.mensualidad = float(request.form.get("mensualidad") or 0)
        p.descuento_setup = float(request.form.get("descuento_setup") or 0)
        p.descuento_mensualidad = float(request.form.get("descuento_mensualidad") or 0)
        p.duracion_minima = int(request.form.get("duracion_minima") or 0)
        p.fecha_vencimiento = _parse_date(request.form.get("fecha_vencimiento"))
        p.estado = request.form.get("estado", "borrador")
        p.condiciones = request.form.get("condiciones")
        p.observaciones = request.form.get("observaciones")
        p.incluye = request.form.get("incluye")
        if p.estado == "enviada" and c.estado_pipeline not in ("Cerrado ganado",):
            c.estado_pipeline = "Propuesta enviada"
        db.session.commit()
        flash("Propuesta guardada.", "success")
        return redirect(url_for("commercial.propuesta_form", cid=c.id, pid=p.id))

    producto_obj = None
    planes = []
    if c.producto_interes:
        producto_obj = ProductoCatalogo.query.filter_by(nombre=c.producto_interes).first()
        if producto_obj and producto_obj.planes_json:
            planes = json.loads(producto_obj.planes_json)

    return render_template(
        "commercial/propuesta_form.html",
        cliente=c, propuesta=p, productos=_productos_activos(),
        planes=planes, estados=PROPUESTA_ESTADOS,
    )


@bp.route("/propuestas/<int:pid>/pdf")
def propuesta_pdf(pid):
    from ..commercial.proposal_pdf import build_propuesta_pdf
    p = PropuestaComercial.query.get_or_404(pid)
    pdf_bytes = build_propuesta_pdf(p, vendedora=_vendedor())
    return Response(pdf_bytes, mimetype="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="propuesta_{pid}.pdf"'
    })


# ---------- Ventas ----------

@bp.route("/ventas")
def ventas_list():
    ventas = Venta.query.order_by(Venta.fecha_cierre.desc()).all()
    return render_template("commercial/ventas_list.html", ventas=ventas)


@bp.route("/ventas/desde-propuesta/<int:pid>", methods=["GET", "POST"])
def venta_desde_propuesta(pid):
    prop = PropuestaComercial.query.get_or_404(pid)
    c = prop.cliente
    if request.method == "POST":
        v = Venta(
            cliente_id=c.id, propuesta_id=prop.id, producto=prop.producto, plan=prop.plan,
            setup_cobrado=float(request.form.get("setup_cobrado") or prop.setup or 0),
            mensualidad_cobrada=float(request.form.get("mensualidad_cobrada") or prop.mensualidad or 0),
            monto_total_primer_pago=float(request.form.get("monto_total_primer_pago") or 0),
            fecha_cierre=_parse_date(request.form.get("fecha_cierre")) or date.today(),
            fecha_pago=_parse_date(request.form.get("fecha_pago")),
            estado_pago=request.form.get("estado_pago", "pendiente"),
            metodo_pago=request.form.get("metodo_pago"),
            observaciones=request.form.get("observaciones"),
            vendedor=_vendedor(),
        )
        if not v.monto_total_primer_pago:
            v.monto_total_primer_pago = v.setup_cobrado + v.mensualidad_cobrada
        db.session.add(v)
        prop.estado = "aceptada"
        c.estado_pipeline = "Cerrado ganado"
        c.tipo_registro = "cliente"
        c.estado = "activo"
        db.session.flush()

        if v.estado_pago == "pagado":
            for com in calcular_comisiones_venta(v, _vendedor()):
                db.session.add(com)

        items = checklist_for_product(prop.producto or "")
        ob = Onboarding(cliente_id=c.id, venta_id=v.id, producto=prop.producto)
        db.session.add(ob)
        db.session.flush()
        for i, titulo in enumerate(items):
            db.session.add(OnboardingItem(onboarding_id=ob.id, titulo=titulo, orden=i))

        db.session.add(Interaccion(
            cliente_id=c.id, tipo="onboarding", canal="venta",
            resumen=f"Venta cerrada: {prop.producto} — {prop.plan}",
            usuario_responsable=_vendedor(),
        ))
        db.session.commit()
        flash("Venta registrada. Onboarding y comisiones creados.", "success")
        slug = portal_slug_from_producto(prop.producto)
        if slug and v.estado_pago == "pagado":
            flash(
                f"Activa el portal del cliente en: Cuentas SaaS (o desde la ficha del cliente).",
                "info",
            )
        return redirect(url_for("commercial.ventas_list"))

    return render_template(
        "commercial/venta_form.html", propuesta=prop, cliente=c,
        estados_pago=VENTA_ESTADOS_PAGO,
    )


# ---------- Comisiones ----------

@bp.route("/comisiones")
def comisiones_list():
    mes = request.args.get("mes")
    estado = request.args.get("estado")
    q = Comision.query
    if estado:
        q = q.filter_by(estado=estado)
    if mes:
        try:
            y, m = map(int, mes.split("-"))
            q = q.filter(db.extract("month", Comision.fecha_generacion) == m)
        except ValueError:
            pass
    comisiones = q.order_by(Comision.fecha_generacion.desc()).all()
    cfg = get_config()
    total_pendiente = sum(x.monto_comision for x in comisiones if x.estado == "pendiente")
    total_aprobada = sum(x.monto_comision for x in comisiones if x.estado == "aprobada")
    hoy = date.today()
    total_pagada_mes = sum(
        x.monto_comision for x in comisiones
        if x.estado == "pagada" and x.fecha_pago and x.fecha_pago.month == hoy.month
    )
    return render_template(
        "commercial/comisiones_list.html",
        comisiones=comisiones, cfg=cfg,
        totales={
            "pendiente": total_pendiente,
            "aprobada": total_aprobada,
            "pagada_mes": total_pagada_mes,
        },
        filtros=request.args,
        estados=COMISION_ESTADOS,
    )


@bp.route("/comisiones/<int:cid>/pagar", methods=["POST"])
def comision_pagar(cid):
    com = Comision.query.get_or_404(cid)
    com.estado = "pagada"
    com.fecha_pago = date.today()
    db.session.commit()
    flash("Comisión marcada como pagada.", "success")
    return redirect(url_for("commercial.comisiones_list"))


@bp.route("/comisiones/config", methods=["GET", "POST"])
def comisiones_config():
    cfg = get_config()
    if request.method == "POST":
        cfg.porcentaje_base = float(request.form.get("porcentaje_base") or 50)
        cfg.porcentaje_alto_ticket = float(request.form.get("porcentaje_alto_ticket") or 30)
        cfg.umbral_alto_ticket = float(request.form.get("umbral_alto_ticket") or 500000)
        cfg.acumula_alto_ticket = bool(request.form.get("acumula_alto_ticket"))
        db.session.commit()
        flash("Configuración actualizada.", "success")
    return render_template("commercial/comisiones_config.html", cfg=cfg)


# ---------- Onboarding ----------

@bp.route("/onboarding")
def onboarding_list():
    obs = Onboarding.query.order_by(Onboarding.creado.desc()).all()
    return render_template("commercial/onboarding_list.html", onboardings=obs)


@bp.route("/onboarding/<int:oid>")
def onboarding_detail(oid):
    ob = Onboarding.query.get_or_404(oid)
    items = OnboardingItem.query.filter_by(onboarding_id=oid).order_by(OnboardingItem.orden).all()
    return render_template("commercial/onboarding_detail.html", onboarding=ob, items=items)


@bp.route("/onboarding/item/<int:iid>/toggle", methods=["POST"])
def onboarding_toggle(iid):
    item = OnboardingItem.query.get_or_404(iid)
    nuevo = request.form.get("estado")
    if nuevo in ("pendiente", "en_proceso", "en proceso", "listo"):
        item.estado = "en proceso" if nuevo == "en_proceso" else nuevo
    else:
        ciclo = {"pendiente": "en proceso", "en proceso": "listo", "listo": "pendiente"}
        item.estado = ciclo.get(item.estado, "listo")
    db.session.commit()
    return redirect(url_for("commercial.onboarding_detail", oid=item.onboarding_id))


# ---------- Materiales ----------

@bp.route("/materiales")
def materiales_list():
    mats = MaterialComercial.query.filter_by(activo=True).order_by(MaterialComercial.creado.desc()).all()
    return render_template("commercial/materiales_list.html", materiales=mats, productos=_productos_activos())


@bp.route("/materiales/subir", methods=["POST"])
def materiales_subir():
    f = request.files.get("archivo")
    nombre = request.form.get("nombre") or (f.filename if f else "Material")
    rel_path = None
    if f and f.filename:
        ext = os.path.splitext(f.filename)[1].lower()
        folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "comercial")
        os.makedirs(folder, exist_ok=True)
        fn = f"{datetime.utcnow():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}{ext}"
        f.save(os.path.join(folder, fn))
        rel_path = f"comercial/{fn}"
    m = MaterialComercial(
        nombre=nombre, producto=request.form.get("producto"),
        tipo=request.form.get("tipo", "otro"),
        archivo_path=rel_path, link_externo=request.form.get("link_externo"),
        descripcion=request.form.get("descripcion"),
    )
    db.session.add(m)
    db.session.commit()
    flash("Material guardado.", "success")
    return redirect(url_for("commercial.materiales_list"))


# ---------- Reporte semanal ----------

@bp.route("/reporte-semanal")
def reporte_semanal():
    hoy = date.today()
    inicio = hoy - timedelta(days=hoy.weekday())
    fin = inicio + timedelta(days=6)

    nuevos = Cliente.query.filter(Cliente.creado >= datetime.combine(inicio, datetime.min.time())).count()
    contactados = Interaccion.query.filter(Interaccion.fecha >= datetime.combine(inicio, datetime.min.time())).count()
    demos = Cliente.query.filter(
        Cliente.estado_pipeline.in_(["Demo agendada", "Demo realizada"]),
        Cliente.actualizado >= datetime.combine(inicio, datetime.min.time()),
    ).count()
    propuestas = PropuestaComercial.query.filter(
        PropuestaComercial.creado >= datetime.combine(inicio, datetime.min.time()),
        PropuestaComercial.estado.in_(["enviada", "aceptada"]),
    ).count()
    ventas = Venta.query.filter(Venta.fecha_cierre >= inicio, Venta.fecha_cierre <= fin).all()
    monto = sum(v.monto_total_primer_pago or 0 for v in ventas)
    mrr = sum(v.mensualidad_cobrada or 0 for v in ventas)
    comisiones = Comision.query.filter(
        Comision.fecha_generacion >= datetime.combine(inicio, datetime.min.time()),
    ).all()
    com_total = sum(c.monto_comision for c in comisiones)

    reporte = {
        "inicio": inicio, "fin": fin,
        "leads_nuevos": nuevos, "contactos": contactados, "demos": demos,
        "propuestas": propuestas, "ventas_count": len(ventas),
        "monto_vendido": monto, "mrr_nuevo": mrr, "comisiones": com_total,
    }
    texto = _reporte_texto(reporte)
    return render_template("commercial/reporte_semanal.html", reporte=reporte, texto=texto, stats=reporte)


def _reporte_texto(r):
    return f"""Reporte semanal Mi Gestor
Semana: {r['inicio'].strftime('%d/%m')} – {r['fin'].strftime('%d/%m/%Y')}

Leads nuevos: {r['leads_nuevos']}
Contactos realizados: {r['contactos']}
Demos: {r['demos']}
Propuestas enviadas: {r['propuestas']}
Ventas cerradas: {r['ventas_count']}
Monto vendido: ${r['monto_vendido']:,.0f}
MRR nuevo: ${r['mrr_nuevo']:,.0f}
Comisiones generadas: ${r['comisiones']:,.0f}
Próximas acciones: Revisar pipeline y seguimientos vencidos."""


# ---------- Ficha comercial extendida (API rápida) ----------

@bp.route("/cliente/<int:cid>/enriquecer", methods=["POST"])
def cliente_enriquecer(cid):
    c = Cliente.query.get_or_404(cid)
    sug = enriquecer_cliente(c)
    for k, val in sug.items():
        if val and hasattr(c, k):
            setattr(c, k, val)
    c.actualizado = datetime.utcnow()
    db.session.commit()
    flash("Sugerencias comerciales aplicadas (prioridad, dolor, plan, mensaje).", "success")
    return redirect(url_for("clients.detail", cid=c.id))


@bp.route("/cliente/<int:cid>/interaccion-rapida", methods=["POST"])
def interaccion_rapida(cid):
    c = Cliente.query.get_or_404(cid)
    i = Interaccion(
        cliente_id=c.id,
        tipo=request.form.get("tipo", "WhatsApp"),
        canal=request.form.get("tipo", "WhatsApp"),
        resumen=request.form.get("resumen", "").strip() or "Contacto",
        resultado=request.form.get("resultado"),
        proxima_accion=request.form.get("proxima_accion"),
        proxima_fecha=_parse_date(request.form.get("proxima_fecha")),
        usuario_responsable=_vendedor(),
    )
    c.fecha_ultimo_contacto = datetime.utcnow()
    c.fecha_proximo_seguimiento = i.proxima_fecha
    c.proxima_accion = i.proxima_accion
    if c.estado_pipeline == "Nuevo":
        c.estado_pipeline = "Contactado"
    db.session.add(i)
    db.session.commit()
    return redirect(request.referrer or url_for("commercial.pipeline"))


# ---------- Cuentas SaaS (clientes pagadores) ----------

@bp.route("/saas/rapido", methods=["GET", "POST"])
@bp.route("/saas/rapido/<int:cid>", methods=["GET", "POST"])
def saas_rapido(cid=None):
    """Alta directa: portal + email, sin pipeline ni prospecto."""
    cliente = Cliente.query.get(cid) if cid else None
    if request.method == "POST":
        try:
            cuenta, plain, meta, cliente, cliente_nuevo = create_saas_cuenta_rapido(
                portal_slug=request.form.get("portal_slug", ""),
                nombre_negocio=request.form.get("nombre_negocio", ""),
                email=request.form.get("email", ""),
                password=request.form.get("password") or None,
                plan=request.form.get("plan"),
                notas=request.form.get("notas"),
                telefono=request.form.get("telefono"),
                cliente_id=int(request.form["cliente_id"]) if request.form.get("cliente_id") else None,
                send_email=request.form.get("send_email") == "1",
                vendedor=_vendedor(),
            )
            db.session.commit()
            url = portal_acceso_url(cuenta.portal_slug)
            parts = []
            if cliente_nuevo:
                parts.append("Ficha CRM creada automáticamente.")
            if meta.get("email_sent"):
                parts.append(f"Correo enviado a {cuenta.email}.")
            else:
                parts.append(f"Acceso: {url} · Usuario: {cuenta.email} · Clave: {plain}")
            flash(" ".join(parts), "success")
            return redirect(url_for("commercial.saas_detalle", sid=cuenta.id))
        except ValueError as exc:
            flash(str(exc), "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Error al crear cuenta: {exc}", "danger")

    sugerido_slug = portal_slug_from_producto(cliente.producto_interes if cliente else None)
    return render_template(
        "commercial/saas_rapido.html",
        cliente=cliente,
        portales=SAAS_PORTAL_SLUGS,
        labels=SAAS_PORTAL_LABELS,
        sugerido_slug=sugerido_slug,
        password_sugerida=generate_password(),
    )


@bp.route("/saas")
def saas_list():
    portal = request.args.get("portal")
    q = SaasCuenta.query.filter_by(activo=True)
    if portal:
        q = q.filter_by(portal_slug=portal)
    cuentas = q.order_by(SaasCuenta.creado.desc()).all()
    return render_template(
        "commercial/saas_list.html",
        cuentas=cuentas,
        portales=SAAS_PORTAL_SLUGS,
        labels=SAAS_PORTAL_LABELS,
        portal_filter=portal,
    )


@bp.route("/saas/nuevo", methods=["GET", "POST"])
@bp.route("/saas/nuevo/<int:cid>", methods=["GET", "POST"])
def saas_nuevo(cid=None):
    cliente = Cliente.query.get(cid) if cid else None
    if request.method == "POST":
        cid_form = request.form.get("cliente_id") or cid
        if not cid_form:
            flash("Selecciona un cliente del CRM.", "danger")
            return redirect(url_for("commercial.saas_nuevo"))
        try:
            cuenta, plain, meta = create_saas_cuenta(
                cliente_id=int(cid_form),
                portal_slug=request.form.get("portal_slug", ""),
                nombre_negocio=request.form.get("nombre_negocio", ""),
                email=request.form.get("email", ""),
                password=request.form.get("password") or None,
                plan=request.form.get("plan"),
                notas=request.form.get("notas"),
                send_email=request.form.get("send_email") == "1",
                vendedor=_vendedor(),
            )
            db.session.commit()
            url = portal_acceso_url(cuenta.portal_slug)
            if meta.get("email_sent"):
                flash(f"Cuenta creada y correo enviado a {cuenta.email}.", "success")
            else:
                flash(
                    f"Cuenta creada. Acceso: {url} — Usuario: {cuenta.email} — Clave: {plain}",
                    "success",
                )
            return redirect(url_for("commercial.saas_detalle", sid=cuenta.id))
        except ValueError as exc:
            flash(str(exc), "danger")
        except Exception as exc:
            db.session.rollback()
            flash(f"Error al crear cuenta: {exc}", "danger")

    sugerido_slug = portal_slug_from_producto(cliente.producto_interes if cliente else None)
    return render_template(
        "commercial/saas_form.html",
        cliente=cliente,
        clientes=Cliente.query.filter_by(activo=True).order_by(Cliente.nombre).limit(500).all(),
        portales=SAAS_PORTAL_SLUGS,
        labels=SAAS_PORTAL_LABELS,
        sugerido_slug=sugerido_slug,
        password_sugerida=generate_password(),
    )


@bp.route("/saas/<int:sid>")
def saas_detalle(sid):
    from ..models_commercial import SaasHerramientaRegistro

    cuenta = SaasCuenta.query.get_or_404(sid)
    registros = (
        SaasHerramientaRegistro.query.filter_by(saas_cuenta_id=sid)
        .order_by(SaasHerramientaRegistro.actualizado.desc())
        .limit(40)
        .all()
    )
    alertas = [r for r in registros if r.estado in ("alerta", "campana_pendiente")]
    return render_template(
        "commercial/saas_detalle.html",
        cuenta=cuenta,
        acceso_url=portal_acceso_url(cuenta.portal_slug),
        registros=registros,
        alertas_count=len(alertas),
    )
