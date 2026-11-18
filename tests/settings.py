"""Configuración aislada; no requiere ni toca SQL Server."""
import os
os.environ.setdefault("DJANGO_SECRET_KEY", "only-for-isolated-ui-tests-not-production")
from config.settings import *  # noqa: F403,E402
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
DEBUG = True
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
MIGRATION_MODULES = dict.fromkeys(["instituciones", "cuentas", "autenticacion", "cuidadores", "retiros", "chat", "auditoria"])

