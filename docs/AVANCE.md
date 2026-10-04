# Avance Mi Gestor

Checkpoint de la fase 1. El inventario de partida está en el canvas `mi-gestor.canvas.tsx`.

## Qué quedó funcionando

- Una instalación vacía abre `/setup`, crea al propietario y no vuelve a dejarse tomar.
- Los datos ya existentes se asignan a un negocio inicial y el asistente solo pide al propietario, sin borrarlos ni recargar ejemplos.
- Los ejemplos ficticios solo entran si se marcan en una instalación nueva.
- Cada negocio tiene módulos. Apagar redes responde 404 en esas rutas y no borra publicaciones.
- Dos negocios no comparten clientes: el servidor filtra por el negocio de la sesión, no por un id enviado en el formulario.
- Usuarios con contraseña hasheada, roles y desactivación. La clave compartida del `.env` ya no abre la sesión.
- Respaldo SQLite desde Ajustes y también antes de la migración `001_negocio`, en `backups/`.
- Auditoría de la configuración inicial, altas de cliente, módulos, usuarios y respaldos.

## Matriz

| ID | Estado | Evidencia | Pendiente |
| --- | --- | --- | --- |
| MG-01 | Hecho en esta copia | `/setup`, prueba `test_setup_persists_and_blocks_a_second_owner` | Recuperación de contraseña del propietario |
| MG-02 | Hecho para los módulos con pantalla | Nav y `guard_request`. Prueba de redes | Tiempo y finanzas todavía no tienen pantallas |
| MG-03 | Parcial | Negocios, selector y filtro de lectura/escritura | Falta el mismo filtro en archivos `/uploads/` |
| MG-04 | Parcial | Usuarios, roles, desactivación, auditoría de altas | Invitación por correo, cliente de portal, permisos finos de montos y adjuntos |
| MG-05 | Ausente | El pipeline sigue fijo en código | Etapas editables |
| MG-06 | Ausente | La ficha de cliente ya junta interacciones | Duplicados y fusión |
| MG-07 | Ausente | El tablero lista vencimientos, no es una agenda accionable | Completar y posponer desde un solo lugar |
| MG-08 | Ausente | No hay motor de reglas | |
| MG-09 | Ausente | Hay lista y Gantt, no Kanban de tareas | |
| MG-10 | Ausente | | Capacidad semanal |
| MG-11 | Ausente | | Tiempo y cronómetro |
| MG-12 | Ausente | El PDF actual no versiona partidas | |
| MG-13 | Ausente | La venta guarda un estado de pago, no cuotas | |
| MG-14 | Ausente | | Caja |
| MG-15 | Ausente | Las cuentas de portal no son un portal autónomo | |
| MG-16 | Ausente | Hay plantillas fijas de proyecto y mensajes | Versiones exportables |
| MG-17 | Ausente | | Campañas y origen |
| MG-18 | Parcial previo | La IA ya redacta si hay API key | Vista previa, permisos y no enviar sola |
| MG-19 | Ausente | Hay manifiesto PWA, sin cola offline | |
| MG-20 | Parcial | Respaldo de archivo SQLite | Exportar un negocio y restaurarlo en otra instalación |

## Siguiente paso

MG-06 y MG-07: ficha con cronología y agenda que complete el seguimiento original. Antes, cerrar el hueco de `/uploads/` para que un negocio no descargue archivos de otro si conoce el nombre.

## Cómo probar esta fase

```powershell
.\.venv\Scripts\python.exe -m pip install pytest==8.3.3
.\.venv\Scripts\python.exe -m pytest tests/test_fase1.py
```

Al arrancar la copia local que ya tenía datos, entra a `/setup` y crea al propietario. La cuenta compartida anterior ya no abre la sesión.
