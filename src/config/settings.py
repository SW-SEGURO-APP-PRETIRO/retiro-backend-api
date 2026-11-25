"""Configuración del monolito modular Retiro Escolar Seguro.

Todos los valores sensibles salen de variables de entorno (.env). Nada secreto va en este archivo.
"""
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent  # .../src
env = environ.Env(DJANGO_DEBUG=(bool, False))
# Lee el .env de la raíz del repo si existe (en Docker llega como variables de entorno)
environ.Env.read_env(BASE_DIR.parent / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
PASSWORD_RESET_URL = env(
    "PASSWORD_RESET_URL",
    default="https://localhost:8443/autenticacion/restablecer/",
)

# Claves para cifrado de campos (Fernet) y firmas HMAC. Ver shared/utils/crypto.py
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY", default="")
HMAC_SIGNING_KEY = env("HMAC_SIGNING_KEY", default="")

# ---------------------------------------------------------------- Aplicaciones
INSTALLED_APPS = [
    "daphne",  # servidor ASGI (debe ir primero para que runserver use ASGI)
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "channels",
    "rest_framework",
    "drf_spectacular",
    # Utilidades transversales (comandos esperar_bd y seed_demo)
    "shared",
    # Módulos del monolito (orden = de base a cima)
    "apps.auditoria",
    "apps.instituciones",
    "apps.cuentas",
    "apps.autenticacion",
    "apps.cuidadores",
    "apps.retiros",
    "apps.chat",
]

AUTH_USER_MODEL = "cuentas.Usuario"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Fija la institución del usuario autenticado para TODA la petición (aislamiento multi-institución)
    "shared.middlewares.tenancy.TenancyMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ------------------------------------------------------------------ Base de datos
DATABASES = {
    "default": {
        "ENGINE": "mssql",
        "NAME": env("DB_NAME", default="retiro_escolar"),
        "USER": env("DB_USER", default="retiro_app"),
        "PASSWORD": env("DB_PASSWORD", default=""),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="1433"),
        "OPTIONS": {
            "driver": "ODBC Driver 18 for SQL Server",
            # El contenedor usa un certificado autofirmado: solo aceptable en entorno local
            "extra_params": "TrustServerCertificate=yes",
        },
        # Cada petición reutiliza la conexión unos segundos
        "CONN_MAX_AGE": 60,
    }
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------- Contraseñas
# Argon2 primero: es el que se usa al crear contraseñas nuevas.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ----------------------------------------------------------------------- Sesiones
SESSION_COOKIE_AGE = 30 * 60  # 30 min de inactividad
SESSION_SAVE_EVERY_REQUEST = True  # cada petición renueva el plazo
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = False  # el proxy ya fuerza HTTPS
    SECURE_HSTS_SECONDS = 31536000
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# ------------------------------------------------------------------------- Correo
# En desarrollo el correo se imprime en la consola de `app` (docker compose logs app).
# Para enviar correo real defina EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend y EMAIL_HOST*.
EMAIL_BACKEND = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=25)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Retiro Escolar Seguro <no-responder@retiro.local>")

# ------------------------------------------------------------------------- API
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "shared.api.standard_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Retiro Escolar Seguro API",
    "DESCRIPTION": "API REST del sistema Retiro Escolar Seguro.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

LOGIN_URL = "/autenticacion/ingresar/"

# ----------------------------------------------------------------- Tiempo real
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

# ------------------------------------------------------------------ Localización
LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Assets del panel disponibles también detrás de Daphne/Caddy, con DEBUG=False.
WHITENOISE_USE_FINDERS = True
STATIC_ROOT = BASE_DIR.parent / "staticfiles"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
