import os
import tempfile

import pytest

from app import create_app
from app.extensions import db
from app.models import Cliente, Publicacion
from app.tenancy import Auditoria, Usuario


def _build_app(path):
    uri = "sqlite:///" + path.replace("\\", "/")
    return create_app(config_overrides={
        "SQLALCHEMY_DATABASE_URI": uri,
        "TESTING": True,
        "SECRET_KEY": "test-secret",
    })


@pytest.fixture
def app():
    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    application = _build_app(path)
    application.db_path = path
    yield application
    with application.app_context():
        db.engine.dispose()
    os.remove(path)


@pytest.fixture
def client(app):
    return app.test_client()


def _setup(client, perfil="servicios", negocio="Taller Norte"):
    return client.post("/setup", data={
        "nombre": "Ana Dueña",
        "email": "ana@ejemplo.test",
        "password": "clave-segura",
        "negocio": negocio,
        "perfil": perfil,
        "moneda": "CLP",
        "zona": "America/Santiago",
    }, follow_redirects=False)


def test_setup_persists_and_blocks_a_second_owner(app, client):
    assert client.get("/").headers["Location"].endswith("/setup")
    response = _setup(client)
    assert response.status_code == 302
    assert client.get("/setup").status_code == 403
    created = client.post("/clientes/nuevo", data={"nombre": "Cliente Uno"}, follow_redirects=True)
    assert created.status_code == 200
    assert b"Cliente Uno" in created.data

    again = _build_app(app.db_path)
    try:
        with again.test_client() as fresh:
            assert fresh.get("/setup").status_code == 403
            login = fresh.post("/login", data={"username": "ana@ejemplo.test", "password": "clave-segura"})
            assert login.status_code == 302
            page = fresh.get("/clientes/")
            assert b"Cliente Uno" in page.data
    finally:
        with again.app_context():
            db.engine.dispose()


def test_disabling_redes_hides_routes_and_keeps_rows(app, client):
    assert _setup(client, perfil="personal").status_code == 302
    assert client.get("/redes/").status_code == 404
    with app.app_context():
        db.session.add(Publicacion(negocio_id=1, plataforma="instagram", titulo="Borrador guardado", estado="borrador"))
        db.session.commit()
        assert Publicacion.query.execution_options(skip_tenant=True).count() == 1
    assert client.get("/proyectos/").status_code == 200
    with app.app_context():
        assert Publicacion.query.execution_options(skip_tenant=True).count() == 1


def test_negocio_isolation_and_deactivated_user(app, client):
    _setup(client)
    detail = client.post("/clientes/nuevo", data={"nombre": "Solo Norte"}, follow_redirects=True)
    assert b"Solo Norte" in detail.data
    with app.app_context():
        secreto = Cliente.query.execution_options(skip_tenant=True).filter_by(nombre="Solo Norte").one()
        secreto_id = secreto.id

    other = client.post("/negocios", data={"nombre": "Taller Sur"}, follow_redirects=True)
    assert other.status_code == 200
    invited = client.post("/ajustes/usuarios", data={
        "nombre": "Beto",
        "email": "beto@ejemplo.test",
        "password": "clave-segura",
        "rol": "vendedor",
    })
    assert invited.status_code == 302

    beto = app.test_client()
    assert beto.post("/login", data={"username": "beto@ejemplo.test", "password": "clave-segura"}).status_code == 302
    hidden = beto.get(f"/clientes/{secreto_id}")
    assert hidden.status_code == 404

    with app.app_context():
        beto_id = Usuario.query.filter_by(email="beto@ejemplo.test").one().id
    client.post(f"/ajustes/usuarios/{beto_id}/desactivar")
    rejected = beto.post("/login", data={"username": "beto@ejemplo.test", "password": "clave-segura"}, follow_redirects=True)
    assert b"incorrectos" in rejected.data

    with app.app_context():
        acciones = [row.accion for row in Auditoria.query.execution_options(skip_tenant=True).all()]
    assert "alta_cliente" in acciones
    assert "desactivar_usuario" in acciones
