from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..extensions import db
from ..models import Cliente, Interaccion
from ..tenancy import audit

bp = Blueprint("clients", __name__)

CAMPOS = [
    "nombre", "empresa", "rut", "email", "telefono", "direccion",
    "instagram", "linkedin", "facebook", "estado", "fuente", "notas",
    "tipo_registro", "nombre_contacto", "cargo_contacto", "nicho", "producto_interes",
    "comuna", "ciudad", "region", "tiktok", "sitio_web", "whatsapp",
    "prioridad", "temperatura", "estado_pipeline", "dolor_detectado", "motivo_encaje",
    "plan_sugerido", "proxima_accion", "responsable", "mensaje_sugerido", "tags",
]
CAMPOS_NUM = ["setup_estimado", "mensualidad_estimada", "monto_oportunidad", "probabilidad_cierre"]
CAMPOS_FECHA = ["fecha_proximo_seguimiento", "fecha_primer_contacto"]


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


@bp.route("/")
def list_clients():
    q = request.args.get("q", "").strip()
    query = Cliente.query
    if q:
        like = f"%{q}%"
        query = query.filter(db.or_(Cliente.nombre.ilike(like),
                                    Cliente.empresa.ilike(like),
                                    Cliente.email.ilike(like)))
    clientes = query.order_by(Cliente.creado.desc()).all()
    return render_template("clients/list.html", clientes=clientes, q=q)


def _apply_form(c, form):
    for f in CAMPOS:
        setattr(c, f, form.get(f) or None)
    for f in CAMPOS_NUM:
        val = form.get(f)
        setattr(c, f, float(val) if val else None)
    for f in CAMPOS_FECHA:
        setattr(c, f, _parse_date(form.get(f)))


@bp.route("/nuevo", methods=["GET", "POST"])
def new_client():
    if request.method == "POST":
        c = Cliente()
        _apply_form(c, request.form)
        db.session.add(c)
        db.session.flush()
        audit("alta_cliente", "cliente", c.id, c.nombre)
        db.session.commit()
        flash("Cliente creado", "success")
        return redirect(url_for("clients.detail", cid=c.id))
    return render_template("clients/form.html", cliente=None)


@bp.route("/<int:cid>")
def detail(cid):
    c = Cliente.query.get_or_404(cid)
    interacciones = Interaccion.query.filter_by(cliente_id=cid).order_by(Interaccion.fecha.desc()).all()
    return render_template("clients/detail.html", c=c, interacciones=interacciones)


@bp.route("/<int:cid>/editar", methods=["GET", "POST"])
def edit_client(cid):
    c = Cliente.query.get_or_404(cid)
    if request.method == "POST":
        _apply_form(c, request.form)
        db.session.commit()
        flash("Cliente actualizado", "success")
        return redirect(url_for("clients.detail", cid=c.id))
    return render_template("clients/form.html", cliente=c)


@bp.route("/<int:cid>/eliminar", methods=["POST"])
def delete_client(cid):
    c = Cliente.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    flash("Cliente eliminado", "info")
    return redirect(url_for("clients.list_clients"))


@bp.route("/<int:cid>/interaccion", methods=["POST"])
def add_interaction(cid):
    c = Cliente.query.get_or_404(cid)
    i = Interaccion(
        cliente_id=c.id,
        canal=request.form.get("canal"),
        tipo=request.form.get("canal"),
        resumen=request.form["resumen"].strip(),
        proxima_accion=request.form.get("proxima_accion") or None,
        proxima_fecha=_parse_date(request.form.get("proxima_fecha")),
    )
    c.fecha_ultimo_contacto = datetime.utcnow()
    c.fecha_proximo_seguimiento = i.proxima_fecha
    c.proxima_accion = i.proxima_accion
    if c.estado_pipeline == "Nuevo":
        c.estado_pipeline = "Contactado"
    db.session.add(i)
    db.session.commit()
    flash("Interacción registrada", "success")
    return redirect(url_for("clients.detail", cid=c.id))


@bp.route("/interaccion/<int:iid>/eliminar", methods=["POST"])
def delete_interaction(iid):
    i = Interaccion.query.get_or_404(iid)
    cid = i.cliente_id
    db.session.delete(i)
    db.session.commit()
    return redirect(url_for("clients.detail", cid=cid))
