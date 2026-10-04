import os
import sys
from flask import Flask, abort, redirect, request, send_from_directory, session, url_for, current_app
from werkzeug.exceptions import HTTPException
from .branding import brand_company, brand_name
from .database import build_database_uri, is_sqlite_uri
from .env_loader import safe_load_dotenv
from .extensions import db, migrate


def create_app(mount_path=None, config_overrides=None):
    base_dir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    safe_load_dotenv(os.path.join(base_dir, ".env"), override=False)
    extra_root = os.environ.get("EXTRA_APP_ROOT", "").strip()
    if extra_root and extra_root not in sys.path:
        sys.path.insert(0, extra_root)
    if mount_path is None:
        mount_path = os.environ.get("CRM_MOUNT_PATH", "")
    mount_path = (mount_path or "").strip().rstrip("/")

    app = Flask(__name__)

    os.makedirs(os.path.join(base_dir, "uploads"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "uploads", "social"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "uploads", "referencias"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "uploads", "publicidad"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "uploads", "comercial"), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "uploads", "import_previews"), exist_ok=True)

    db_uri = build_database_uri(base_dir)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "local-dev-only")
    app.config["BASE_DIR"] = base_dir
    app.config["UPLOAD_FOLDER"] = os.path.join(base_dir, "uploads")
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if config_overrides:
        app.config.update(config_overrides)
        db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
    if not is_sqlite_uri(db_uri):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
            "pool_recycle": 280,
            "pool_pre_ping": True,
        }
    app.config["CRM_MOUNT_PATH"] = mount_path
    if mount_path:
        app.config["APPLICATION_ROOT"] = mount_path
        app.config["SESSION_COOKIE_PATH"] = mount_path

    db.init_app(app)
    migrate.init_app(app, db)

    from .auth import bp as auth_bp
    from .pwa import register_pwa
    from .routes.setup import bp as setup_bp
    from .routes.account import bp as account_bp
    from .access import guard_request, load_context, negocios_del_usuario
    from .tenancy import installation_ready, register_tenant_hooks

    register_tenant_hooks()
    app.register_blueprint(auth_bp)
    app.register_blueprint(setup_bp)
    app.register_blueprint(account_bp)
    register_pwa(app, mount_path=mount_path)

    public_endpoints = {
        None, "auth.login", "auth.logout", "setup.wizard",
        "pwa_manifest", "pwa_service_worker", "team_photo", "static",
    }

    @app.before_request
    def require_crm_login():
        if request.method == "POST":
            origin = request.origin
            if origin and origin != request.host_url.rstrip("/"):
                abort(403)
        if request.endpoint in public_endpoints:
            return
        if not installation_ready():
            return redirect(url_for("setup.wizard"))
        if not session.get("usuario_id"):
            return redirect(url_for("auth.login", next=request.path))
        try:
            guard_request(request.endpoint)
        except HTTPException as exc:
            if exc.code == 401:
                return redirect(url_for("auth.login", next=request.path))
            raise

    # Blueprints
    from .routes.dashboard import bp as dashboard_bp
    from .routes.projects import bp as projects_bp
    from .routes.clients import bp as clients_bp
    from .routes.social import bp as social_bp
    from .routes.quickadd import bp as quick_bp
    from .routes.prospects import bp as prospects_bp
    from .routes.publicidad import bp as publicidad_bp
    from .routes.commercial import bp as commercial_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(projects_bp, url_prefix="/proyectos")
    app.register_blueprint(clients_bp, url_prefix="/clientes")
    app.register_blueprint(social_bp, url_prefix="/redes")
    app.register_blueprint(quick_bp, url_prefix="/q")
    app.register_blueprint(prospects_bp, url_prefix="/prospectos")
    app.register_blueprint(publicidad_bp, url_prefix="/publicidad")
    app.register_blueprint(commercial_bp)

    @app.route("/uploads/<path:filename>")
    def uploaded_file(filename):
        return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

    @app.route("/equipo/<path:rel>")
    def team_photo(rel):
        """Fotos del equipo para login (ruta explícita, sin depender de /static/)."""
        return send_from_directory(os.path.join(app.root_path, "static"), rel)

    # Hacer Cliente/Proyecto disponibles globalmente para el FAB
    from .models import Cliente as _C, Proyecto as _P

    @app.context_processor
    def _inject_globals():
        user, membresia, modulos = (None, None, {nombre: False for nombre in (
            "clientes", "ventas", "proyectos", "redes", "publicidad", "tiempo", "finanzas",
        )})
        if session.get("usuario_id"):
            try:
                user, membresia, modulos = load_context()
            except Exception:
                pass
        payload = {
            "crm_root": request.script_root
            or current_app.config.get("CRM_MOUNT_PATH", ""),
            "brand_name": brand_name(),
            "brand_company": brand_company(),
            "modulos": modulos,
            "rol_actual": membresia.rol if membresia else "",
            "negocio_actual": session.get("negocio_id"),
            "negocios": negocios_del_usuario(user.id) if user else [],
        }
        negocio = next((n for n in payload["negocios"] if n.id == payload["negocio_actual"]), None)
        if negocio and negocio.marca:
            payload["brand_name"] = negocio.marca
        try:
            if session.get("negocio_id"):
                payload["_quick_clientes"] = _C.query.order_by(_C.nombre).all()
                payload["_quick_proyectos"] = _P.query.order_by(_P.nombre).all()
            else:
                payload["_quick_clientes"] = []
                payload["_quick_proyectos"] = []
        except Exception:
            payload["_quick_clientes"] = []
            payload["_quick_proyectos"] = []
        return payload

    with app.app_context():
        from . import models  # noqa: F401
        from .tenancy import register_tenant_hooks as _hooks
        _hooks()
        db.create_all()
        if is_sqlite_uri(db_uri):
            _migrate_sqlite()
        from .schema_migrate import apply_schema_steps
        apply_schema_steps(base_dir, db_uri, testing=bool(app.config.get("TESTING")))

    return app


def _migrate_sqlite():
    """Agrega columnas nuevas a tablas existentes (SQLite simple migrate)."""
    from sqlalchemy import text
    nuevas = [
        ("proyectos", "tipo", "VARCHAR(40)"),
        ("proyectos", "objetivo", "TEXT"),
        ("proyectos", "usa_redes", "BOOLEAN DEFAULT 0"),
        ("proyectos", "plataformas_redes", "VARCHAR(200)"),
        ("proyectos", "frecuencia_posts", "INTEGER DEFAULT 0"),
        ("publicaciones", "imagen_path", "VARCHAR(300)"),
        ("prospectos_ia", "historial_contacto", "TEXT"),
        ("prospectos_ia", "ultimo_contacto", "DATETIME"),
        ("publicaciones", "material_id", "INTEGER"),
        ("publicaciones", "origen", "VARCHAR(40)"),
        ("publicaciones", "formato_creativo", "VARCHAR(40)"),
    ]
    cliente_cols = [
        ("tipo_registro", "VARCHAR(40)"),
        ("nombre_contacto", "VARCHAR(150)"),
        ("cargo_contacto", "VARCHAR(100)"),
        ("nicho", "VARCHAR(80)"),
        ("producto_interes", "VARCHAR(120)"),
        ("comuna", "VARCHAR(80)"),
        ("ciudad", "VARCHAR(80)"),
        ("region", "VARCHAR(80)"),
        ("tiktok", "VARCHAR(100)"),
        ("sitio_web", "VARCHAR(300)"),
        ("whatsapp", "VARCHAR(50)"),
        ("prioridad", "VARCHAR(20)"),
        ("temperatura", "VARCHAR(20)"),
        ("estado_pipeline", "VARCHAR(40)"),
        ("dolor_detectado", "TEXT"),
        ("motivo_encaje", "TEXT"),
        ("plan_sugerido", "VARCHAR(80)"),
        ("setup_estimado", "FLOAT"),
        ("mensualidad_estimada", "FLOAT"),
        ("monto_oportunidad", "FLOAT"),
        ("probabilidad_cierre", "INTEGER"),
        ("fecha_primer_contacto", "DATE"),
        ("fecha_ultimo_contacto", "DATETIME"),
        ("fecha_proximo_seguimiento", "DATE"),
        ("proxima_accion", "VARCHAR(250)"),
        ("responsable", "VARCHAR(80)"),
        ("mensaje_sugerido", "TEXT"),
        ("tags", "VARCHAR(300)"),
        ("activo", "BOOLEAN DEFAULT 1"),
        ("actualizado", "DATETIME"),
    ]
    inter_cols = [
        ("tipo", "VARCHAR(40)"),
        ("resultado", "VARCHAR(200)"),
        ("detalle", "TEXT"),
        ("usuario_responsable", "VARCHAR(80)"),
    ]
    with db.engine.begin() as conn:
        for tabla, col, tipo_sql in nuevas:
            existing = [r[1] for r in conn.execute(text(f"PRAGMA table_info({tabla})"))]
            if col not in existing:
                conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo_sql}"))
        for col, tipo_sql in cliente_cols:
            existing = [r[1] for r in conn.execute(text("PRAGMA table_info(clientes)"))]
            if col not in existing:
                conn.execute(text(f"ALTER TABLE clientes ADD COLUMN {col} {tipo_sql}"))
        for col, tipo_sql in inter_cols:
            existing = [r[1] for r in conn.execute(text("PRAGMA table_info(interacciones)"))]
            if col not in existing:
                conn.execute(text(f"ALTER TABLE interacciones ADD COLUMN {col} {tipo_sql}"))
