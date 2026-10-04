import json
import re
from datetime import datetime, timedelta, time

from .ai import generate_text
from .social_publish import enrich_post_from_content


def build_batch_prompt(*, texto_fuente: str, plataforma: str, tono: str, cantidad: int, tema_extra: str = ""):
    extra = f"\nEnfoque adicional: {tema_extra}" if tema_extra else ""
    return f"""Eres estratega de contenidos para una tarotista en redes sociales.

A partir del material fuente, crea exactamente {cantidad} publicaciones distintas para {plataforma}.
Tono: {tono}
{extra}

MATERIAL FUENTE:
{texto_fuente[:10000]}

Responde SOLO con un JSON válido (array), sin markdown ni texto extra:
[
  {{
    "titulo": "título corto",
    "contenido": "copy listo para publicar (2-4 párrafos cortos o bullets)",
    "hashtags": "#ejemplo #tarot",
    "formato": "post|carrusel|reel|story",
    "angulo": "educativo|tip|promo|inspiracional|mito|pregunta"
  }}
]

Reglas:
- Cada publicación debe ser única y basada en el material.
- Español chileno, cercano y ético (sin promesas absolutas).
- Variar ángulos: tips, historias, preguntas, promos suaves, educación.
- Hashtags relevantes en cada ítem."""


def parse_posts_response(raw: str, cantidad: int = 12) -> list[dict]:
    raw = (raw or "").strip()
    if not raw:
        return []

    # JSON directo o dentro de ```json
    json_match = re.search(r"\[[\s\S]*\]", raw)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            if isinstance(data, list):
                return [_normalize_post(item) for item in data[:cantidad] if isinstance(item, dict)]
        except json.JSONDecodeError:
            pass

    # Fallback: bloques ## Publicación
    blocks = re.split(r"##\s*Publicaci[oó]n\s*\d+", raw, flags=re.I)
    out = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        titulo = ""
        for line in block.splitlines():
            if line.lower().startswith("título:") or line.lower().startswith("titulo:"):
                titulo = line.split(":", 1)[1].strip()
                break
        out.append({
            "titulo": titulo or f"Publicación {len(out) + 1}",
            "contenido": block,
            "hashtags": "",
            "formato": "post",
            "angulo": "variado",
        })
        if len(out) >= cantidad:
            break
    return out


def _normalize_post(item: dict) -> dict:
    return {
        "titulo": (item.get("titulo") or "Sin título")[:180],
        "contenido": (item.get("contenido") or "").strip(),
        "hashtags": (item.get("hashtags") or "").strip(),
        "formato": (item.get("formato") or "post").strip(),
        "angulo": (item.get("angulo") or "").strip(),
    }


def generate_posts_from_material(
    *,
    texto_fuente: str,
    plataforma: str,
    tono: str,
    cantidad: int,
    tema_extra: str = "",
) -> list[dict]:
    raw = generate_text(
        build_batch_prompt(
            texto_fuente=texto_fuente,
            plataforma=plataforma,
            tono=tono,
            cantidad=cantidad,
            tema_extra=tema_extra,
        ),
        system=(
            "Generas calendarios editoriales para marca personal de tarot. "
            "Respondes únicamente con JSON válido."
        ),
        temperature=0.8,
        max_tokens=4500,
    )
    posts = parse_posts_response(raw, cantidad)
    if len(posts) < max(3, cantidad // 2):
        raise RuntimeError("La IA devolvió muy pocas publicaciones. Intenta de nuevo.")
    return posts


CREATIVE_STYLES = {
    "comic": {
        "label": "Cómic / viñetas",
        "desc": "Historieta corta de 2-4 viñetas con humor o enseñanza",
        "aspect": "4:5",
    },
    "meme": {
        "label": "Meme / humor",
        "desc": "Formato relatable y divertido para engagement",
        "aspect": "1:1",
    },
    "tip": {
        "label": "Tip visual",
        "desc": "Tarjeta con consejo espiritual o de tarot",
        "aspect": "1:1",
    },
    "story": {
        "label": "Story personal",
        "desc": "Historia vertical usando tu foto como protagonista",
        "aspect": "9:16",
    },
    "variacion": {
        "label": "Variación creativa",
        "desc": "Remix artístico de tu foto con estética mística",
        "aspect": "4:5",
    },
}


def creative_copy_prompt(*, estilo: str, tema: str, plataforma: str, tono: str):
    style = CREATIVE_STYLES.get(estilo, CREATIVE_STYLES["variacion"])
    return f"""Crea UN post para {plataforma} de una tarotista.
Estilo visual: {style['label']} — {style['desc']}
Tema: {tema or 'tarot y espiritualidad'}
Tono: {tono}

Devuelve en Markdown:
## Título
## Copy
(texto listo para publicar)
## Hashtags
## Idea visual
(descripción breve para generar la imagen)"""


def creative_image_prompt(*, estilo: str, tema: str, tono: str, idea_visual: str = ""):
    style = CREATIVE_STYLES.get(estilo, CREATIVE_STYLES["variacion"])
    idea = idea_visual or tema or "tarot espiritual"
    base = {
        "comic": (
            f"Cómic ilustrado de 3 viñetas sobre {idea}, estilo tarotista, "
            f"tono {tono}, colores violeta y dorado, sin texto legible en la imagen."
        ),
        "meme": (
            f"Imagen estilo meme espiritual/tarot sobre {idea}, divertida pero respetuosa, "
            f"alta calidad para Instagram."
        ),
        "tip": (
            f"Tarjeta visual de tip espiritual sobre {idea}, estética mística elegante, "
            f"iconos de tarot, luna, velas."
        ),
        "story": (
            f"Imagen vertical story con ambiente místico sobre {idea}, integrando la persona "
            f"de la foto de referencia en escena de tarot (sin copiar rostro literalmente)."
        ),
        "variacion": (
            f"Arte creativo inspirado en la foto de referencia, tema {idea}, estilo místico "
            f"moderno, tarot, aura, sin texto en la imagen."
        ),
    }
    return base.get(estilo, base["variacion"])


def create_publicaciones_from_items(
    db,
    Publicacion,
    *,
    items: list[dict],
    plataforma: str,
    material_id: int | None = None,
    origen: str = "campana_docs",
    formato_creativo: str | None = None,
    espaciar_dias: bool = False,
    imagen_path: str | None = None,
):
    created = []
    base_date = datetime.now() + timedelta(days=1)
    for idx, item in enumerate(items):
        fecha = None
        if espaciar_dias:
            d = base_date.date() + timedelta(days=idx)
            fecha = datetime.combine(d, time(10, 30))

        p = Publicacion(
            plataforma=plataforma,
            titulo=item.get("titulo") or f"Publicación {idx + 1}",
            contenido=item.get("contenido") or "",
            hashtags=item.get("hashtags") or None,
            estado="programada" if fecha else "borrador",
            fecha_programada=fecha,
            material_id=material_id,
            origen=origen,
            formato_creativo=formato_creativo or item.get("formato"),
            imagen_path=imagen_path if idx == 0 and imagen_path else None,
        )
        enrich_post_from_content(p)
        db.session.add(p)
        created.append(p)
    db.session.commit()
    return created
