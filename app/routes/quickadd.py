"""Endpoints rápidos (JSON) para crear/buscar sin recargar la página."""
from datetime import datetime, date
from flask import Blueprint, request, jsonify, url_for
from ..extensions import db
from ..models import Cliente, Proyecto, Tarea, Publicacion, TareaSocial, Interaccion
from ..outreach import generate_outreach_draft

bp = Blueprint("quick", __name__)


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _parse_dt(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


@bp.route("/buscar")
def search():
    q = (request.args.get("q") or "").strip()
    if len(q) < 2:
        return jsonify([])
    like = f"%{q}%"
    out = []
    for c in Cliente.query.filter(db.or_(Cliente.nombre.ilike(like),
                                          Cliente.empresa.ilike(like),
                                          Cliente.email.ilike(like))).limit(8):
        out.append({"tipo": "Cliente", "icono": "people",
                    "label": c.nombre + (f" · {c.empresa}" if c.empresa else ""),
                    "url": url_for("clients.detail", cid=c.id)})
    for p in Proyecto.query.filter(Proyecto.nombre.ilike(like)).limit(8):
        out.append({"tipo": "Proyecto", "icono": "kanban",
                    "label": p.nombre + (f" · {p.cliente.nombre}" if p.cliente else ""),
                    "url": url_for("projects.detail", pid=p.id)})
    for pu in Publicacion.query.filter(db.or_(Publicacion.titulo.ilike(like),
                                              Publicacion.contenido.ilike(like))).limit(5):
        out.append({"tipo": f"Post {pu.plataforma}", "icono": "megaphone",
                    "label": (pu.titulo or "(sin título)"),
                    "url": url_for("social.edit_post", pid=pu.id)})
    return jsonify(out)


@bp.route("/cliente", methods=["POST"])
def quick_cliente():
    data = request.get_json(silent=True) or request.form
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return {"ok": False, "error": "Nombre requerido"}, 400
    c = Cliente(
        nombre=nombre,
        empresa=(data.get("empresa") or None),
        telefono=(data.get("telefono") or None),
        email=(data.get("email") or None),
        instagram=(data.get("instagram") or None),
        estado=(data.get("estado") or "prospecto"),
        notas=(data.get("notas") or None),
    )
    db.session.add(c)
    db.session.commit()
    return {"ok": True, "id": c.id, "nombre": c.nombre,
            "url": url_for("clients.detail", cid=c.id)}


@bp.route("/interaccion", methods=["POST"])
def quick_interaccion():
    data = request.get_json(silent=True) or request.form
    cid = data.get("cliente_id")
    if not cid:
        return {"ok": False, "error": "cliente_id requerido"}, 400
    i = Interaccion(
        cliente_id=int(cid),
        canal=data.get("canal") or "otro",
        resumen=(data.get("resumen") or "").strip() or "(sin resumen)",
        proxima_accion=data.get("proxima_accion") or None,
        proxima_fecha=_parse_date(data.get("proxima_fecha")),
    )
    db.session.add(i)
    db.session.commit()
    return {"ok": True, "id": i.id}


@bp.route("/tarea_social", methods=["POST"])
def quick_tarea_social():
    data = request.get_json(silent=True) or request.form
    t = TareaSocial(
        plataforma=data.get("plataforma") or "instagram",
        tipo=data.get("tipo") or "DM",
        objetivo=data.get("objetivo") or None,
        mensaje=data.get("mensaje") or None,
        fecha=_parse_dt(data.get("fecha")),
    )
    db.session.add(t)
    db.session.commit()
    return {"ok": True, "id": t.id}


@bp.route("/post", methods=["POST"])
def quick_post():
    data = request.get_json(silent=True) or request.form
    p = Publicacion(
        plataforma=data.get("plataforma") or "instagram",
        titulo=data.get("titulo") or None,
        contenido=data.get("contenido") or None,
        hashtags=data.get("hashtags") or None,
        fecha_programada=_parse_dt(data.get("fecha_programada")),
        estado=data.get("estado") or ("programada" if data.get("fecha_programada") else "borrador"),
        proyecto_id=int(data.get("proyecto_id")) if data.get("proyecto_id") else None,
    )
    db.session.add(p)
    db.session.commit()
    return {"ok": True, "id": p.id, "url": url_for("social.edit_post", pid=p.id)}


@bp.route("/tarea", methods=["POST"])
def quick_tarea():
    data = request.get_json(silent=True) or request.form
    pid = data.get("proyecto_id")
    if not pid:
        return {"ok": False, "error": "proyecto_id requerido"}, 400
    fi = _parse_date(data.get("fecha_inicio")) or date.today()
    ff = _parse_date(data.get("fecha_fin")) or fi
    t = Tarea(
        proyecto_id=int(pid),
        nombre=(data.get("nombre") or "").strip() or "Nueva tarea",
        fecha_inicio=fi, fecha_fin=ff,
        progreso=int(data.get("progreso") or 0),
    )
    db.session.add(t)
    db.session.commit()
    return {"ok": True, "id": t.id}
