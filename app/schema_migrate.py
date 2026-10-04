"""Migraciones versionadas. Cada paso corre una sola vez."""

import os
from datetime import datetime

from sqlalchemy import inspect, text

from .database import is_sqlite_uri
from .extensions import db
from .tenancy import MODULOS, ModulosNegocio, Negocio, SchemaRevision, table_has_column


def apply_schema_steps(base_dir: str, db_uri: str, *, testing: bool = False) -> None:
    if db.session.get(SchemaRevision, "001_negocio") is None:
        if not testing:
            _backup_sqlite(base_dir, db_uri)
        _step_negocio(db_uri)
        db.session.add(SchemaRevision(id="001_negocio"))
        db.session.commit()


def create_backup(base_dir: str, db_uri: str, prefix: str = "manual") -> str | None:
    """Copia consistente de SQLite. MySQL no se copia en caliente desde aquí."""
    return _backup_sqlite(base_dir, db_uri, prefix)


def _backup_sqlite(base_dir: str, db_uri: str, prefix: str = "pre-mg01") -> str | None:
    if not is_sqlite_uri(db_uri):
        return None
    path = db_uri.replace("sqlite:///", "", 1)
    if not path or path == ":memory:" or not os.path.isfile(path) or os.path.getsize(path) == 0:
        return None
    folder = os.path.join(base_dir, "backups")
    os.makedirs(folder, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = os.path.join(folder, f"{prefix}-{stamp}.sqlite")
    if os.path.abspath(path) == os.path.abspath(dest):
        return None
    import sqlite3
    source = sqlite3.connect(path)
    try:
        target = sqlite3.connect(dest)
        try:
            source.backup(target)
        finally:
            target.close()
    finally:
        source.close()
    return dest


def _tenant_tables() -> list[str]:
    names = []
    for mapper in db.Model.registry.mappers:
        cls = mapper.class_
        if getattr(cls, "__tenant__", False):
            names.append(cls.__tablename__)
    return names


def _step_negocio(db_uri: str) -> None:
    is_sqlite = is_sqlite_uri(db_uri)
    with db.engine.begin() as conn:
        tables = set(inspect(conn).get_table_names())
        for table in _tenant_tables():
            if table not in tables:
                continue
            if table_has_column(conn, table, "negocio_id"):
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN negocio_id INTEGER"))
        for table in _tenant_tables():
            if table not in tables:
                continue
            index = f"ix_{table}_negocio_id"
            try:
                if is_sqlite:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {index} ON {table} (negocio_id)"))
                else:
                    existing = {idx["name"] for idx in inspect(conn).get_indexes(table)}
                    if index not in existing:
                        conn.execute(text(f"CREATE INDEX {index} ON {table} (negocio_id)"))
            except Exception:
                pass

    db.session.commit()
    negocio = Negocio.query.order_by(Negocio.id).first()
    if negocio is None:
        has_rows = False
        for table in ("clientes", "proyectos", "publicaciones"):
            try:
                count = db.session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
            except Exception:
                count = 0
            if count:
                has_rows = True
                break
        if not has_rows:
            return
        negocio = Negocio(nombre=os.environ.get("BRAND_COMPANY") or "Mi negocio", tipo_actividad="servicios")
        db.session.add(negocio)
        db.session.flush()

    for table in _tenant_tables():
        try:
            db.session.execute(
                text(f"UPDATE {table} SET negocio_id = :nid WHERE negocio_id IS NULL"),
                {"nid": negocio.id},
            )
        except Exception:
            db.session.rollback()
            raise
    if not db.session.get(ModulosNegocio, negocio.id):
        flags = {nombre: True for nombre in MODULOS}
        flags["tiempo"] = False
        flags["finanzas"] = False
        db.session.add(ModulosNegocio(negocio_id=negocio.id, **flags))
    db.session.commit()
