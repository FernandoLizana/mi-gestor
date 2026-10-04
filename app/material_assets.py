import os
import uuid
from datetime import datetime

MATERIAL_SUBFOLDER = "publicidad"
ALLOWED_MATERIAL_EXT = {".pdf", ".jpg", ".jpeg", ".png"}


def materiales_dir(upload_folder: str) -> str:
    path = os.path.join(upload_folder, MATERIAL_SUBFOLDER)
    os.makedirs(path, exist_ok=True)
    return path


def save_material_upload(file_storage, upload_folder: str) -> tuple[str, str]:
    """Guarda archivo y devuelve (ruta_relativa, tipo_archivo)."""
    if not file_storage or not file_storage.filename:
        raise ValueError("No se recibió archivo")

    ext = os.path.splitext(file_storage.filename)[1].lower()
    if ext not in ALLOWED_MATERIAL_EXT:
        raise ValueError("Formato no permitido. Usa PDF, JPG o PNG.")

    tipo = "pdf" if ext == ".pdf" else "imagen"
    filename = f"{datetime.utcnow():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}{ext}"
    dest = os.path.join(materiales_dir(upload_folder), filename)
    file_storage.save(dest)
    return f"{MATERIAL_SUBFOLDER}/{filename}", tipo
