"""Vista previa LOCAL y explícita del panel; nunca usar en despliegue.

SQLite permite revisar el frontend sin instalar SQL Server. No reproduce
el trigger SQL de auditoría ni Redis. No importa variables de otras cuentas.
"""
import os
import secrets
os.environ.setdefault("DJANGO_SECRET_KEY", secrets.token_urlsafe(48))
from .settings import *  # noqa: E402,F403

DEBUG = True
ESCOLAR_PREVIEW = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost", "testserver"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR.parent / ".preview.sqlite3"}}
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = False
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
MIGRATION_MODULES = dict.fromkeys(["instituciones", "cuentas", "autenticacion", "cuidadores", "retiros", "chat", "auditoria"])
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
REDIS_URL = "redis://127.0.0.1:6399/0"
