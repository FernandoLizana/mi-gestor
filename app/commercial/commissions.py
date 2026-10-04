from ..extensions import db
from ..models import Comision, ConfigComision, Venta


def get_config() -> ConfigComision:
    cfg = ConfigComision.query.first()
    if not cfg:
        cfg = ConfigComision()
        db.session.add(cfg)
        db.session.commit()
    return cfg


def calcular_comisiones_venta(venta: Venta, vendedor: str) -> list[Comision]:
    cfg = get_config()
    comisiones = []
    primer_pago = venta.monto_total_primer_pago or (venta.setup_cobrado or 0) + (venta.mensualidad_cobrada or 0)

    if primer_pago > 0:
        monto_base = primer_pago * (cfg.porcentaje_base / 100.0)
        comisiones.append(Comision(
            venta_id=venta.id,
            vendedor=vendedor,
            tipo_comision="base",
            porcentaje=cfg.porcentaje_base,
            base_calculo=primer_pago,
            monto_comision=monto_base,
            estado="pendiente",
        ))

    mensualidad = venta.mensualidad_cobrada or 0
    if mensualidad > cfg.umbral_alto_ticket:
        monto_at = mensualidad * (cfg.porcentaje_alto_ticket / 100.0)
        if cfg.acumula_alto_ticket or not comisiones:
            comisiones.append(Comision(
                venta_id=venta.id,
                vendedor=vendedor,
                tipo_comision="alto_ticket",
                porcentaje=cfg.porcentaje_alto_ticket,
                base_calculo=mensualidad,
                monto_comision=monto_at,
                estado="pendiente",
                observaciones="Comisión especial alto ticket",
            ))
        elif comisiones:
            comisiones[0].monto_comision = monto_at
            comisiones[0].tipo_comision = "alto_ticket"
            comisiones[0].porcentaje = cfg.porcentaje_alto_ticket
            comisiones[0].base_calculo = mensualidad
            comisiones[0].observaciones = "Reemplaza comisión base (no acumula)"

    return comisiones
