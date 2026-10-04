from datetime import date, timedelta
from .extensions import db
from .models import Cliente, Proyecto, Tarea, Publicacion


def ensure_seed():
    if Cliente.query.first():
        return

    c1 = Cliente(nombre="Juan Pérez", empresa="Panadería La Espiga", email="juan@example.com",
                 telefono="+56 9 1234 5678", estado="activo", fuente="Instagram",
                 notas="Cliente recurrente, le interesa marketing digital.")
    c2 = Cliente(nombre="María Soto", empresa="Estudio Soto Arq.", email="maria@example.com",
                 telefono="+56 9 8765 4321", estado="prospecto", fuente="LinkedIn")
    db.session.add_all([c1, c2])
    db.session.flush()

    p1 = Proyecto(nombre="Rebranding La Espiga", descripcion="Nueva identidad y redes",
                  cliente_id=c1.id, estado="en curso",
                  fecha_inicio=date.today() - timedelta(days=5),
                  fecha_fin=date.today() + timedelta(days=25),
                  presupuesto=850000)
    p2 = Proyecto(nombre="Postulación Sercotec Capital Semilla",
                  descripcion="Preparar postulación para emprendedora",
                  cliente_id=c2.id, estado="planificación",
                  fecha_inicio=date.today(),
                  fecha_fin=date.today() + timedelta(days=40))
    db.session.add_all([p1, p2])
    db.session.flush()

    tareas = [
        Tarea(proyecto_id=p1.id, nombre="Investigación de mercado",
              fecha_inicio=date.today() - timedelta(days=5),
              fecha_fin=date.today() + timedelta(days=2), progreso=80),
        Tarea(proyecto_id=p1.id, nombre="Diseño de logo",
              fecha_inicio=date.today() + timedelta(days=2),
              fecha_fin=date.today() + timedelta(days=12), progreso=20),
        Tarea(proyecto_id=p1.id, nombre="Plan de contenidos",
              fecha_inicio=date.today() + timedelta(days=10),
              fecha_fin=date.today() + timedelta(days=25), progreso=0),
        Tarea(proyecto_id=p2.id, nombre="Levantar información del negocio",
              fecha_inicio=date.today(),
              fecha_fin=date.today() + timedelta(days=7), progreso=0),
        Tarea(proyecto_id=p2.id, nombre="Redacción del proyecto",
              fecha_inicio=date.today() + timedelta(days=7),
              fecha_fin=date.today() + timedelta(days=25), progreso=0),
        Tarea(proyecto_id=p2.id, nombre="Carga en plataforma",
              fecha_inicio=date.today() + timedelta(days=25),
              fecha_fin=date.today() + timedelta(days=35), progreso=0),
    ]
    db.session.add_all(tareas)

    db.session.add(Publicacion(
        plataforma="instagram", titulo="Lanzamiento nuevo logo La Espiga",
        contenido="¡Estrenamos imagen! Te contamos la historia detrás del nuevo logo...",
        hashtags="#panaderia #rebranding #localchile",
        estado="borrador", proyecto_id=p1.id,
    ))

    db.session.commit()
