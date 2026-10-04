import json
import re
from urllib.parse import urlparse

import requests


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


def normalize_instagram_handle(raw: str) -> str:
    if not raw:
        return ""
    raw = raw.strip()
    if not raw:
        return ""
    if raw.startswith("@"):
        raw = raw[1:]
    if "instagram.com" in raw:
        try:
            path = urlparse(raw).path.strip("/")
            if path:
                raw = path.split("/")[0]
        except Exception:
            pass
    return re.sub(r"[^a-zA-Z0-9._]", "", raw).strip(".")


def parse_handles_bulk(text: str):
    handles = []
    seen = set()
    for line in (text or "").splitlines():
        h = normalize_instagram_handle(line)
        if not h:
            continue
        key = h.lower()
        if key in seen:
            continue
        seen.add(key)
        handles.append(h)
    return handles


def build_profile_url(handle: str) -> str:
    return f"https://www.instagram.com/{handle}/"


def fetch_profile_snapshot(handle: str, limit: int = 4):
    """Obtiene señales visibles del perfil público. Devuelve dict con bio/posts/error."""
    handle = normalize_instagram_handle(handle)
    if not handle:
        return {"bio": None, "posts": [], "error": "handle vacío"}

    url = build_profile_url(handle)
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Accept-Language": "es-CL,es;q=0.9"},
            timeout=20,
        )
        if resp.status_code >= 400:
            return {"bio": None, "posts": [], "error": f"HTTP {resp.status_code}"}
        html = resp.text
    except Exception as e:
        return {"bio": None, "posts": [], "error": str(e)}

    bio = _extract_bio(html)
    posts = _extract_posts(html, limit=limit)
    if not bio and not posts:
        return {"bio": None, "posts": [], "error": "No se pudieron extraer señales públicas"}
    return {"bio": bio, "posts": posts, "error": None}


def _extract_bio(html: str):
    m = re.search(r'"biography":"(.*?)"', html)
    if not m:
        return None
    try:
        return bytes(m.group(1), "utf-8").decode("unicode_escape").strip()
    except Exception:
        return m.group(1).strip()


def _extract_posts(html: str, limit: int = 4):
    """
    Extrae captions recientes desde blobs JSON embebidos.
    Es best-effort: Instagram cambia estructura con frecuencia.
    """
    posts = []
    seen = set()
    for match in re.finditer(r'{"node":\{"__typename":"GraphImage".{0,2000}?\}\}', html):
        chunk = match.group(0)
        caption_match = re.search(r'"text":"(.*?)"', chunk)
        if not caption_match:
            continue
        caption = caption_match.group(1)
        try:
            caption = bytes(caption, "utf-8").decode("unicode_escape")
        except Exception:
            pass
        caption = caption.replace("\\n", " ").strip()
        if not caption:
            continue
        if caption in seen:
            continue
        seen.add(caption)
        posts.append(caption[:240])
        if len(posts) >= limit:
            break

    if posts:
        return posts

    # Fallback más tolerante: buscar JSON-LD
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.S):
        try:
            data = json.loads(block)
        except Exception:
            continue
        if isinstance(data, dict) and data.get("@type") in {"ProfilePage", "Person"}:
            desc = data.get("description")
            if desc:
                return [desc[:240]]
    return []
