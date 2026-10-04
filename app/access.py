"""Qué puede abrir cada rol y cada módulo."""

from flask import abort, session

from .extensions import db
from .tenancy import MODULOS, Membresia, ModulosNegocio, Usuario, current_negocio_id, current_usuario_id

# Prefijo de endpoint -> módulo. El tablero y el alta rápida no se apagan.
ENDPOINT_MODULE = (
    ("clients.", "clientes"),
    ("commercial.", "ventas"),
    ("prospects.", "ventas"),
    ("projects.", "proyectos"),
    ("social.", "redes"),
    ("publicidad.", "publicidad"),
)

ROLE_MODULES = {
    "propietario": set(MODULOS),
    "administrador": set(MODULOS),
    "vendedor": {"clientes", "ventas"},
    "colaborador": {"clientes", "proyectos"},
    "cliente_portal": set(),
}


def load_context():
    uid = current_usuario_id()
    nid = current_negocio_id()
    user = db.session.get(Usuario, uid) if uid else None
    membresia = None
    if user and nid:
        membresia = (
            Membresia.query.execution_options(skip_tenant=True)
            .filter_by(usuario_id=user.id, negocio_id=nid)
            .first()
        )
    modulos = {nombre: True for nombre in MODULOS}
    row = db.session.get(ModulosNegocio, nid) if nid else None
    if row:
        modulos = row.as_dict()
    return user, membresia, modulos


def module_for_endpoint(endpoint: str | None) -> str | None:
    if not endpoint:
        return None
    for prefix, module in ENDPOINT_MODULE:
        if endpoint.startswith(prefix):
            return module
    return None


def guard_request(endpoint: str | None) -> None:
    user, membresia, modulos = load_context()
    if not user or not user.activo or not membresia:
        session.clear()
        abort(401)
    module = module_for_endpoint(endpoint)
    if module and not modulos.get(module, False):
        abort(404)
    if module and module not in ROLE_MODULES.get(membresia.rol, set()):
        abort(403)
    if (
        endpoint
        and endpoint.startswith("account.")
        and endpoint != "account.switch_negocio"
        and membresia.rol not in ("propietario", "administrador")
    ):
        abort(403)


def negocios_del_usuario(usuario_id: int):
    rows = (
        Membresia.query.execution_options(skip_tenant=True)
        .filter_by(usuario_id=usuario_id)
        .all()
    )
    return [row.negocio for row in rows if row.negocio]
