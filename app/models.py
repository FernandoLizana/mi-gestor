from datetime import datetime, date
from .extensions import db
from .tenancy import TenantMixin


# ---------------- CRM ----------------
class Cliente(TenantMixin, db.Model):
    __tablename__ = "clientes"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    empresa = db.Column(db.String(150))
    rut = db.Column(db.String(20))
    email = db.Column(db.String(150))
    telefono = db.Column(db.String(50))
    direccion = db.Column(db.String(250))
    instagram = db.Column(db.String(100))
    linkedin = db.Column(db.String(200))
    facebook = db.Column(db.String(200))
    estado = db.Column(db.String(40), default="prospecto")  # prospecto, activo, inactivo, cerrado
    fuente = db.Column(db.String(80))  # de dónde llegó
    notas = db.Column(db.Text)
    creado = db.Column(db.DateTime, default=datetime.utcnow)

    interacciones = db.relationship("Interaccion", backref="cliente", cascade="all, delete-orphan")
    proyectos = db.relationship("Proyecto", backref="cliente")

    # --- Campos comerciales (Mi Gestor ventas SaaS) ---
    tipo_registro = db.Column(db.String(40), default="prospecto")
    nombre_contacto = db.Column(db.String(150))
    cargo_contacto = db.Column(db.String(100))
    nicho = db.Column(db.String(80))
    producto_interes = db.Column(db.String(120))
    comuna = db.Column(db.String(80))
    ciudad = db.Column(db.String(80))
    region = db.Column(db.String(80))
    tiktok = db.Column(db.String(100))
    sitio_web = db.Column(db.String(300))
    whatsapp = db.Column(db.String(50))
    prioridad = db.Column(db.String(20), default="media")
    temperatura = db.Column(db.String(20), default="frio")
    estado_pipeline = db.Column(db.String(40), default="Nuevo")
    dolor_detectado = db.Column(db.Text)
    motivo_encaje = db.Column(db.Text)
    plan_sugerido = db.Column(db.String(80))
    setup_estimado = db.Column(db.Float)
    mensualidad_estimada = db.Column(db.Float)
    monto_oportunidad = db.Column(db.Float)
    probabilidad_cierre = db.Column(db.Integer)
    fecha_primer_contacto = db.Column(db.Date)
    fecha_ultimo_contacto = db.Column(db.DateTime)
    fecha_proximo_seguimiento = db.Column(db.Date)
    proxima_accion = db.Column(db.String(250))
    responsable = db.Column(db.String(80))
    mensaje_sugerido = db.Column(db.Text)
    tags = db.Column(db.String(300))
    activo = db.Column(db.Boolean, default=True)
    actualizado = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def nombre_negocio(self):
        return self.empresa or self.nombre

    @property
    def display_nombre(self):
        return self.empresa or self.nombre_contacto or self.nombre


class Interaccion(TenantMixin, db.Model):
    __tablename__ = "interacciones"
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    canal = db.Column(db.String(40))  # email, whatsapp, instagram, llamada, reunión
    tipo = db.Column(db.String(40))
    resumen = db.Column(db.Text, nullable=False)
    resultado = db.Column(db.String(200))
    detalle = db.Column(db.Text)
    proxima_accion = db.Column(db.String(250))
    proxima_fecha = db.Column(db.Date)
    usuario_responsable = db.Column(db.String(80))


# ---------------- Proyectos / Gantt ----------------
class Proyecto(TenantMixin, db.Model):
    __tablename__ = "proyectos"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"))
    estado = db.Column(db.String(40), default="planificación")  # planificación, en curso, pausado, completado
    fecha_inicio = db.Column(db.Date, default=date.today)
    fecha_fin = db.Column(db.Date)
    presupuesto = db.Column(db.Float, default=0)
    creado = db.Column(db.DateTime, default=datetime.utcnow)

    # Campos del wizard guiado
    tipo = db.Column(db.String(40))  # servicio, producto, fondo, vivienda, marketing, otro
    objetivo = db.Column(db.Text)  # qué se quiere lograr
    usa_redes = db.Column(db.Boolean, default=False)
    plataformas_redes = db.Column(db.String(200))  # csv: instagram,linkedin,...
    frecuencia_posts = db.Column(db.Integer, default=0)  # posts por semana

    tareas = db.relationship("Tarea", backref="proyecto", cascade="all, delete-orphan", order_by="Tarea.fecha_inicio")
    metas = db.relationship("Meta", backref="proyecto", cascade="all, delete-orphan")
    plan_ventas = db.relationship("PlanVentas", backref="proyecto", uselist=False, cascade="all, delete-orphan")
    estrategia = db.relationship("EstrategiaIA", backref="proyecto", uselist=False, cascade="all, delete-orphan")


class Meta(TenantMixin, db.Model):
    __tablename__ = "metas"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    valor_objetivo = db.Column(db.Float, default=0)
    valor_actual = db.Column(db.Float, default=0)
    unidad = db.Column(db.String(40))  # CLP, unidades, leads, seguidores, %


class PlanVentas(TenantMixin, db.Model):
    __tablename__ = "planes_ventas"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=False, unique=True)
    precio_unitario = db.Column(db.Float, default=0)
    unidades_meta = db.Column(db.Integer, default=0)
    canales = db.Column(db.String(300))  # csv: web,instagram,referidos,ferias,...
    conversion_estimada = db.Column(db.Float, default=0)  # %
    notas = db.Column(db.Text)


class EstrategiaIA(TenantMixin, db.Model):
    __tablename__ = "estrategias_ia"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=False, unique=True)
    contenido = db.Column(db.Text)  # Markdown
    fuente = db.Column(db.String(40), default="heurística")  # heurística, openai, claude, manual
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


class Tarea(TenantMixin, db.Model):
    __tablename__ = "tareas"
    id = db.Column(db.Integer, primary_key=True)
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    progreso = db.Column(db.Integer, default=0)  # 0-100
    dependencias = db.Column(db.String(250))  # ids separados por coma


# ---------------- Redes Sociales ----------------
class Publicacion(TenantMixin, db.Model):
    __tablename__ = "publicaciones"
    id = db.Column(db.Integer, primary_key=True)
    plataforma = db.Column(db.String(30), nullable=False)  # instagram, linkedin, facebook, tiktok
    titulo = db.Column(db.String(200))
    contenido = db.Column(db.Text)
    hashtags = db.Column(db.String(500))
    fecha_programada = db.Column(db.DateTime)
    estado = db.Column(db.String(30), default="borrador")  # borrador, programada, publicada
    proyecto_id = db.Column(db.Integer, db.ForeignKey("proyectos.id"))
    creado = db.Column(db.DateTime, default=datetime.utcnow)
    # métricas (post-publicación, manuales)
    vistas = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    comentarios = db.Column(db.Integer, default=0)
    compartidos = db.Column(db.Integer, default=0)
    imagen_path = db.Column(db.String(300))  # ruta relativa en uploads/
    material_id = db.Column(db.Integer, db.ForeignKey("materiales_publicidad.id"))
    origen = db.Column(db.String(40))  # manual, campana_docs, estudio_creativo
    formato_creativo = db.Column(db.String(40))  # comic, meme, tip, carrusel, etc.

    material = db.relationship("MaterialPublicidad", backref="publicaciones")


class MaterialPublicidad(TenantMixin, db.Model):
    """PDFs, papers o imágenes fuente para campañas de contenido."""
    __tablename__ = "materiales_publicidad"
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    archivo_path = db.Column(db.String(300), nullable=False)
    tipo_archivo = db.Column(db.String(20))  # pdf, imagen
    texto_extraido = db.Column(db.Text)
    notas = db.Column(db.Text)
    publicaciones_generadas = db.Column(db.Integer, default=0)
    creado = db.Column(db.DateTime, default=datetime.utcnow)


class TareaSocial(TenantMixin, db.Model):
    """Recordatorios: contactar a alguien, enviar DM, etc."""
    __tablename__ = "tareas_sociales"
    id = db.Column(db.Integer, primary_key=True)
    plataforma = db.Column(db.String(30))
    tipo = db.Column(db.String(40))  # DM, comentar, seguir, responder
    objetivo = db.Column(db.String(200))  # @usuario, link, etc.
    mensaje = db.Column(db.Text)
    fecha = db.Column(db.DateTime)
    completada = db.Column(db.Boolean, default=False)
    notas = db.Column(db.Text)


class MetricaTikTok(TenantMixin, db.Model):
    __tablename__ = "metricas_tiktok"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=date.today)
    seguidores = db.Column(db.Integer, default=0)
    vistas_perfil = db.Column(db.Integer, default=0)
    vistas_videos = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    comentarios = db.Column(db.Integer, default=0)
    compartidos = db.Column(db.Integer, default=0)
    notas = db.Column(db.String(250))


class MetricaInstagram(TenantMixin, db.Model):
    __tablename__ = "metricas_instagram"
    id = db.Column(db.Integer, primary_key=True)
    fecha = db.Column(db.Date, default=date.today)
    seguidores = db.Column(db.Integer, default=0)
    alcance = db.Column(db.Integer, default=0)
    impresiones = db.Column(db.Integer, default=0)
    likes = db.Column(db.Integer, default=0)
    comentarios = db.Column(db.Integer, default=0)
    guardados = db.Column(db.Integer, default=0)
    notas = db.Column(db.String(250))


class ProspectoIA(TenantMixin, db.Model):
    __tablename__ = "prospectos_ia"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150))
    plataforma = db.Column(db.String(40))
    perfil_url = db.Column(db.String(500))
    bio = db.Column(db.Text)
    publicaciones = db.Column(db.Text)
    objetivo = db.Column(db.Text)
    oferta = db.Column(db.Text)
    tono = db.Column(db.String(40), default="cercano")
    analisis = db.Column(db.Text)
    mensaje = db.Column(db.Text)
    estado = db.Column(db.String(40), default="nuevo")
    historial_contacto = db.Column(db.Text)
    ultimo_contacto = db.Column(db.DateTime)
    creado = db.Column(db.DateTime, default=datetime.utcnow)


from .models_commercial import (  # noqa: E402, F401
    ProductoCatalogo,
    PropuestaComercial,
    Venta,
    Comision,
    ConfigComision,
    Onboarding,
    OnboardingItem,
    MaterialComercial,
    ClienteMaterial,
    PlantillaMensaje,
    SaasCuenta,
    SaasHerramientaRegistro,
)
