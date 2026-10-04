#!/usr/bin/env python3
"""
Importa prospectos comerciales desde Excel (.xlsx).

  python import_prospectos.py --check-db
  python import_prospectos.py --dry-run archivo.xlsx
  python import_prospectos.py --duplicate-policy skip archivo.xlsx

Política ante duplicados: skip | update | create.

Requisitos:
  - .env en la raíz de este repositorio
  - openpyxl (requirements.txt)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _load_cli_env() -> None:
    from app.env_loader import safe_load_dotenv

    safe_load_dotenv(str(_REPO_ROOT / ".env"), override=False)


def _mask_db_uri(uri: str) -> str:
    if "@" not in uri:
        return uri
    prefix, rest = uri.split("@", 1)
    if "://" in prefix:
        scheme, creds = prefix.split("://", 1)
        if ":" in creds:
            user = creds.split(":", 1)[0]
            return f"{scheme}://{user}:****@{rest}"
    return uri


def _print_db_config() -> None:
    print("Config MySQL (desde entorno):")
    print(f"  DB_HOST={os.environ.get('DB_HOST', '(vacío)')}")
    print(f"  DB_NAME={os.environ.get('DB_NAME', '(vacío)')}")
    print(f"  DB_USER={os.environ.get('DB_USER', '(vacío)')}")
    if os.environ.get("DATABASE_URL"):
        print(f"  DATABASE_URL={_mask_db_uri(os.environ['DATABASE_URL'])}")


def check_db_connection() -> int:
    _load_cli_env()
    _print_db_config()
    from urllib.parse import quote_plus

    from sqlalchemy import create_engine, text

    from app.database import build_database_uri

    uri = build_database_uri(str(_REPO_ROOT))
    print(f"\nURI: {_mask_db_uri(uri)}\n")

    host = os.environ.get("DB_HOST", "localhost")
    port = os.environ.get("DB_PORT", "3306")
    user = os.environ.get("DB_USER", "")
    password = quote_plus(os.environ.get("DB_PASSWORD", ""))
    driver = os.environ.get("DB_DRIVER", "mysql+pymysql")
    db_name = os.environ.get("DB_NAME", "")
    server_uri = f"{driver}://{user}:{password}@{host}:{port}/?charset=utf8mb4"

    try:
        engine = create_engine(uri, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            count = conn.execute(text("SELECT COUNT(*) FROM clientes")).scalar()
        print(f"Conexión OK. Registros en clientes: {count}")
        return 0
    except Exception as exc:
        err = str(exc)
        print(f"ERROR de conexión: {exc}\n")

        if "1044" in err or "1045" in err:
            print("Diagnóstico adicional:")
            try:
                engine = create_engine(server_uri, pool_pre_ping=True)
                with engine.connect() as conn:
                    rows = conn.execute(text("SHOW DATABASES")).fetchall()
                names = sorted(
                    r[0] for r in rows
                    if r[0] not in {"information_schema", "mysql", "performance_schema", "sys"}
                )
                if names:
                    print(f"  Bases accesibles para {user}:")
                    for name in names:
                        mark = "  ← usa este DB_NAME en .env" if name == db_name else ""
                        print(f"    - {name}{mark}")
                    if db_name and db_name not in names:
                        print(
                            f"\n  El .env pide DB_NAME={db_name} pero ese usuario NO tiene acceso."
                        )
                        print("  Cambia .env a uno de la lista, o vincula usuario y base.")
                else:
                    print(f"  El usuario {user} no ve ninguna base de datos.")
                    print("  Crea la base y vincúlala al usuario.")
            except Exception as exc2:
                print(f"  No se pudo listar bases: {exc2}")
                if "1045" in str(exc2):
                    print("  Error 1045 = usuario o contraseña incorrectos en DB_PASSWORD.")

        print(
            "\nRevisa DB_HOST, DB_NAME, DB_USER y DB_PASSWORD en el .env de este repositorio.\n"
            "Si DB_HOST está vacío, la app usa SQLite local (data.sqlite)."
        )
        return 1


_load_cli_env()

from app import create_app  # noqa: E402
from app.commercial.csv_import import parse_import_file, validate_import_rows  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models import Cliente  # noqa: E402


def _apply_fields(fields: dict, existing: Cliente | None, policy: str) -> str:
    """Inserta o actualiza. Retorna: imported | updated | skipped."""
    if existing and policy == "skip":
        return "skipped"
    if existing and policy == "update":
        for key, val in fields.items():
            if val is not None and hasattr(existing, key):
                setattr(existing, key, val)
        existing.actualizado = datetime.utcnow()
        return "updated"
    c = Cliente(**{k: v for k, v in fields.items() if hasattr(Cliente, k)})
    db.session.add(c)
    return "imported"


def import_file(
    path: Path,
    *,
    producto: str | None,
    fuente: str,
    nicho: str | None,
    responsable: str,
    duplicate_policy: str,
    dry_run: bool,
) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"No existe el archivo: {path}")

    raw = path.read_bytes()
    parsed = parse_import_file(raw, path.name)
    validation = validate_import_rows(
        parsed["rows"],
        producto_default=producto,
        fuente_default=fuente,
        nicho_default=nicho,
    )

    error_rows = validation["errors"]
    stats = {
        "imported": 0,
        "updated": 0,
        "skipped": 0,
        "error_count": len(error_rows),
    }

    for item in validation["valid"]:
        fields = dict(item["fields"])
        if not fields.get("responsable"):
            fields["responsable"] = responsable
        if dry_run:
            stats["imported"] += 1
            continue
        action = _apply_fields(fields, None, duplicate_policy)
        stats[action] += 1

    for item in validation["duplicates"]:
        fields = dict(item["fields"])
        if not fields.get("responsable"):
            fields["responsable"] = responsable
        dup = item["duplicate"]
        if dry_run:
            if duplicate_policy == "skip":
                stats["skipped"] += 1
            elif duplicate_policy == "update":
                stats["updated"] += 1
            else:
                stats["imported"] += 1
            continue
        action = _apply_fields(fields, dup, duplicate_policy)
        stats[action] += 1

    return {
        "file": path.name,
        "rows": len(parsed["rows"]),
        "valid": len(validation["valid"]),
        "duplicates": len(validation["duplicates"]),
        "errors": error_rows,
        **stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Importar prospectos Excel al CRM Mi Gestor")
    parser.add_argument(
        "archivos",
        nargs="*",
        help="Rutas a archivos .xlsx (subidos al servidor)",
    )
    parser.add_argument(
        "--producto",
        default=None,
        help="Producto por defecto (ej. Agenda de reservas, Sitio web, Campañas)",
    )
    parser.add_argument(
        "--nicho",
        default=None,
        help="Nicho por defecto (ej. 'tarot / espiritualidad')",
    )
    parser.add_argument(
        "--responsable",
        default="equipo",
        help="Responsable por defecto si la fila no lo trae",
    )
    parser.add_argument(
        "--fuente",
        default="Import Excel",
        help="Fuente por defecto para filas sin fuente",
    )
    parser.add_argument(
        "--duplicate-policy",
        choices=("skip", "update", "create"),
        default="skip",
        help="skip=omitir duplicados, update=actualizar existente, create=crear otro registro",
    )
    parser.add_argument(
        "--check-db",
        action="store_true",
        help="Solo prueba conexión MySQL y muestra DB_USER/DB_NAME (sin importar)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra resumen; no escribe en la base de datos",
    )
    args = parser.parse_args()

    if args.check_db:
        return check_db_connection()

    if not args.archivos:
        parser.error("Indica al menos un archivo .xlsx o usa --check-db")

    _load_cli_env()
    app = create_app()
    with app.app_context():
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        print(f"Base de datos: {_mask_db_uri(uri)}")
        print(f"DB_USER={os.environ.get('DB_USER')}  DB_NAME={os.environ.get('DB_NAME')}")
        if args.dry_run:
            print("Modo dry-run: no se guardará nada.\n")

        before = Cliente.query.filter_by(activo=True).count()
        print(f"Prospectos activos antes: {before}\n")

        totals = {"imported": 0, "updated": 0, "skipped": 0, "errors": 0}

        for raw_path in args.archivos:
            path = Path(raw_path).expanduser().resolve()
            print(f"--- {path.name} ---")
            try:
                result = import_file(
                    path,
                    producto=args.producto,
                    fuente=args.fuente,
                    nicho=args.nicho,
                    responsable=args.responsable,
                    duplicate_policy=args.duplicate_policy,
                    dry_run=args.dry_run,
                )
            except FileNotFoundError as exc:
                print(f"  ERROR: {exc}")
                return 1

            print(f"  Filas leídas:     {result['rows']}")
            print(f"  Nuevas válidas:   {result['valid']}")
            print(f"  Duplicadas:       {result['duplicates']}")
            print(f"  Errores:          {len(result['errors'])}")
            if result["errors"]:
                for err in result["errors"][:10]:
                    print(f"    L{err['line']}: {err['reason']}")
                if len(result["errors"]) > 10:
                    print(f"    ... y {len(result['errors']) - 10} más")

            label = "Simulados" if args.dry_run else "Importados"
            print(f"  {label}:          {result['imported']}")
            print(f"  Actualizados:     {result['updated']}")
            print(f"  Omitidos:         {result['skipped']}\n")

            for key in totals:
                if key == "errors":
                    totals[key] += len(result["errors"])
                else:
                    totals[key] += result[key]

        if not args.dry_run:
            db.session.commit()
            after = Cliente.query.filter_by(activo=True).count()
            print(f"Prospectos activos después: {after} (+{after - before})")

        print(
            f"Resumen: {totals['imported']} importados, "
            f"{totals['updated']} actualizados, "
            f"{totals['skipped']} omitidos, "
            f"{totals['errors']} errores."
        )

    return 0 if totals["errors"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
