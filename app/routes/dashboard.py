from datetime import date, timedelta, datetime, time
from flask import Blueprint, render_template
from ..database import database_status
from ..models import (
    Cliente, Proyecto, Tarea, Publicacion, TareaSocial, Interaccion, ProspectoIA,
    PropuestaComercial, Venta, Comision, Onboarding,
)

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    hoy = date.today()
    en_7 = hoy + timedelta(days=7)
    ahora = datetime.now()
    inicio_hoy = datetime.combine(hoy, time.min)
    fin_hoy = datetime.combine(hoy, time.max)

    stats = {
        "clientes": Cliente.query.count(),
        "proyectos_activos": Proyecto.query.filter(Proyecto.estado.in_(["en curso", "planificación"])).count(),
        "publicaciones_pendientes": Publicacion.query.filter(Publicacion.estado != "publicada").count(),
        "prospectos_pendientes": ProspectoIA.query.filter(
            ProspectoIA.estado.in_(["nuevo", "analizado", "mensaje_generado"])
        ).count(),
    }

    pubs_hoy = (
        Publicacion.query.filter(
            Publicacion.estado != "publicada",
            Publicacion.fecha_programada >= inicio_hoy,
            Publicacion.fecha_programada <= fin_hoy,
        )
        .order_by(Publicacion.fecha_programada)
        .all()
    )

    pubs_atrasadas = (
        Publicacion.query.filter(
            Publicacion.estado != "publicada",
            Publicacion.fecha_programada != None,
            Publicacion.fecha_programada < inicio_hoy,
        )
        .order_by(Publicacion.fecha_programada)
        .limit(8)
        .all()
    )

    pubs_sin_fecha = (
        Publicacion.query.filter(
            Publicacion.estado != "publicada",
            Publicacion.fecha_programada == None,
        )
        .order_by(Publicacion.creado.desc())
        .limit(6)
        .all()
    )

    prospectos_accion = (
        ProspectoIA.query.filter(
            ProspectoIA.estado.in_(["mensaje_generado", "analizado", "nuevo"])
        )
        .order_by(ProspectoIA.ultimo_contacto.is_(None), ProspectoIA.creado.desc())
        .limit(8)
        .all()
    )

    tareas_proximas = (
        Tarea.query.filter(Tarea.fecha_fin >= hoy, Tarea.fecha_fin <= en_7)
        .order_by(Tarea.fecha_fin)
        .limit(6)
        .all()
    )

    seguimientos = (
        Interaccion.query.filter(
            Interaccion.proxima_fecha != None,
            Interaccion.proxima_fecha <= en_7,
        )
        .order_by(Interaccion.proxima_fecha)
        .limit(6)
        .all()
    )

    tareas_sociales = (
        TareaSocial.query.filter_by(completada=False)
        .order_by(TareaSocial.fecha)
        .limit(6)
        .all()
    )

    inicio_mes = date(hoy.year, hoy.month, 1)
    seg_vencidos = Cliente.query.filter(
        Cliente.fecha_proximo_seguimiento != None,
        Cliente.fecha_proximo_seguimiento < hoy,
        ~Cliente.estado_pipeline.in_(["Cerrado ganado", "Cerrado perdido"]),
    ).count()
    seg_hoy = Cliente.query.filter(Cliente.fecha_proximo_seguimiento == hoy).count()
    ventas_mes = Venta.query.filter(Venta.fecha_cierre >= inicio_mes).all()
    monto_mes = sum(v.monto_total_primer_pago or 0 for v in ventas_mes)
    mrr_mes = sum(v.mensualidad_cobrada or 0 for v in ventas_mes)
    com_pend = Comision.query.filter_by(estado="pendiente").all()
    com_pagadas_mes = Comision.query.filter(
        Comision.estado == "pagada",
        Comision.fecha_pago >= inicio_mes,
    ).all()
    embudo = {
        "nuevos": Cliente.query.filter_by(estado_pipeline="Nuevo").count(),
        "contactados": Cliente.query.filter(Cliente.estado_pipeline.in_(["Contactado", "Respondió"])).count(),
        "demos": Cliente.query.filter(Cliente.estado_pipeline.in_(["Demo agendada", "Demo realizada"])).count(),
        "propuestas": Cliente.query.filter_by(estado_pipeline="Propuesta enviada").count(),
        "cerrados": Cliente.query.filter_by(estado_pipeline="Cerrado ganado").count(),
        "perdidos": Cliente.query.filter_by(estado_pipeline="Cerrado perdido").count(),
    }
    prop_pendientes = PropuestaComercial.query.filter(
        PropuestaComercial.estado.in_(["borrador", "enviada"])
    ).count()
    alertas = {
        "calientes_sin_seg": Cliente.query.filter(
            Cliente.temperatura == "caliente",
            Cliente.fecha_proximo_seguimiento == None,
        ).count(),
        "prop_por_vencer": PropuestaComercial.query.filter(
            PropuestaComercial.estado == "enviada",
            PropuestaComercial.fecha_vencimiento != None,
            PropuestaComercial.fecha_vencimiento <= hoy + timedelta(days=3),
        ).count(),
        "sin_onboarding": Onboarding.query.filter_by(estado="en curso").count(),
        "com_sin_aprobar": len(com_pend),
    }

    return render_template(
        "dashboard.html",
        stats=stats,
        db_status=database_status(),
        hoy=hoy,
        ahora=ahora,
        pubs_hoy=pubs_hoy,
        pubs_atrasadas=pubs_atrasadas,
        pubs_sin_fecha=pubs_sin_fecha,
        prospectos_accion=prospectos_accion,
        tareas_proximas=tareas_proximas,
        seguimientos=seguimientos,
        tareas_sociales=tareas_sociales,
        comercial={
            "seg_vencidos": seg_vencidos,
            "seg_hoy": seg_hoy,
            "ventas_mes": len(ventas_mes),
            "monto_mes": monto_mes,
            "mrr_mes": mrr_mes,
            "com_pendiente": sum(c.monto_comision for c in com_pend),
            "com_pagada_mes": sum(c.monto_comision for c in com_pagadas_mes),
            "embudo": embudo,
            "prop_pendientes": prop_pendientes,
            "alertas": alertas,
        },
    )
