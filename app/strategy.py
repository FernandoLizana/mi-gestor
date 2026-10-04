"""Generador de estrategia recomendada según el tipo de proyecto.

No requiere API externa. Si el usuario configura una API de IA en el futuro,
se puede sustituir esta función por una llamada al LLM manteniendo la firma.
"""
import requests

from .ai import AIConfigError, generate_text, is_ai_configured


def generate_strategy(*, tipo, nombre, objetivo, usa_redes, plataformas, frecuencia,
                      tiene_ventas, precio, unidades_meta, canales, conversion):
    """Devuelve un texto Markdown con la estrategia recomendada."""
    if is_ai_configured():
        try:
            return _generate_ai_strategy(
                tipo=tipo,
                nombre=nombre,
                objetivo=objetivo,
                usa_redes=usa_redes,
                plataformas=plataformas,
                frecuencia=frecuencia,
                tiene_ventas=tiene_ventas,
                precio=precio,
                unidades_meta=unidades_meta,
                canales=canales,
                conversion=conversion,
            )
        except (AIConfigError, KeyError, requests.RequestException):
            pass

    s = []
    s.append(f"# Estrategia recomendada — {nombre}\n")
    if objetivo:
        s.append(f"**Objetivo declarado:** {objetivo}\n")

    # Sección por tipo de proyecto
    s.append("## 1. Enfoque general\n")
    s.append(_enfoque_por_tipo(tipo))

    # Hitos críticos
    s.append("\n## 2. Hitos críticos a cumplir\n")
    s.extend(_hitos(tipo))

    # Redes sociales
    if usa_redes:
        s.append("\n## 3. Estrategia de contenidos (redes)\n")
        s.extend(_estrategia_redes(plataformas, frecuencia, tipo))
    else:
        s.append("\n## 3. Comunicación\n")
        s.append("- Como no se usarán redes sociales en este proyecto, prioriza canales directos (email, WhatsApp, llamadas, referidos).")
        s.append("- Documenta los puntos de contacto con el cliente para no perder oportunidades de venta.")

    # Plan de ventas
    if tiene_ventas:
        s.append("\n## 4. Embudo de ventas\n")
        s.extend(_embudo_ventas(precio, unidades_meta, canales, conversion))
    else:
        s.append("\n## 4. Sin venta directa\n")
        s.append("- Define igualmente un KPI claro (ej. cantidad de leads, monto adjudicado, alcance) para medir el éxito.")

    # Riesgos y validaciones
    s.append("\n## 5. Riesgos típicos y mitigación\n")
    s.extend(_riesgos(tipo))

    # Próximos pasos
    s.append("\n## 6. Tus próximos 3 pasos\n")
    s.extend(_proximos_pasos(tipo, usa_redes, tiene_ventas))

    return "\n".join(s)


def _generate_ai_strategy(*, tipo, nombre, objetivo, usa_redes, plataformas, frecuencia,
                          tiene_ventas, precio, unidades_meta, canales, conversion):
    system = """Eres un consultor senior en estrategia comercial, gestión de proyectos,
marketing digital y postulación a fondos en Chile. Responde en español chileno claro,
práctico y accionable. No inventes datos. Si falta información, declara supuestos."""
    prompt = f"""Crea una estrategia dinámica en Markdown para este proyecto:

Nombre: {nombre}
Tipo: {tipo}
Objetivo: {objetivo or 'No especificado'}
Usa redes sociales: {'sí' if usa_redes else 'no'}
Plataformas: {', '.join(plataformas) if plataformas else 'No especificadas'}
Frecuencia de publicaciones semanal: {frecuencia}
Tiene plan de ventas: {'sí' if tiene_ventas else 'no'}
Precio unitario: {precio}
Unidades meta: {unidades_meta}
Canales: {canales or 'No especificados'}
Conversión estimada: {conversion}%

Estructura requerida:
# Estrategia recomendada — {nombre}
## 1. Diagnóstico rápido
## 2. Objetivo y KPI principal
## 3. Plan de acción por etapas
## 4. Estrategia de contenidos o comunicación
## 5. Embudo comercial o seguimiento
## 6. Riesgos y mitigación
## 7. Próximos 7 días

Incluye tareas concretas, métricas y recomendaciones específicas para el contexto."""
    return generate_text(prompt, system=system, temperature=0.7, max_tokens=1800)


def _enfoque_por_tipo(tipo):
    base = {
        "fondo": (
            "Estás postulando a un fondo concursable. La clave NO es vender, es **demostrar mérito y cumplir bases**. "
            "Lee 2 veces las bases, arma una matriz de criterios de evaluación y asegúrate de que cada sección los aborde explícitamente. "
            "Reserva un 20% del tiempo solo para revisión y ajustes finales."
        ),
        "vivienda": (
            "Para postulación a subsidio habitacional (DS1/DS19) lo más importante es **tener toda la documentación lista antes del llamado**: "
            "RSH actualizado, ahorro mínimo, certificados al día y, si aplica, reserva con la inmobiliaria. "
            "El llamado es corto: si no estás listo, pierdes el ciclo."
        ),
        "marketing": (
            "Es un proyecto de marketing/comunicaciones. Define primero el **objetivo medible** (ej. +500 seguidores, 50 leads, 10 ventas). "
            "Sin objetivo cuantificable la campaña no se puede evaluar. Asigna presupuesto separado para producción, pauta y análisis."
        ),
        "producto": (
            "Estás creando o lanzando un producto. Valida la demanda **antes** de invertir en stock o desarrollo: pre-ventas, encuestas, lista de espera. "
            "Tu primer hito debería ser una venta real, no un MVP perfecto."
        ),
        "servicio": (
            "Es un proyecto de servicio para un cliente. Define al inicio el **alcance, los entregables y los criterios de aceptación**. "
            "El 80% de los problemas en proyectos de servicios vienen de un alcance mal acordado. Cierra esto antes de empezar."
        ),
        "otro": (
            "Define con claridad qué significa 'éxito' para este proyecto y un único KPI principal. "
            "Sin foco, los proyectos personales tienden a estancarse."
        ),
    }
    return base.get(tipo, base["otro"])


def _hitos(tipo):
    h = {
        "fondo": [
            "- [ ] Lectura completa de bases con resumen propio.",
            "- [ ] Verificación de elegibilidad (rubro, antigüedad, región).",
            "- [ ] Documentos legales y financieros vigentes.",
            "- [ ] Borrador del proyecto y revisión por terceros.",
            "- [ ] Carga en plataforma con 48h de holgura.",
        ],
        "vivienda": [
            "- [ ] Registro Social de Hogares actualizado.",
            "- [ ] Ahorro mínimo en libreta + cartola histórica.",
            "- [ ] Documentación completa (CI, certificados).",
            "- [ ] Simulación en sitio MINVU y elección de tramo.",
            "- [ ] Postulación durante el llamado oficial.",
        ],
        "marketing": [
            "- [ ] Objetivo SMART definido (específico, medible, alcanzable, relevante, temporal).",
            "- [ ] Audiencia y mensajes clave documentados.",
            "- [ ] Calendario editorial de al menos 4 semanas.",
            "- [ ] Producción de piezas (foto/video/copy).",
            "- [ ] Mecanismo de medición instalado antes de lanzar.",
        ],
        "producto": [
            "- [ ] Validación de mercado con potenciales clientes reales.",
            "- [ ] Prototipo o MVP funcional.",
            "- [ ] Pricing definido en base a valor, no a costo.",
            "- [ ] Primera venta real (incluso a precio simbólico).",
            "- [ ] Iteración con feedback de los primeros usuarios.",
        ],
        "servicio": [
            "- [ ] Brief firmado con alcance y entregables.",
            "- [ ] Contrato u orden de compra.",
            "- [ ] Plan de hitos y pagos.",
            "- [ ] Reuniones de avance pactadas.",
            "- [ ] Acta de cierre y solicitud de testimonio/referido.",
        ],
    }
    return h.get(tipo, [
        "- [ ] Definir entregable principal y fecha objetivo.",
        "- [ ] Identificar 3 hitos intermedios verificables.",
        "- [ ] Asignar tiempo semanal fijo al proyecto.",
    ])


def _estrategia_redes(plataformas, frecuencia, tipo):
    if not plataformas:
        plataformas = ["instagram"]
    out = [f"- **Plataformas activas:** {', '.join(plataformas)}",
           f"- **Frecuencia objetivo:** {frecuencia} publicaciones por semana"]

    consejos = {
        "instagram": "Alterna **Reels (alcance)**, carruseles educativos (guardado) y stories diarias (cercanía). Hashtags entre 8-15 mezclando nicho y locales.",
        "linkedin": "Posts texto-largo con una idea fuerte funcionan mejor que enlaces. Publica martes-jueves 8-10am. Comenta en posts de tu red antes de publicar el tuyo.",
        "facebook": "Hoy funciona más para grupos y comunidad que para feed orgánico. Considera grupo propio o publicaciones en grupos locales relevantes.",
        "tiktok": "Primeros 3 segundos lo son todo. Hook fuerte + valor concreto + CTA. Series de videos sobre un mismo tema crecen más rápido que videos sueltos.",
    }
    for p in plataformas:
        if p in consejos:
            out.append(f"- **{p.capitalize()}:** {consejos[p]}")

    out.append("- **Pilares de contenido (3):** define 3 temas recurrentes (ej. educación, detrás de cámaras, casos de éxito) y rota entre ellos.")
    out.append("- **Llamado a la acción:** cada 3 posts incluye un CTA claro (DM, link en bio, comentario).")
    if tipo == "marketing":
        out.append("- **Pauta:** considera reservar 20-30% del presupuesto para promocionar los posts que mejor desempeño orgánico tengan (1 semana después).")
    return out


def _embudo_ventas(precio, unidades_meta, canales, conversion):
    out = []
    if precio and unidades_meta:
        ingreso = precio * unidades_meta
        out.append(f"- **Meta de ingresos:** ${ingreso:,.0f} CLP ({unidades_meta} unidades × ${precio:,.0f}).".replace(",", "."))
    if conversion and unidades_meta:
        leads_necesarios = int(unidades_meta / (conversion / 100)) if conversion > 0 else 0
        out.append(f"- **Leads necesarios estimados:** ~{leads_necesarios} (asumiendo {conversion:.0f}% de conversión).")
    if canales:
        out.append(f"- **Canales de captación:** {canales}.")
        out.append("  - Asigna un porcentaje de meta a cada canal y mide semanalmente cuál convierte mejor.")
    out.append("- **Etapas del embudo:** Conocimiento → Interés (lead) → Consideración (conversación) → Decisión (venta) → Fidelización (referido).")
    out.append("- **Seguimiento:** registra **cada interacción de venta** en la ficha del cliente para no perder oportunidades por falta de continuidad.")
    return out


def _riesgos(tipo):
    r = {
        "fondo": [
            "- ⚠ **Subsanación tardía:** revisa email/plataforma diariamente después del cierre.",
            "- ⚠ **Documentos vencidos:** valida vigencias 1 semana antes de cargar.",
            "- ⚠ **Inconsistencias entre secciones:** una persona que no escribió el proyecto debe leerlo completo.",
        ],
        "vivienda": [
            "- ⚠ **RSH desactualizado** o tramo equivocado: revisa antes del llamado.",
            "- ⚠ **Ahorro insuficiente** en la fecha de corte.",
            "- ⚠ **Documentos faltantes** del cónyuge o cargas familiares.",
        ],
        "marketing": [
            "- ⚠ **Falta de constancia:** el algoritmo penaliza pausas. Mejor 3/semana sostenido que 10 una semana y nada al mes siguiente.",
            "- ⚠ **No medir:** sin métricas no sabes qué optimizar.",
            "- ⚠ **Confundir alcance con ventas:** muchos seguidores ≠ muchos clientes.",
        ],
        "producto": [
            "- ⚠ **Construir sin validar.** Habla con 10 potenciales clientes antes de invertir.",
            "- ⚠ **Sobreingeniería:** lanza simple, mejora con feedback real.",
            "- ⚠ **Stock sin venta:** evita comprar inventario antes de tener pre-pedidos.",
        ],
        "servicio": [
            "- ⚠ **Scope creep:** todo cambio fuera del alcance debe quedar por escrito y cotizarse.",
            "- ⚠ **Pagos atrasados:** define adelanto + pagos por hito.",
            "- ⚠ **Cliente que no responde:** cláusula de pausa después de X días sin feedback.",
        ],
    }
    return r.get(tipo, [
        "- ⚠ **Falta de tiempo:** bloquea horas fijas en el calendario.",
        "- ⚠ **Falta de claridad:** define entregable concreto.",
    ])


def _proximos_pasos(tipo, usa_redes, tiene_ventas):
    pasos = ["1. Revisa la carta Gantt de este proyecto y ajusta tareas si falta alguna."]
    if tipo == "fondo":
        pasos.append("2. Descarga las bases del fondo y léelas completas hoy mismo.")
    elif tipo == "vivienda":
        pasos.append("2. Verifica tu Registro Social de Hogares en registrosocial.gob.cl.")
    elif tipo == "producto":
        pasos.append("2. Identifica 5 personas con quienes validar la idea esta semana.")
    elif tipo == "servicio":
        pasos.append("2. Envía el brief al cliente para que lo apruebe por escrito.")
    elif tipo == "marketing":
        pasos.append("2. Define el KPI principal de la campaña en una sola frase.")
    else:
        pasos.append("2. Define el primer entregable verificable y su fecha.")
    if usa_redes:
        pasos.append("3. Crea los primeros 3 borradores de contenido desde el botón **Crear post** del proyecto.")
    elif tiene_ventas:
        pasos.append("3. Carga tu cartera actual de prospectos y registra al menos una interacción esta semana.")
    else:
        pasos.append("3. Agenda una revisión semanal de 15 minutos para no perder el hilo.")
    return ["- " + p for p in pasos]
