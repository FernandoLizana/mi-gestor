"""Almacena vistas previas de importación en disco (evita cookies de sesión gigantes)."""
import json
import os
import re
import uuid
from datetime import datetime, timedelta

from flask import current_app

PREVIEW_TTL_HOURS = 24
_PREVIEW_ID_RE = re.compile(r"^[a-f0-9]{32}$")


def _preview_dir() -> str:
    folder = os.path.join(current_app.config["UPLOAD_FOLDER"], "import_previews")
    os.makedirs(folder, exist_ok=True)
    return folder


def _cleanup_old():
    cutoff = datetime.utcnow() - timedelta(hours=PREVIEW_TTL_HOURS)
    folder = _preview_dir()
    for name in os.listdir(folder):
        if not name.endswith(".json"):
            continue
        path = os.path.join(folder, name)
        try:
            if datetime.utcfromtimestamp(os.path.getmtime(path)) < cutoff:
                os.remove(path)
        except OSError:
            pass


def save_import_preview(payload: dict) -> str:
    _cleanup_old()
    preview_id = uuid.uuid4().hex
    path = os.path.join(_preview_dir(), f"{preview_id}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"created": datetime.utcnow().isoformat(), **payload},
            f,
            ensure_ascii=False,
            default=str,
        )
    return preview_id


def load_import_preview(preview_id: str) -> dict | None:
    if not preview_id or not _PREVIEW_ID_RE.match(preview_id):
        return None
    path = os.path.join(_preview_dir(), f"{preview_id}.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def delete_import_preview(preview_id: str):
    if not preview_id or not _PREVIEW_ID_RE.match(preview_id):
        return
    path = os.path.join(_preview_dir(), f"{preview_id}.json")
    try:
        os.remove(path)
    except OSError:
        pass
