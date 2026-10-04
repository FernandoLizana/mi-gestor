from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from ..extensions import db
from ..seed import ensure_seed
from ..seed_commercial import ensure_commercial_seed
from ..tenancy import (
    MODULOS,
    PERFILES,
    Membresia,
    ModulosNegocio,
    Negocio,
    Usuario,
    audit,
    installation_ready,
)

bp = Blueprint("setup", __name__)


def _modulos_from_form(perfil: str) -> dict:
    base = dict(PERFILES.get(perfil, PERFILES["servicios"]))
    base["clientes"] = True
    return base


@bp.route("/setup", methods=["GET", "POST"])
def wizard():
    if installation_ready():
        abort(403)
    existente = Negocio.query.order_by(Negocio.id).first()
    if request.method == "POST":
        nombre = (request.form.get("nombre") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        perfil = request.form.get("perfil") or "servicios"
        if perfil not in PERFILES:
            perfil = "servicios"
        if not nombre or not email or len(password) < 8:
            flash("Nombre, correo y una contraseña de al menos 8 caracteres son obligatorios.", "error")
            return render_template("setup.html", perfiles=PERFILES, existente=existente, modulos=MODULOS)
        if Usuario.query.filter(db.func.lower(Usuario.email) == email).first():
            flash("Ese correo ya está registrado.", "error")
            return render_template("setup.html", perfiles=PERFILES, existente=existente, modulos=MODULOS)

        if existente:
            negocio = existente
        else:
            negocio = Negocio(
                nombre=(request.form.get("negocio") or nombre).strip()[:150],
                tipo_actividad=perfil,
                moneda=(request.form.get("moneda") or "CLP").strip()[:8] or "CLP",
                zona_horaria=(request.form.get("zona") or "America/Santiago").strip()[:60],
                marca=(request.form.get("negocio") or nombre).strip()[:150],
            )
            db.session.add(negocio)
            db.session.flush()

        user = Usuario(email=email, nombre=nombre[:150], activo=True)
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        db.session.add(Membresia(usuario_id=user.id, negocio_id=negocio.id, rol="propietario"))

        if not db.session.get(ModulosNegocio, negocio.id):
            db.session.add(ModulosNegocio(negocio_id=negocio.id, **_modulos_from_form(perfil)))

        session["usuario_id"] = user.id
        session["negocio_id"] = negocio.id
        session["crm_auth"] = True
        session["crm_user"] = user.nombre

        if request.form.get("ejemplos") == "1" and not existente:
            ensure_seed()
            ensure_commercial_seed()
        audit("configuracion_inicial", "negocio", negocio.id, "Alta del propietario")
        db.session.commit()
        flash("Listo. Esta instalación ya tiene propietario.", "success")
        return redirect(url_for("dashboard.index"))

    return render_template("setup.html", perfiles=PERFILES, existente=existente, modulos=MODULOS)
