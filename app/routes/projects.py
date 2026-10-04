from datetime import datetime, date, timedelta
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from ..extensions import db
from ..models import Proyecto, Tarea, Cliente, Meta, PlanVentas, EstrategiaIA
from ..templates_proyectos import PLANTILLAS
from ..strategy import generate_strategy

bp = Blueprint("projects", __name__)


def _parse_date(s, default=None):
    if not s:
        return default
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return default


@bp.route("/")
def list_projects():
    proyectos = Proyecto.query.order_by(Proyecto.creado.desc()).all()
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template("projects/list.html", proyectos=proyectos,
                           plantillas=PLANTILLAS, clientes=clientes)


@bp.route("/i-d")
def rd_projects():
    """Portafolio interno I+D — no visible en el sitio público."""
    try:
        from data.content import build_rd_project_categories

        categories = build_rd_project_categories()
    except ImportError:
        categories = []
    return render_template("projects/rd.html", categories=categories)


@bp.route("/desde_plantilla", methods=["POST"])
def from_template():
    key = request.form.get("plantilla")
    plt = PLANTILLAS.get(key)
    if not plt:
        flash("Plantilla no encontrada", "error")
        return redirect(url_for("projects.list_projects"))
    inicio = _parse_date(request.form.get("fecha_inicio"), date.today())
    cliente_id = request.form.get("cliente_id") or None
    nombre = request.form.get("nombre") or plt["nombre"]
    p = Proyecto(
        nombre=nombre,
        descripcion=plt["descripcion"],
        cliente_id=cliente_id,
        estado="planificación",
        fecha_inicio=inicio,
        fecha_fin=inicio + timedelta(days=plt["duracion_dias"]),
    )
    db.session.add(p)
    db.session.flush()
    for nombre_t, offset, dur in plt["tareas"]:
        db.session.add(Tarea(
            proyecto_id=p.id, nombre=nombre_t,
            fecha_inicio=inicio + timedelta(days=offset),
            fecha_fin=inicio + timedelta(days=offset + dur),
            progreso=0,
        ))
    db.session.commit()
    flash(f"Proyecto creado desde plantilla '{plt['nombre']}'", "success")
    return redirect(url_for("projects.detail", pid=p.id))


@bp.route("/nuevo", methods=["GET", "POST"])
def new_project():
    if request.method == "POST":
        p = Proyecto(
            nombre=request.form["nombre"].strip(),
            descripcion=request.form.get("descripcion"),
            cliente_id=request.form.get("cliente_id") or None,
            estado=request.form.get("estado", "planificación"),
            fecha_inicio=_parse_date(request.form.get("fecha_inicio"), date.today()),
            fecha_fin=_parse_date(request.form.get("fecha_fin")),
            presupuesto=float(request.form.get("presupuesto") or 0),
        )
        db.session.add(p)
        db.session.commit()
        flash("Proyecto creado", "success")
        return redirect(url_for("projects.detail", pid=p.id))
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template("projects/form.html", proyecto=None, clientes=clientes)


@bp.route("/<int:pid>")
def detail(pid):
    p = Proyecto.query.get_or_404(pid)
    return render_template("projects/detail.html", p=p)


@bp.route("/<int:pid>/editar", methods=["GET", "POST"])
def edit_project(pid):
    p = Proyecto.query.get_or_404(pid)
    if request.method == "POST":
        p.nombre = request.form["nombre"].strip()
        p.descripcion = request.form.get("descripcion")
        p.cliente_id = request.form.get("cliente_id") or None
        p.estado = request.form.get("estado", p.estado)
        p.fecha_inicio = _parse_date(request.form.get("fecha_inicio"), p.fecha_inicio)
        p.fecha_fin = _parse_date(request.form.get("fecha_fin"), p.fecha_fin)
        p.presupuesto = float(request.form.get("presupuesto") or 0)
        db.session.commit()
        flash("Proyecto actualizado", "success")
        return redirect(url_for("projects.detail", pid=p.id))
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template("projects/form.html", proyecto=p, clientes=clientes)


@bp.route("/<int:pid>/eliminar", methods=["POST"])
def delete_project(pid):
    p = Proyecto.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    flash("Proyecto eliminado", "info")
    return redirect(url_for("projects.list_projects"))


# ---------------- Tareas ----------------
@bp.route("/<int:pid>/tareas/nueva", methods=["POST"])
def new_task(pid):
    p = Proyecto.query.get_or_404(pid)
    t = Tarea(
        proyecto_id=p.id,
        nombre=request.form["nombre"].strip(),
        fecha_inicio=_parse_date(request.form.get("fecha_inicio"), date.today()),
        fecha_fin=_parse_date(request.form.get("fecha_fin"), date.today()),
        progreso=int(request.form.get("progreso") or 0),
        dependencias=request.form.get("dependencias") or None,
    )
    db.session.add(t)
    db.session.commit()
    flash("Tarea agregada", "success")
    return redirect(url_for("projects.detail", pid=p.id))


@bp.route("/tareas/<int:tid>/eliminar", methods=["POST"])
def delete_task(tid):
    t = Tarea.query.get_or_404(tid)
    pid = t.proyecto_id
    db.session.delete(t)
    db.session.commit()
    return redirect(url_for("projects.detail", pid=pid))


@bp.route("/<int:pid>/gantt.json")
def gantt_json(pid):
    p = Proyecto.query.get_or_404(pid)
    data = []
    for t in p.tareas:
        data.append({
            "id": str(t.id),
            "name": t.nombre,
            "start": t.fecha_inicio.isoformat(),
            "end": t.fecha_fin.isoformat(),
            "progress": t.progreso or 0,
            "dependencies": t.dependencias or "",
        })
    return jsonify(data)


@bp.route("/tareas/<int:tid>/actualizar", methods=["POST"])
def update_task(tid):
    """Endpoint para que el Gantt actualice fechas/progreso al arrastrar."""
    t = Tarea.query.get_or_404(tid)
    data = request.get_json(silent=True) or {}
    if "start" in data:
        t.fecha_inicio = _parse_date(data["start"], t.fecha_inicio)
    if "end" in data:
        t.fecha_fin = _parse_date(data["end"], t.fecha_fin)
    if "progress" in data:
        try:
            t.progreso = int(data["progress"])
        except (TypeError, ValueError):
            pass
    db.session.commit()
    return {"ok": True}


# =================================================================
# WIZARD GUIADO
# =================================================================
@bp.route("/wizard", methods=["GET"])
def wizard():
    clientes = Cliente.query.order_by(Cliente.nombre).all()
    return render_template("projects/wizard.html",
                           clientes=clientes,
                           plantillas=PLANTILLAS,
                           today=date.today().isoformat())


@bp.route("/wizard/preview_estrategia", methods=["POST"])
def wizard_preview():
    """Genera la estrategia recomendada en base a lo que lleva el wizard."""
    d = request.get_json(silent=True) or {}
    plataformas = [p for p in (d.get("plataformas") or "").split(",") if p]
    contenido = generate_strategy(
        tipo=d.get("tipo") or "otro",
        nombre=d.get("nombre") or "Proyecto",
        objetivo=d.get("objetivo") or "",
        usa_redes=bool(d.get("usa_redes")),
        plataformas=plataformas,
        frecuencia=int(d.get("frecuencia") or 0),
        tiene_ventas=bool(d.get("tiene_ventas")),
        precio=float(d.get("precio") or 0),
        unidades_meta=int(d.get("unidades_meta") or 0),
        canales=d.get("canales") or "",
        conversion=float(d.get("conversion") or 0),
    )
    return {"ok": True, "contenido": contenido}


@bp.route("/wizard", methods=["POST"])
def wizard_save():
    f = request.form
    nombre = f.get("nombre", "").strip()
    if not nombre:
        flash("El nombre del proyecto es obligatorio", "error")
        return redirect(url_for("projects.wizard"))

    fi = _parse_date(f.get("fecha_inicio"), date.today())
    ff = _parse_date(f.get("fecha_fin"))
    plataformas_list = f.getlist("plataformas")
    usa_redes = f.get("usa_redes") == "1"
    tiene_ventas = f.get("tiene_ventas") == "1"

    p = Proyecto(
        nombre=nombre,
        descripcion=f.get("descripcion") or None,
        cliente_id=int(f.get("cliente_id")) if f.get("cliente_id") else None,
        estado="planificación",
        fecha_inicio=fi,
        fecha_fin=ff,
        presupuesto=float(f.get("presupuesto") or 0),
        tipo=f.get("tipo") or "otro",
        objetivo=f.get("objetivo") or None,
        usa_redes=usa_redes,
        plataformas_redes=",".join(plataformas_list) if plataformas_list else None,
        frecuencia_posts=int(f.get("frecuencia") or 0),
    )
    db.session.add(p)
    db.session.flush()

    # Tareas: desde plantilla o manual
    plantilla_key = f.get("plantilla")
    if plantilla_key and plantilla_key in PLANTILLAS:
        plt = PLANTILLAS[plantilla_key]
        if not ff:
            p.fecha_fin = fi + timedelta(days=plt["duracion_dias"])
        for nombre_t, offset, dur in plt["tareas"]:
            db.session.add(Tarea(
                proyecto_id=p.id, nombre=nombre_t,
                fecha_inicio=fi + timedelta(days=offset),
                fecha_fin=fi + timedelta(days=offset + dur),
                progreso=0,
            ))

    # Meta principal
    meta_nombre = f.get("meta_nombre")
    meta_valor = f.get("meta_valor")
    if meta_nombre and meta_valor:
        try:
            db.session.add(Meta(
                proyecto_id=p.id,
                nombre=meta_nombre,
                valor_objetivo=float(meta_valor),
                unidad=f.get("meta_unidad") or "",
            ))
        except ValueError:
            pass

    # Plan de ventas
    if tiene_ventas:
        db.session.add(PlanVentas(
            proyecto_id=p.id,
            precio_unitario=float(f.get("precio") or 0),
            unidades_meta=int(f.get("unidades_meta") or 0),
            canales=",".join(f.getlist("canales")),
            conversion_estimada=float(f.get("conversion") or 0),
            notas=f.get("plan_notas") or None,
        ))

    # Estrategia
    estrategia_md = f.get("estrategia_contenido")
    if estrategia_md:
        db.session.add(EstrategiaIA(
            proyecto_id=p.id,
            contenido=estrategia_md,
            fuente="heurística",
        ))

    db.session.commit()
    flash(f"Proyecto '{p.nombre}' creado con asistente guiado ✓", "success")
    return redirect(url_for("projects.detail", pid=p.id))
