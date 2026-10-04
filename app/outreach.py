from .ai import AIConfigError, generate_text, is_ai_configured


SYSTEM_PROMPT = """Eres un asistente de prospección ética para uso profesional.
Tu trabajo es analizar información proporcionada manualmente por el usuario y redactar mensajes personalizados.
No inventes datos, no finjas una relación previa, no uses manipulación emocional y no prometas resultados falsos.
Si falta información, dilo claramente. El mensaje debe ser breve, humano y específico."""


def build_profile_context(*, nombre, plataforma, perfil_url, bio, publicaciones, objetivo, oferta):
    partes = [
        f"Nombre/contacto: {nombre or 'No especificado'}",
        f"Plataforma: {plataforma or 'No especificada'}",
        f"URL del perfil: {perfil_url or 'No especificada'}",
        f"Bio/resumen visible: {bio or 'No proporcionado'}",
        f"Publicaciones, intereses o señales relevantes: {publicaciones or 'No proporcionadas'}",
        f"Contexto u objetivo del contacto: {objetivo or 'No especificado'}",
        f"Oferta, propuesta o motivo legítimo para contactar: {oferta or 'No especificada'}",
    ]
    return "\n".join(partes)


def generate_outreach_draft(*, nombre=None, plataforma=None, perfil_url=None, bio=None,
                            publicaciones=None, objetivo=None, oferta=None, tono="cercano"):
    if not is_ai_configured():
        return _fallback_draft(nombre=nombre, plataforma=plataforma, objetivo=objetivo, oferta=oferta)

    contexto = build_profile_context(
        nombre=nombre,
        plataforma=plataforma,
        perfil_url=perfil_url,
        bio=bio,
        publicaciones=publicaciones,
        objetivo=objetivo,
        oferta=oferta,
    )
    prompt = f"""Analiza este contexto y crea un borrador de primer mensaje para contactar a esta persona.

{contexto}

Requisitos:
- Tono: {tono}.
- Máximo 900 caracteres.
- Debe mencionar 1 detalle específico del perfil si existe.
- Debe incluir una razón clara para escribirle.
- Debe cerrar con una pregunta simple.
- No debe sonar automatizado.
- No incluyas asuntos legales ni afirmes haber revisado información que no aparece en el contexto.

Devuelve solo el mensaje final."""
    try:
        return generate_text(prompt, system=SYSTEM_PROMPT, temperature=0.75, max_tokens=500)
    except AIConfigError:
        return _fallback_draft(nombre=nombre, plataforma=plataforma, objetivo=objetivo, oferta=oferta)


def _fallback_draft(*, nombre=None, plataforma=None, objetivo=None, oferta=None):
    saludo = f"Hola {nombre}" if nombre else "Hola"
    medio = f" en {plataforma}" if plataforma else ""
    motivo = objetivo or "vi que podríamos tener una conversación interesante"
    propuesta = oferta or "me gustaría contarte una idea que puede ser útil para ti"
    return f"{saludo}, ¿cómo estás? Te escribo{medio} porque {motivo}. {propuesta}. ¿Te parece si te cuento en 2 líneas y me dices si hace sentido?"
