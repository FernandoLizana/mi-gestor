"""Montaje opcional bajo un prefijo WSGI, por ejemplo /crm."""

import os

from app import create_app

CRM_MOUNT_PATH = (os.environ.get("CRM_MOUNT_PATH") or "").strip().rstrip("/") or "/crm"


class ScriptNameMiddleware:
    def __init__(self, app, script_name: str):
        self.app = app
        self.script_name = script_name.rstrip("/")

    def __call__(self, environ, start_response):
        environ["SCRIPT_NAME"] = self.script_name
        return self.app(environ, start_response)


_crm_wsgi = None


def get_crm_application():
    global _crm_wsgi
    if _crm_wsgi is None:
        flask_app = create_app(mount_path=CRM_MOUNT_PATH)
        _crm_wsgi = ScriptNameMiddleware(flask_app, CRM_MOUNT_PATH)
    return _crm_wsgi


class LazyCRMWSGI:
    """Retrasa la carga hasta el primer request."""

    def __call__(self, environ, start_response):
        return get_crm_application()(environ, start_response)


def lazy_crm_application():
    return LazyCRMWSGI()
