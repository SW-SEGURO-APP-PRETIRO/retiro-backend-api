"""Presentación exclusiva del Panel del Administrador del Sistema (ADMIN_SISTEMA).

Módulo independiente de `panel_escolar`, con sus propias plantillas, autenticación web y recursos estáticos.
"""
from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from shared.permissions import EsAdminSistema

SISTEMA_PAGES = [
    ("inicio", "Resumen de plataforma", "home", "Supervisión operativa global y estado de la plataforma."),
    ("instituciones", "Instituciones", "school", "Control de estados, registro y trazabilidad de colegios."),
    ("pendientes", "Solicitudes pendientes", "check", "Validación de RUC, correo y activación de instituciones."),
    ("administradores", "Administradores escolares", "shield", "Seguimiento de responsables por institución."),
    ("cuentas", "Cuentas globales", "people", "Supervisión transversal de usuarios por rol, institución y estado."),
    ("seguridad", "Seguridad y accesos", "lock", "Cuentas bloqueadas, intentos fallidos, claves temporales y anomalías."),
    ("bitacora", "Bitácora técnica", "history", "Eventos técnicos y de seguridad inmutables. Solo lectura."),
    ("integridad", "Integridad y auditoría", "key", "Verificación criptográfica de cadenas SHA-256 y estado de plataforma."),
    ("chat", "Chat de soporte", "chat", "Canales institucionales y comunicación directa con administradores escolares."),
    ("notificaciones", "Notificaciones del sistema", "bell", "Solicitudes de aprobación y alertas de seguridad en tiempo real."),
]

AUTH_TITLES = {
    "ingresar": "Inicia sesión en el sistema",
    "recuperar": "Recupera tu acceso administrativo",
    "restablecer": "Crea una nueva contraseña",
    "cambiar-contrasena": "Actualiza tu contraseña temporal",
}


@never_cache
@ensure_csrf_cookie
@require_GET
def panel_sistema(request, page="inicio"):
    if not request.user.is_authenticated:
        return redirect("/sistema/autenticacion/ingresar/")
    if not EsAdminSistema().has_permission(request, None):
        return render(request, "sistema/denegado.html", status=403)
    if request.user.contrasena_temporal:
        return redirect("/sistema/autenticacion/cambiar-contrasena/")
    item = next((p for p in SISTEMA_PAGES if p[0] == page), None)
    if item is None:
        return render(request, "sistema/denegado.html", status=404)
    return render(
        request,
        "sistema/panel.html",
        {
            "page": page,
            "title": item[1],
            "description": item[3],
            "navigation": SISTEMA_PAGES,
            "preview": getattr(settings, "ESCOLAR_PREVIEW", False),
        },
    )


@never_cache
@ensure_csrf_cookie
@require_GET
def auth_sistema_page(request, mode="ingresar"):
    if mode not in AUTH_TITLES:
        return render(request, "sistema/denegado.html", status=404)
    if mode == "cambiar-contrasena" and not request.user.is_authenticated:
        return redirect("/sistema/autenticacion/ingresar/")
    return render(
        request,
        "sistema/auth.html",
        {
            "mode": mode,
            "title": AUTH_TITLES[mode],
            "preview": getattr(settings, "ESCOLAR_PREVIEW", False),
        },
    )
