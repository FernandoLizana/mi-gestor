import re
import os

PLATFORM_LINKS = {
    "instagram": "https://www.instagram.com/",
    "tiktok": "https://www.tiktok.com/tiktokstudio/upload",
    "facebook": "https://www.facebook.com/",
    "linkedin": "https://www.linkedin.com/feed/",
}

PLATFORM_TIPS = {
    "instagram": [
        "Toca + → Post (o Reel/Story según el formato).",
        "Sube la imagen descargada desde tu galería.",
        "Pega el texto copiado y revisa hashtags.",
        "Publica y vuelve aquí para marcar como hecho.",
    ],
    "tiktok": [
        "Abre TikTok Studio o la app → Subir video/imagen.",
        "Selecciona el archivo descargado.",
        "Pega la descripción copiada (incluye hashtags).",
        "Publica y marca como hecho en el CRM.",
    ],
    "facebook": [
        "Crea publicación en tu página o perfil.",
        "Adjunta la imagen y pega el texto.",
    ],
    "linkedin": [
        "Inicia publicación en el feed.",
        "Adjunta imagen y pega el copy profesional.",
    ],
}


def platform_upload_url(plataforma: str) -> str:
    return PLATFORM_LINKS.get((plataforma or "").lower(), "https://www.instagram.com/")


def platform_tips(plataforma: str) -> list[str]:
    return PLATFORM_TIPS.get((plataforma or "").lower(), PLATFORM_TIPS["instagram"])


def _clean_line(line: str) -> str:
    line = line.strip()
    if line.startswith("- "):
        line = line[2:].strip()
    if ":" in line:
        label, _, value = line.partition(":")
        if label.lower() in (
            "título", "titulo", "guion breve", "guión breve",
            "cta", "hashtags", "hashtag",
        ):
            return value.strip()
    return line


def caption_body(contenido: str | None) -> str:
    if not contenido:
        return ""
    lines = []
    for raw in contenido.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("##"):
            continue
        cleaned = _clean_line(line)
        if cleaned:
            lines.append(cleaned)
    return "\n\n".join(lines).strip()


def full_caption(contenido: str | None, hashtags: str | None, *, with_signature=True) -> str:
    parts = []
    body = caption_body(contenido)
    if body:
        parts.append(body)
    tags = (hashtags or "").strip()
    if tags:
        parts.append(tags)
    sig = (os.environ.get("BRAND_SIGNATURE") or "").strip()
    if with_signature and sig:
        parts.append(sig)
    return "\n\n".join(parts).strip()


def hashtags_only(hashtags: str | None, contenido: str | None) -> str:
    tags = (hashtags or "").strip()
    if tags:
        return tags
    if not contenido:
        return ""
    found = []
    for line in contenido.splitlines():
        if "hashtag" in line.lower() and ":" in line:
            found.append(line.split(":", 1)[-1].strip())
    text = " ".join(found)
    inline = re.findall(r"#\w+", contenido)
    if inline:
        text = (text + " " + " ".join(dict.fromkeys(inline))).strip()
    return text


def enrich_post_from_content(post) -> None:
    """Rellena hashtags desde el contenido IA si faltan."""
    if not (post.hashtags or "").strip() and post.contenido:
        post.hashtags = hashtags_only(None, post.contenido)
