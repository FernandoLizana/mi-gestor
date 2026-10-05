import base64
import mimetypes
import os
import uuid
from datetime import datetime

REF_SUBFOLDER = "referencias"
ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def referencias_dir(upload_folder: str) -> str:
    path = os.path.join(upload_folder, REF_SUBFOLDER)
    os.makedirs(path, exist_ok=True)
    return path


def list_reference_images(upload_folder: str):
    folder = referencias_dir(upload_folder)
    items = []
    for name in sorted(os.listdir(folder)):
        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_EXT:
            continue
        rel = f"{REF_SUBFOLDER}/{name}"
        full = os.path.join(upload_folder, rel)
        items.append({
            "name": name,
            "rel_path": rel,
            "size_kb": round(os.path.getsize(full) / 1024, 1),
        })
    return items


def save_reference_upload(file_storage, upload_folder: str) -> str:
    if not file_storage or not file_storage.filename:
        raise ValueError("No se recibió archivo")

    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError("Formato no permitido. Usa JPG, PNG o WEBP.")

    filename = f"{datetime.utcnow():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}{ext}"
    dest = os.path.join(referencias_dir(upload_folder), filename)
    file_storage.save(dest)
    return f"{REF_SUBFOLDER}/{filename}"


def _reference_file(upload_folder: str, rel_path: str) -> str:
    rel = (rel_path or "").replace("\\", "/").strip()
    if not rel.startswith(f"{REF_SUBFOLDER}/") or ".." in rel.split("/"):
        raise ValueError("Ruta no válida")
    root = os.path.realpath(referencias_dir(upload_folder))
    full = os.path.realpath(os.path.join(upload_folder, rel))
    if os.path.commonpath([root, full]) != root:
        raise ValueError("Ruta no válida")
    return full


def delete_reference(rel_path: str, upload_folder: str):
    full = _reference_file(upload_folder, rel_path)
    if os.path.isfile(full):
        os.remove(full)


def load_reference_as_data_url(upload_folder: str, rel_path: str) -> str:
    full = _reference_file(upload_folder, rel_path)
    if not os.path.isfile(full):
        raise FileNotFoundError(rel_path)

    mime, _ = mimetypes.guess_type(full)
    if not mime:
        mime = "image/jpeg"
    with open(full, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def resolve_reference_paths(upload_folder: str, selected_names):
    """Convierte nombres de archivo seleccionados a rutas relativas válidas."""
    if not selected_names:
        return []
    valid = {x["name"] for x in list_reference_images(upload_folder)}
    out = []
    for name in selected_names:
        if name in valid:
            out.append(f"{REF_SUBFOLDER}/{name}")
    return out
