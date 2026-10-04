from datetime import datetime, date
from .extensions import db
from .tenancy import TenantMixin


class ProductoCatalogo(TenantMixin, db.Model):
    __tablename__ = "productos_catalogo"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(60), unique=True, nullable=False)
    nombre = db.Column(db.String(120), nullable=False)
    descripcion = db.Column(db.Text)
    precio_mensual_sugerido = db.Column(db.Float, default=0)
    setup_sugerido = db.Column(db.Float, default=0)
    nicho = db.Column(db.String(80))
    link_landing = db.Column(db.String(300))
    link_demo = db.Column(db.String(300))
    pdf_comercial_path = db.Column(db.String(300))
    activo = db.Column(db.Boolean, default=True)
    planes_json = db.Column(db.Text)  # JSON con planes sugeridos
    creado = db.Column(db.DateTime, default=datetime.utcnow)


class PropuestaComercial(TenantMixin, db.Model):
    __tablename__ = "propuestas_comerciales"
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    producto = db.Column(db.String(120))
    plan = db.Column(db.String(80))
    setup = db.Column(db.Float, default=0)
    mensualidad = db.Column(db.Float, default=0)
    descuento_setup = db.Column(db.Float, default=0)
    descuento_mensualidad = db.Column(db.Float, default=0)
    duracion_minima = db.Column(db.Integer, default=0)
    fecha_emision = db.Column(db.Date, default=date.today)
    fecha_vencimiento = db.Column(db.Date)
    estado = db.Column(db.String(30), default="borrador")
    condiciones = db.Column(db.Text)
    observaciones = db.Column(db.Text)
    incluye = db.Column(db.Text)
    creado = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship("Cliente", backref="propuestas")
    venta = db.relationship("Venta", backref="propuesta", uselist=False)


class Venta(TenantMixin, db.Model):
    __tablename__ = "ventas"
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    propuesta_id = db.Column(db.Integer, db.ForeignKey("propuestas_comerciales.id"))
    producto = db.Column(db.String(120))
    plan = db.Column(db.String(80))
    setup_cobrado = db.Column(db.Float, default=0)
    mensualidad_cobrada = db.Column(db.Float, default=0)
    monto_total_primer_pago = db.Column(db.Float, default=0)
    fecha_cierre = db.Column(db.Date, default=date.today)
    fecha_pago = db.Column(db.Date)
    estado_pago = db.Column(db.String(30), default="pendiente")
    metodo_pago = db.Column(db.String(40))
    comprobante_path = db.Column(db.String(300))
    observaciones = db.Column(db.Text)
    vendedor = db.Column(db.String(80))
    creado = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship("Cliente", backref="ventas")
    comisiones = db.relationship("Comision", backref="venta", cascade="all, delete-orphan")


class Comision(TenantMixin, db.Model):
    __tablename__ = "comisiones"
    id = db.Column(db.Integer, primary_key=True)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"), nullable=False)
    vendedor = db.Column(db.String(80))
    tipo_comision = db.Column(db.String(30), default="base")
    porcentaje = db.Column(db.Float, default=0)
    base_calculo = db.Column(db.Float, default=0)
    monto_comision = db.Column(db.Float, default=0)
    estado = db.Column(db.String(30), default="pendiente")
    fecha_generacion = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_pago = db.Column(db.Date)
    observaciones = db.Column(db.Text)


class ConfigComision(TenantMixin, db.Model):
    __tablename__ = "config_comision"
    id = db.Column(db.Integer, primary_key=True)
    porcentaje_base = db.Column(db.Float, default=50.0)
    porcentaje_alto_ticket = db.Column(db.Float, default=30.0)
    umbral_alto_ticket = db.Column(db.Float, default=500000.0)
    acumula_alto_ticket = db.Column(db.Boolean, default=True)


class Onboarding(TenantMixin, db.Model):
    __tablename__ = "onboardings"
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    venta_id = db.Column(db.Integer, db.ForeignKey("ventas.id"))
    producto = db.Column(db.String(120))
    estado = db.Column(db.String(40), default="en curso")
    creado = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship("Cliente", backref="onboardings")
    items = db.relationship("OnboardingItem", backref="onboarding", cascade="all, delete-orphan")


class OnboardingItem(TenantMixin, db.Model):
    __tablename__ = "onboarding_items"
    id = db.Column(db.Integer, primary_key=True)
    onboarding_id = db.Column(db.Integer, db.ForeignKey("onboardings.id"), nullable=False)
    titulo = db.Column(db.String(200), nullable=False)
    estado = db.Column(db.String(30), default="pendiente")
    responsable = db.Column(db.String(80))
    fecha_limite = db.Column(db.Date)
    notas = db.Column(db.Text)
    orden = db.Column(db.Integer, default=0)


class MaterialComercial(TenantMixin, db.Model):
    __tablename__ = "materiales_comerciales"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    producto = db.Column(db.String(120))
    tipo = db.Column(db.String(40))
    archivo_path = db.Column(db.String(300))
    link_externo = db.Column(db.String(500))
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    creado = db.Column(db.DateTime, default=datetime.utcnow)


class ClienteMaterial(TenantMixin, db.Model):
    __tablename__ = "cliente_materiales"
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("materiales_comerciales.id"))
    nombre = db.Column(db.String(200))
    archivo_path = db.Column(db.String(300))
    notas = db.Column(db.Text)
    creado = db.Column(db.DateTime, default=datetime.utcnow)

    cliente = db.relationship("Cliente", backref="materiales_adjuntos")
    material = db.relationship("MaterialComercial")


class PlantillaMensaje(TenantMixin, db.Model):
    __tablename__ = "plantillas_mensaje"
    id = db.Column(db.Integer, primary_key=True)
    producto = db.Column(db.String(120))
    canal = db.Column(db.String(40))
    etapa = db.Column(db.String(60))
    titulo = db.Column(db.String(200))
    cuerpo = db.Column(db.Text, nullable=False)
    activo = db.Column(db.Boolean, default=True)


class SaasCuenta(TenantMixin, db.Model):
    """Cuenta de cliente en un portal (login en /portal/<slug>/acceso)."""
    __tablename__ = "saas_cuentas"
    __table_args__ = (
        db.UniqueConstraint("portal_slug", "email", name="uq_saas_portal_email"),
    )

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    portal_slug = db.Column(db.String(60), nullable=False, index=True)
    nombre_negocio = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    plan = db.Column(db.String(80))
    estado = db.Column(db.String(30), default="activo")  # activo, suspendido
    activo = db.Column(db.Boolean, default=True)
    notas = db.Column(db.Text)
    creado = db.Column(db.DateTime, default=datetime.utcnow)
    ultimo_acceso = db.Column(db.DateTime)

    cliente = db.relationship("Cliente", backref="saas_cuentas")

    def set_password(self, password: str) -> None:
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        from werkzeug.security import check_password_hash

        return check_password_hash(self.password_hash, password)

    @property
    def portal_label(self) -> str:
        from .commercial.saas_constants import SAAS_PORTAL_LABELS

        return SAAS_PORTAL_LABELS.get(self.portal_slug, self.portal_slug)


class SaasHerramientaRegistro(TenantMixin, db.Model):
    """Datos guardados desde herramientas de valor agregado (/herramientas)."""
    __tablename__ = "saas_herramienta_registros"

    id = db.Column(db.Integer, primary_key=True)
    saas_cuenta_id = db.Column(db.Integer, db.ForeignKey("saas_cuentas.id"), nullable=False, index=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False, index=True)
    portal_slug = db.Column(db.String(60), nullable=False, index=True)
    tool_slug = db.Column(db.String(80), nullable=False, index=True)
    titulo = db.Column(db.String(200), nullable=False)
    payload_json = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String(40), default="activo")  # activo, campana_pendiente, alerta, completado
    fecha_evento = db.Column(db.Date)  # próximo mantenimiento, asamblea, etc.
    creado = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    saas_cuenta = db.relationship("SaasCuenta", backref="herramienta_registros")
    cliente = db.relationship("Cliente", backref="saas_herramienta_registros")

    def payload(self) -> dict:
        import json

        try:
            return json.loads(self.payload_json or "{}")
        except json.JSONDecodeError:
            return {}

    def set_payload(self, data: dict) -> None:
        import json

        self.payload_json = json.dumps(data, ensure_ascii=False)

