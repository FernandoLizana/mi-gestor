from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, session, url_for

from ..access import load_context, negocios_del_usuario
from ..extensions import db
from ..schema_migrate import create_backup
from ..tenancy import (
    MODULOS,
    PERFILES,
    Membresia,
    ModulosNegocio,
    Negocio,
    Usuario,
    audit,
    current_negocio_id,
    current_usuario_id,
)

bp = Blueprint("account", __name__)


@bp.route("/ajustes", methods=["GET", "POST"])
def settings():
    user, membresia, modulos = load_context()
    row = db.session.get(ModulosNegocio, current_negocio_id())
    if request.method == "POST" and row:
        for nombre in MODULOS:
            setattr(row, nombre, request.form.get(f"mod_{nombre}") == "1")
        row.clientes = True
        audit("modulos", "negocio", row.negocio_id, "Módulos actualizados")
        db.session.commit()
        flash("Módulos guardados. Los datos de un módulo apagado se conservan.", "success")
        return redirect(url_for("account.settings"))
    miembros = (
        Membresia.query.execution_options(skip_tenant=True)
        .filter_by(negocio_id=current_negocio_id())
        .all()
    )
    return render_template(
        "account/settings.html",
        modulos=modulos,
        nombres_modulos=MODULOS,
        miembros=miembros,
        rol=membresia.rol if membresia else "",
        usuario=user,
    )


@bp.route("/ajustes/usuarios", methods=["POST"])
def add_user():
    nombre = (request.form.get("nombre") or "").strip()
    email = (request.form.get("email") or "").strip().lower()
    password = request.form.get("password") or ""
    rol = request.form.get("rol") or "colaborador"
    if rol not in ("administrador", "vendedor", "colaborador"):
        rol = "colaborador"
    if not nombre or not email or len(password) < 8:
        flash("Para invitar hace falta nombre, correo y contraseña de 8 caracteres.", "error")
        return redirect(url_for("account.settings"))
    user = Usuario.query.filter(db.func.lower(Usuario.email) == email).first()
    if user is None:
        user = Usuario(email=email, nombre=nombre[:150], activo=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
    else:
        flash("Esa persona ya tenía cuenta. Se le dio acceso a este negocio.", "info")
    nid = current_negocio_id()
    exists = (
        Membresia.query.execution_options(skip_tenant=True)
        .filter_by(usuario_id=user.id, negocio_id=nid)
        .first()
    )
    if not exists:
        db.session.add(Membresia(usuario_id=user.id, negocio_id=nid, rol=rol))
    audit("alta_usuario", "usuario", user.id, rol)
    db.session.commit()
    flash("Acceso creado.", "success")
    return redirect(url_for("account.settings"))


@bp.route("/ajustes/usuarios/<int:uid>/desactivar", methods=["POST"])
def deactivate_user(uid):
    if uid == current_usuario_id():
        flash("No puedes desactivar tu propia sesión desde aquí.", "error")
        return redirect(url_for("account.settings"))
    user = db.session.get(Usuario, uid)
    member = (
        Membresia.query.execution_options(skip_tenant=True)
        .filter_by(usuario_id=uid, negocio_id=current_negocio_id())
        .first()
    )
    if not user or not member:
        abort(404)
    user.activo = False
    audit("desactivar_usuario", "usuario", user.id)
    db.session.commit()
    flash("Esa persona ya no puede entrar.", "info")
    return redirect(url_for("account.settings"))


@bp.post("/negocios")
def new_negocio():
    nombre = (request.form.get("nombre") or "").strip()
    if not nombre:
        flash("El negocio necesita un nombre.", "error")
        return redirect(url_for("account.settings"))
    negocio = Negocio(nombre=nombre[:150], tipo_actividad="servicios", marca=nombre[:150])
    db.session.add(negocio)
    db.session.flush()
    flags = dict(PERFILES["servicios"])
    db.session.add(ModulosNegocio(negocio_id=negocio.id, **flags))
    db.session.add(Membresia(
        usuario_id=current_usuario_id(),
        negocio_id=negocio.id,
        rol="propietario",
    ))
    audit("alta_negocio", "negocio", negocio.id, nombre[:150])
    db.session.commit()
    session["negocio_id"] = negocio.id
    flash(f"Ahora estás en {negocio.nombre}.", "success")
    return redirect(url_for("dashboard.index"))


@bp.post("/negocios/cambiar")
def switch_negocio():
    try:
        nid = int(request.form.get("negocio_id") or 0)
    except ValueError:
        nid = 0
    allowed = {n.id for n in negocios_del_usuario(current_usuario_id())}
    if nid not in allowed:
        abort(403)
    session["negocio_id"] = nid
    return redirect(request.referrer or url_for("dashboard.index"))


@bp.post("/ajustes/respaldo")
def backup():
    uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    base_dir = current_app.config["BASE_DIR"]
    dest = create_backup(base_dir, uri, prefix="respaldo")
    if not dest:
        flash("Este respaldo automático cubre SQLite. En MySQL usa mysqldump con la base detenida o en modo consistente.", "error")
        return redirect(url_for("account.settings"))
    audit("respaldo", detalle=dest)
    db.session.commit()
    flash(f"Respaldo guardado en {dest}", "success")
    return redirect(url_for("account.settings"))
