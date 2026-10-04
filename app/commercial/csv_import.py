import csv
import io
import re
from datetime import datetime

from ..commercial.constants import IMPORT_COLUMN_ALIASES, PRODUCT_NAME_ALIASES
from ..models import Cliente

IMPORT_MAX_BYTES = 15 * 1024 * 1024
ALLOWED_IMPORT_EXTENSIONS = (".csv", ".xlsx")


def detect_encoding(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def detect_delimiter(sample: str) -> str:
    try:
        dialect = csv.Sniffer().sniff(sample[:4096], delimiters=",;\t")
        return dialect.delimiter
    except csv.Error:
        if sample.count(";") > sample.count(","):
            return ";"
        if "\t" in sample:
            return "\t"
        return ","


def normalize_header(h: str) -> str:
    key = re.sub(r"[^a-z0-9_]", "_", (h or "").strip().lower())
    key = re.sub(r"_+", "_", key).strip("_")
    return IMPORT_COLUMN_ALIASES.get(key, key)


def parse_csv_content(raw: bytes, delimiter: str | None = None):
    encoding = detect_encoding(raw)
    text = raw.decode(encoding, errors="replace")
    delim = delimiter or detect_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    headers = [normalize_header(h) for h in (reader.fieldnames or [])]
    rows = []
    for i, row in enumerate(reader, start=2):
        mapped = {}
        for orig, norm in zip(reader.fieldnames or [], headers):
            val = (row.get(orig) or "").strip()
            if val:
                mapped[norm] = val
        rows.append({"line": i, "data": mapped})
    return {"encoding": encoding, "delimiter": delim, "headers": headers, "rows": rows}


def parse_xlsx_content(raw: bytes):
    import openpyxl

    wb = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    ws = wb.active
    row_iter = ws.iter_rows(values_only=True)
    try:
        raw_headers = next(row_iter)
    except StopIteration:
        wb.close()
        return {"encoding": "xlsx", "delimiter": None, "headers": [], "rows": []}

    headers = [normalize_header(str(h) if h is not None else "") for h in raw_headers]
    rows = []
    for i, row in enumerate(row_iter, start=2):
        if not row or not any(c is not None and str(c).strip() for c in row):
            continue
        mapped = {}
        for norm, val in zip(headers, row):
            if val is None:
                continue
            s = str(val).strip()
            if s:
                mapped[norm] = s
        rows.append({"line": i, "data": mapped})
    wb.close()
    return {"encoding": "xlsx", "delimiter": None, "headers": headers, "rows": rows}


def parse_import_file(raw: bytes, filename: str, delimiter: str | None = None):
    ext = (filename or "").lower().rsplit(".", 1)[-1] if "." in (filename or "") else ""
    if ext == "xlsx":
        return parse_xlsx_content(raw)
    return parse_csv_content(raw, delimiter)


def _norm_text_key(s: str) -> str:
    return (
        (s or "")
        .strip()
        .lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )


def _normalize_product_name(value: str | None) -> str | None:
    if not value:
        return value
    key = _norm_text_key(value)
    return PRODUCT_NAME_ALIASES.get(key, value.strip())


def _normalize_priority(value: str | None) -> str:
    key = _norm_text_key(value or "media")
    mapping = {
        "baja": "baja",
        "media": "media",
        "alta": "alta",
        "muy alta": "muy alta",
        "muy_alta": "muy alta",
    }
    return mapping.get(key, "media")


def _normalize_temperature(value: str | None) -> str:
    key = _norm_text_key(value or "frio")
    mapping = {"frio": "frio", "tibio": "tibio", "caliente": "caliente"}
    return mapping.get(key, "frio")


def _enrich_import_row(data: dict) -> dict:
    """Completa campos derivados de columnas habituales en un Excel de prospectos."""
    out = dict(data)
    if not out.get("sitio_web"):
        out["sitio_web"] = out.get("url_perfil") or out.get("contacto_url") or out.get("fuente_verificacion")
    if out.get("fuente_verificacion") and not out.get("fuente"):
        out["fuente"] = out["fuente_verificacion"]
    if out.get("producto_interes"):
        out["producto_interes"] = _normalize_product_name(out["producto_interes"])
    extra_notes = []
    for key, label in (
        ("segmento", "Segmento"),
        ("tipo_organizacion", "Tipo"),
        ("modulo_demo", "Demo"),
        ("validacion_contacto", "Validación contacto"),
        ("notas_legales", "Notas legales"),
        ("comision_primera_venta", "Comisión 1ª venta"),
        ("comision_alto_ticket", "Comisión alto ticket"),
    ):
        if out.get(key):
            extra_notes.append(f"{label}: {out[key]}")
    if extra_notes:
        base = out.get("notas") or ""
        out["notas"] = (base + "\n\n" + "\n".join(extra_notes)).strip() if base else "\n".join(extra_notes)
    return out


def _has_minimum_identity(data: dict) -> bool:
    keys = ("nombre_negocio", "instagram", "whatsapp", "email", "sitio_web", "nombre_contacto")
    for k in keys:
        if data.get(k):
            return True
    if data.get("telefono"):
        return True
    return False


def _norm_phone(s):
    return re.sub(r"\D", "", s or "")


def _norm_ig(s):
    s = (s or "").strip().lstrip("@").lower()
    return s


def find_duplicate(cliente_data: dict, existing: list[Cliente]) -> Cliente | None:
    ig = _norm_ig(cliente_data.get("instagram"))
    wa = _norm_phone(cliente_data.get("whatsapp") or cliente_data.get("telefono"))
    email = (cliente_data.get("email") or "").lower()
    web = (cliente_data.get("sitio_web") or "").lower().rstrip("/")
    negocio = (cliente_data.get("nombre_negocio") or "").lower()
    comuna = (cliente_data.get("comuna") or "").lower()

    for c in existing:
        if ig and c.instagram and _norm_ig(c.instagram) == ig:
            return c
        c_wa = _norm_phone(c.whatsapp or c.telefono)
        if wa and c_wa and wa == c_wa:
            return c
        if email and c.email and c.email.lower() == email:
            return c
        if web and c.sitio_web and c.sitio_web.lower().rstrip("/") == web:
            return c
        cn = (c.empresa or c.nombre or "").lower()
        if negocio and comuna and cn == negocio and (c.comuna or "").lower() == comuna:
            return c
    return None


def row_to_cliente_fields(
    data: dict,
    producto_default: str | None = None,
    fuente_default: str | None = None,
    nicho_default: str | None = None,
) -> dict:
    data = _enrich_import_row(data)
    nombre_negocio = data.get("nombre_negocio") or data.get("nombre_contacto") or "Sin nombre"
    nombre_contacto = data.get("nombre_contacto") or data.get("nombre_negocio")
    notas = data.get("notas") or ""
    extras = []
    for key in ("youtube", "otros_contactos", "imagen"):
        if data.get(key):
            extras.append(f"{key}: {data[key]}")
    if extras:
        notas = (notas + "\n\n" + "\n".join(extras)).strip() if notas else "\n".join(extras)
    out = {
        "nombre": nombre_negocio[:150],
        "empresa": nombre_negocio[:150],
        "nombre_contacto": nombre_contacto,
        "cargo_contacto": data.get("cargo_contacto"),
        "email": data.get("email"),
        "telefono": data.get("telefono"),
        "whatsapp": data.get("whatsapp") or data.get("telefono"),
        "instagram": data.get("instagram"),
        "facebook": data.get("facebook"),
        "linkedin": data.get("linkedin"),
        "tiktok": data.get("tiktok"),
        "sitio_web": data.get("sitio_web"),
        "direccion": data.get("direccion"),
        "comuna": data.get("comuna"),
        "ciudad": data.get("ciudad"),
        "region": data.get("region"),
        "nicho": data.get("nicho") or nicho_default,
        "producto_interes": data.get("producto_interes") or producto_default,
        "prioridad": _normalize_priority(data.get("prioridad")),
        "temperatura": _normalize_temperature(data.get("temperatura")),
        "estado_pipeline": data.get("estado_pipeline") or "Nuevo",
        "fuente": data.get("fuente") or fuente_default or "CSV",
        "dolor_detectado": data.get("dolor_detectado"),
        "motivo_encaje": data.get("motivo_encaje"),
        "mensaje_sugerido": data.get("mensaje_sugerido"),
        "notas": notas or None,
        "proxima_accion": data.get("proxima_accion"),
        "responsable": data.get("responsable"),
        "setup_estimado": _float_or_none(data.get("setup_estimado")),
        "mensualidad_estimada": _float_or_none(data.get("mensualidad_estimada")),
        "monto_oportunidad": _float_or_none(data.get("monto_oportunidad")),
        "tipo_registro": "prospecto",
        "estado": "prospecto",
        "activo": True,
    }
    if data.get("fecha_proximo_seguimiento"):
        out["fecha_proximo_seguimiento"] = _parse_date(data["fecha_proximo_seguimiento"])
    return out


def _float_or_none(v):
    if not v:
        return None
    s = str(v).strip().replace("$", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def _parse_date(s):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s.strip()[:10], fmt).date()
        except ValueError:
            continue
    return None


def validate_import_rows(
    rows: list,
    producto_default: str | None = None,
    fuente_default: str | None = None,
    nicho_default: str | None = None,
):
    existing = Cliente.query.filter_by(activo=True).all()
    valid = []
    errors = []
    duplicates = []

    for item in rows:
        data = _enrich_import_row(item["data"])
        line = item["line"]
        if not _has_minimum_identity(data):
            errors.append({"line": line, "reason": "Falta identificador mínimo (negocio, IG, WhatsApp, email o web)", "data": data})
            continue
        dup = find_duplicate(data, existing)
        fields = row_to_cliente_fields(
            data, producto_default,
            fuente_default=fuente_default,
            nicho_default=nicho_default,
        )
        entry = {"line": line, "fields": fields, "duplicate": dup}
        if dup:
            duplicates.append(entry)
        else:
            valid.append(entry)
    return {"valid": valid, "duplicates": duplicates, "errors": errors}
