"""Negocios, usuarios y el sello que separa sus datos."""

from datetime import datetime

from flask import has_request_context, session
from sqlalchemy import event, inspect
from sqlalchemy.orm import Session, with_loader_criteria
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db

MODULOS = ("clientes", "ventas", "proyectos", "redes", "publicidad", "tiempo", "finanzas")

PERFILES = {
    "servicios": {
        "clientes": True, "ventas": True, "proyectos": True,
        "redes": False, "publicidad": False, "tiempo": True, "finanzas": False,
    },
    "agencia": {nombre: True for nombre in MODULOS},
    "comercio": {
        "clientes": True, "ventas": True, "proyectos": False,
        "redes": False, "publicidad": False, "tiempo": False, "finanzas": True,
    },
    "personal": {
        "clientes": True, "ventas": False, "proyectos": True,
        "redes": False, "publicidad": False, "tiempo": False, "finanzas": False,
    },
}

ROLES_ADMIN = ("propietario", "administrador")


class TenantMixin:
    """Los registros de trabajo pertenecen a un negocio. El id lo pone el servidor."""

    __tenant__ = True
    negocio_id = db.Column(db.Integer, index=True)


class Negocio(db.Model):
    __tablename__ = "negocios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    tipo_actividad = db.Column(db.String(40), default="servicios")
    moneda = db.Column(db.String(8), default="CLP")
    zona_horaria = db.Column(db.String(60), default="America/Santiago")
    marca = db.Column(db.String(150))
    creado = db.Column(db.DateTime, default=datetime.utcnow)


class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    activo = db.Column(db.Boolean, default=True, nullable=False)
    creado = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password or "")


class Membresia(db.Model):
    __tablename__ = "membresias"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocios.id"), nullable=False, index=True)
    rol = db.Column(db.String(40), nullable=False, default="colaborador")
    usuario = db.relationship("Usuario", backref="membresias")
    negocio = db.relationship("Negocio")

    __table_args__ = (db.UniqueConstraint("usuario_id", "negocio_id", name="uq_miembro_negocio"),)


class ModulosNegocio(db.Model):
    __tablename__ = "modulos_negocio"
    negocio_id = db.Column(db.Integer, db.ForeignKey("negocios.id"), primary_key=True)
    clientes = db.Column(db.Boolean, default=True, nullable=False)
    ventas = db.Column(db.Boolean, default=True, nullable=False)
    proyectos = db.Column(db.Boolean, default=True, nullable=False)
    redes = db.Column(db.Boolean, default=True, nullable=False)
    publicidad = db.Column(db.Boolean, default=False, nullable=False)
    tiempo = db.Column(db.Boolean, default=False, nullable=False)
    finanzas = db.Column(db.Boolean, default=False, nullable=False)

    def as_dict(self) -> dict:
        return {nombre: bool(getattr(self, nombre)) for nombre in MODULOS}


class Auditoria(db.Model):
    __tablename__ = "auditoria"
    __tenant__ = True
    id = db.Column(db.Integer, primary_key=True)
    negocio_id = db.Column(db.Integer, index=True)
    usuario_id = db.Column(db.Integer)
    accion = db.Column(db.String(80), nullable=False)
    entidad = db.Column(db.String(80))
    entidad_id = db.Column(db.Integer)
    detalle = db.Column(db.String(300))
    creado = db.Column(db.DateTime, default=datetime.utcnow)


class SchemaRevision(db.Model):
    __tablename__ = "schema_revisions"
    id = db.Column(db.String(40), primary_key=True)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)


def current_negocio_id():
    if not has_request_context():
        return None
    value = session.get("negocio_id")
    return int(value) if value else None


def current_usuario_id():
    if not has_request_context():
        return None
    value = session.get("usuario_id")
    return int(value) if value else None


def skip_tenant():
    return db.session().execution_options(skip_tenant=True)


def installation_ready() -> bool:
    owner = (
        Membresia.query.execution_options(skip_tenant=True)
        .filter_by(rol="propietario")
        .first()
    )
    if not owner:
        return False
    user = db.session.get(Usuario, owner.usuario_id)
    return bool(user and user.activo)


def audit(accion: str, entidad: str | None = None, entidad_id: int | None = None, detalle: str | None = None) -> None:
    db.session.add(Auditoria(
        negocio_id=current_negocio_id(),
        usuario_id=current_usuario_id(),
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=(detalle or "")[:300] or None,
    ))


def _tenant_classes():
    classes = []
    for mapper in db.Model.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__tenant__", False):
            classes.append(cls)
    return classes


def register_tenant_hooks() -> None:
    if getattr(register_tenant_hooks, "_done", False):
        return
    register_tenant_hooks._done = True

    @event.listens_for(Session, "do_orm_execute")
    def _scope_reads(execute_state):
        if not execute_state.is_select:
            return
        if execute_state.execution_options.get("skip_tenant"):
            return
        negocio_id = current_negocio_id()
        if not negocio_id:
            return
        for cls in _tenant_classes():
            execute_state.statement = execute_state.statement.options(
                with_loader_criteria(
                    cls,
                    cls.negocio_id == negocio_id,
                    include_aliases=True,
                )
            )

    @event.listens_for(Session, "before_flush")
    def _stamp_writes(session, flush_context, instances):
        negocio_id = current_negocio_id()
        if not negocio_id:
            return
        for obj in session.new:
            if getattr(obj.__class__, "__tenant__", False):
                obj.negocio_id = negocio_id


def table_has_column(connection, table: str, column: str) -> bool:
    try:
        columns = inspect(connection).get_columns(table)
    except Exception:
        return False
    return any(col["name"] == column for col in columns)
