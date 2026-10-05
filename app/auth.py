from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from .extensions import db
from .login_team import build_login_team
from .tenancy import Membresia, Usuario, installation_ready

bp = Blueprint("auth", __name__)


def _safe_next(url: str) -> str:
    url = (url or "").strip()
    if not url.startswith("/") or url.startswith("//") or "\\" in url:
        return ""
    return url


@bp.route("/login", methods=["GET", "POST"])
def login():
    if not installation_ready():
        return redirect(url_for("setup.wizard"))
    next_url = request.args.get("next") or request.form.get("next") or ""
    if session.get("usuario_id"):
        current = db.session.get(Usuario, session.get("usuario_id"))
        if not current or not current.activo:
            session.clear()
        else:
            safe = _safe_next(next_url)
            if safe:
                return redirect(safe)
            return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = Usuario.query.filter(db.func.lower(Usuario.email) == email).first()
        if not user or not user.activo or not user.check_password(password):
            flash("Correo o contraseña incorrectos.", "error")
        else:
            member = (
                Membresia.query.execution_options(skip_tenant=True)
                .filter_by(usuario_id=user.id)
                .order_by(Membresia.id)
                .first()
            )
            if not member:
                flash("Esta cuenta no pertenece a ningún negocio.", "error")
            else:
                session.clear()
                session["usuario_id"] = user.id
                session["negocio_id"] = member.negocio_id
                session["crm_auth"] = True
                session["crm_user"] = user.nombre
                session.permanent = True
                return redirect(_safe_next(next_url) or url_for("dashboard.index"))

    featured, team_others = build_login_team()
    crm_root = request.script_root or current_app.config.get("CRM_MOUNT_PATH", "")
    return render_template(
        "auth/login.html",
        next=request.args.get("next", ""),
        login_featured=featured,
        login_team=team_others,
        crm_root=crm_root,
    )


@bp.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))
