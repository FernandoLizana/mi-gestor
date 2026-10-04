import os
import json
import re
import base64
import uuid
from datetime import datetime
import requests


class AIConfigError(RuntimeError):
    pass


def is_ai_configured():
    provider = os.environ.get("AI_PROVIDER", "openai").lower()
    if provider == "openrouter":
        return bool(os.environ.get("OPENROUTER_API_KEY"))
    return bool(os.environ.get("OPENAI_API_KEY"))


def generate_text(prompt, *, system=None, temperature=0.7, max_tokens=1400):
    provider = os.environ.get("AI_PROVIDER", "openai").lower()
    if provider == "openrouter":
        return _generate_openrouter(
            prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    return _generate_openai(
        prompt,
        system=system,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _build_messages(prompt, system=None):
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    return messages


def _generate_openai(prompt, *, system=None, temperature=0.7, max_tokens=1400):
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise AIConfigError("OPENAI_API_KEY no configurada")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    response = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "model": model,
            "messages": _build_messages(prompt, system),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }),
        timeout=45,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def _generate_openrouter(prompt, *, system=None, temperature=0.7, max_tokens=1400):
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise AIConfigError("OPENROUTER_API_KEY no configurada")

    model = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.environ.get("APP_URL", "http://127.0.0.1:5000"),
            "X-Title": os.environ.get("APP_NAME", "Mi Gestor CRM"),
        },
        data=json.dumps({
            "model": model,
            "messages": _build_messages(prompt, system),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }),
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def describe_image(data_url: str, *, prompt: str, max_tokens: int = 900) -> str:
    """Describe una imagen o PDF visual vía modelo multimodal (OpenRouter)."""
    provider = os.environ.get("AI_PROVIDER", "openai").lower()
    if provider != "openrouter":
        raise AIConfigError("Análisis visual requiere AI_PROVIDER=openrouter")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise AIConfigError("OPENROUTER_API_KEY no configurada")

    model = os.environ.get("OPENROUTER_VISION_MODEL", "google/gemini-2.0-flash-001")
    content = [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": data_url}},
    ]
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.environ.get("APP_URL", "http://127.0.0.1:5001"),
            "X-Title": os.environ.get("APP_NAME", "Mi Gestor CRM"),
        },
        data=json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": max_tokens,
        }),
        timeout=90,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()


def generate_image(prompt, *, aspect_ratio="1:1", reference_data_urls=None):
    """Genera una imagen vía OpenRouter y devuelve data URL base64."""
    provider = os.environ.get("AI_PROVIDER", "openai").lower()
    if provider != "openrouter":
        raise AIConfigError("Generación de imágenes requiere AI_PROVIDER=openrouter")

    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise AIConfigError("OPENROUTER_API_KEY no configurada")

    model = os.environ.get(
        "OPENROUTER_IMAGE_MODEL",
        "google/gemini-2.5-flash-image",
    )
    content = [{"type": "text", "text": prompt}]
    for url in reference_data_urls or []:
        content.append({"type": "image_url", "image_url": {"url": url}})

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "modalities": ["image", "text"],
        "image_config": {"aspect_ratio": aspect_ratio},
    }
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.environ.get("APP_URL", "http://127.0.0.1:5001"),
            "X-Title": os.environ.get("APP_NAME", "Mi Gestor CRM"),
        },
        data=json.dumps(payload),
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    message = data["choices"][0]["message"]
    for image in message.get("images") or []:
        url = (image.get("image_url") or {}).get("url")
        if url:
            return url
    raise RuntimeError("El modelo no devolvió ninguna imagen")


def save_data_url_image(data_url: str, upload_folder: str, subfolder: str = "social") -> str:
    """Guarda data URL en disco. Devuelve ruta relativa dentro de uploads/."""
    match = re.match(r"data:image/(\w+);base64,(.+)", data_url, re.S)
    if not match:
        raise ValueError("Formato de imagen no reconocido")

    ext = match.group(1).replace("jpeg", "jpg")
    raw = base64.b64decode(match.group(2))
    dest_dir = os.path.join(upload_folder, subfolder)
    os.makedirs(dest_dir, exist_ok=True)
    filename = f"{datetime.utcnow():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:8]}.{ext}"
    rel_path = f"{subfolder}/{filename}"
    with open(os.path.join(upload_folder, rel_path), "wb") as f:
        f.write(raw)
    return rel_path
