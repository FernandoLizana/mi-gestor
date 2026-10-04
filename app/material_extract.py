import base64
import mimetypes
import os

from .ai import AIConfigError, describe_image, is_ai_configured


def extract_pdf_text(upload_folder: str, rel_path: str, max_chars: int = 12000) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError("Instala pypdf: pip install pypdf") from e

    full = os.path.join(upload_folder, rel_path)
    if not os.path.isfile(full):
        raise FileNotFoundError(rel_path)

    reader = PdfReader(full)
    chunks = []
    for page in reader.pages[:30]:
        text = (page.extract_text() or "").strip()
        if text:
            chunks.append(text)
        if sum(len(c) for c in chunks) >= max_chars:
            break
    joined = "\n\n".join(chunks).strip()
    return joined[:max_chars] if joined else ""


def file_as_data_url(upload_folder: str, rel_path: str) -> str:
    full = os.path.join(upload_folder, rel_path)
    if not os.path.isfile(full):
        raise FileNotFoundError(rel_path)
    mime, _ = mimetypes.guess_type(full)
    if not mime:
        mime = "application/octet-stream"
    with open(full, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{b64}"


def extract_material_text(upload_folder: str, *, tipo_archivo: str, rel_path: str, notas: str = "") -> str:
    parts = []
    if notas:
        parts.append(f"Notas del usuario:\n{notas.strip()}")

    if tipo_archivo == "pdf":
        try:
            pdf_text = extract_pdf_text(upload_folder, rel_path)
            if pdf_text:
                parts.append(f"Texto extraído del PDF:\n{pdf_text}")
            else:
                parts.append("El PDF no tenía texto extraíble (puede ser escaneado). Usa las notas para describirlo.")
        except Exception as e:
            parts.append(f"No se pudo leer el PDF automáticamente ({e}).")
    elif tipo_archivo == "imagen" and is_ai_configured():
        try:
            desc = describe_image(
                file_as_data_url(upload_folder, rel_path),
                prompt=(
                    "Describe esta imagen o documento visual en español para crear publicaciones "
                    "de redes sociales de una tarotista. Incluye textos visibles, tema, ideas "
                    "clave y mensajes que se podrían comunicar."
                ),
            )
            if desc:
                parts.append(f"Descripción de la imagen:\n{desc}")
        except (AIConfigError, Exception) as e:
            parts.append(f"No se pudo analizar la imagen con IA ({e}).")

    if not parts:
        return notas.strip() or "Material sin texto extraído. Agrega notas al subir el archivo."
    return "\n\n".join(parts)
