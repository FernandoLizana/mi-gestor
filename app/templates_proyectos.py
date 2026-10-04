"""Plantillas de proyecto reutilizables.
Cada plantilla define una secuencia de tareas con duraciones (en días) relativas
al inicio del proyecto. Al instanciarla, se calculan las fechas reales.
"""

PLANTILLAS = {
    "sercotec": {
        "nombre": "Postulación Sercotec (Capital Semilla / Crece)",
        "descripcion": "Plantilla estándar para preparar y postular un proyecto a Sercotec.",
        "duracion_dias": 45,
        "tareas": [
            ("Lectura de bases y verificación de requisitos", 0, 3),
            ("Levantamiento de información del negocio", 3, 7),
            ("Definición de inversiones y cotizaciones", 10, 7),
            ("Redacción del proyecto (modelo, mercado, propuesta)", 17, 12),
            ("Revisión interna y ajustes", 29, 4),
            ("Carga en plataforma Sercotec", 33, 5),
            ("Subsanación de observaciones (post-cierre)", 38, 7),
        ],
    },
    "corfo": {
        "nombre": "Postulación Corfo (Semilla Inicia / Expande)",
        "descripcion": "Plantilla para postular a instrumentos Corfo.",
        "duracion_dias": 60,
        "tareas": [
            ("Análisis de bases y diagnóstico de elegibilidad", 0, 4),
            ("Validación de problema/solución", 4, 10),
            ("Plan de trabajo y cronograma", 14, 7),
            ("Estructura financiera y co-financiamiento", 21, 7),
            ("Redacción técnica del proyecto", 28, 15),
            ("Cartas de compromiso y anexos", 43, 7),
            ("Carga y envío en plataforma", 50, 5),
            ("Pitch y eventual entrevista", 55, 5),
        ],
    },
    "rebranding": {
        "nombre": "Rebranding / Identidad de marca",
        "descripcion": "Plantilla para proyectos de rediseño de marca y bajada a redes.",
        "duracion_dias": 45,
        "tareas": [
            ("Brief y reunión de descubrimiento", 0, 3),
            ("Investigación de mercado y benchmark", 3, 5),
            ("Moodboard y dirección de arte", 8, 4),
            ("Diseño de logo (3 propuestas)", 12, 7),
            ("Iteraciones y aprobación", 19, 5),
            ("Manual de marca (colores, tipografías, usos)", 24, 7),
            ("Plantillas para redes sociales", 31, 7),
            ("Plan de contenidos de lanzamiento", 38, 7),
        ],
    },
    "ds1": {
        "nombre": "Postulación Subsidio DS1 (clase media)",
        "descripcion": "Checklist y pasos para postular al subsidio DS1 del MINVU.",
        "duracion_dias": 30,
        "tareas": [
            ("Verificar Registro Social de Hogares actualizado", 0, 3),
            ("Reunir ahorro mínimo en libreta", 0, 5),
            ("Obtener cartola histórica de ahorro", 3, 2),
            ("Reunir documentos (CI, cert. nacimiento, etc.)", 5, 5),
            ("Simular en sitio MINVU y elegir tramo", 7, 2),
            ("Postulación en línea (durante el llamado)", 10, 5),
            ("Seguimiento de resultados", 15, 15),
        ],
    },
    "ds19": {
        "nombre": "Postulación Subsidio DS19 (Integración Social)",
        "descripcion": "Pasos para postular a una vivienda DS19.",
        "duracion_dias": 25,
        "tareas": [
            ("Buscar proyectos DS19 disponibles en la zona", 0, 5),
            ("Reservar con la inmobiliaria", 5, 3),
            ("Verificar RSH y ahorro", 5, 3),
            ("Reunir documentación", 8, 5),
            ("Postulación con la inmobiliaria", 13, 7),
            ("Seguimiento del subsidio", 20, 5),
        ],
    },
    "lanzamiento_redes": {
        "nombre": "Lanzamiento de campaña en redes",
        "descripcion": "Campaña de 4 semanas en IG / FB / LinkedIn.",
        "duracion_dias": 35,
        "tareas": [
            ("Definir objetivo y KPI", 0, 2),
            ("Definir audiencia y mensajes clave", 2, 3),
            ("Calendario editorial 4 semanas", 5, 4),
            ("Producción de piezas (foto/video/copy)", 9, 10),
            ("Programación de publicaciones", 19, 3),
            ("Ejecución y community management", 22, 10),
            ("Reporte de métricas y aprendizajes", 32, 3),
        ],
    },
}
