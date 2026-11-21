"""Solo presentación. Las operaciones de negocio siguen en la API existente."""
from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from apps.cuentas.models import Rol
from shared.permissions import EsPadreOAdminEscolar

ADMIN_PAGES = [
    ("inicio", "Resumen", "home", "Tu institución, al día."),
    ("estudiantes", "Estudiantes", "students", "Matrícula, cursos y horarios de salida."),
    ("padres", "Padres y representantes", "people", "Cuentas de las familias de tu institución."),
    ("guardias", "Guardias", "shield", "Personal responsable del control en las puertas."),
    ("asignaciones", "Asignaciones", "link", "Vínculos oficiales entre estudiantes y representantes."),
    ("cuidadores", "Cuidadores", "check", "Revisa las solicitudes y emite el acceso de los cuidadores."),
    ("cursos", "Cursos y horarios", "calendar", "Organiza los cursos y su hora de salida."),
    ("puertas", "Puertas", "door", "Puntos de salida de tu institución."),
    ("chat", "Chat institucional", "chat", "Sala general y mensajería directa con tu comunidad escolar."),
    ("bitacora", "Bitácora operativa", "history", "Registro de eventos de tu institución. Solo lectura."),
    ("notificaciones", "Notificaciones", "bell", "Novedades y solicitudes que requieren tu atención."),
    ("institucion", "Mi institución", "school", "Información de contacto del colegio."),
]

PADRE_PAGES = [
    ("inicio", "Resumen familiar", "home", "Tus hijos, cuidadores y avisos del colegio."),
    ("estudiantes", "Mis hijos", "students", "Estudiantes vinculados oficialmente a tu cuenta."),
    ("cuidadores", "Mis cuidadores", "check", "Registra cuidadores y solicita autorización de retiro para tus hijos."),
    ("chat", "Chat con el colegio", "chat", "Sala general de la institución y comunicación directa con administración."),
    ("notificaciones", "Notificaciones", "bell", "Avisos de aprobaciones, rechazos y novedades de retiro."),
    ("institucion", "Mi institución", "school", "Información de contacto del colegio de tus hijos."),
]

PAGES = ADMIN_PAGES


@never_cache
@ensure_csrf_cookie
@require_GET
def panel(request, page="inicio"):
    if not request.user.is_authenticated:
        return redirect("/autenticacion/ingresar/")
    if not EsPadreOAdminEscolar().has_permission(request, None):
        return render(request, "escolar/denegado.html", status=403)
    if request.user.contrasena_temporal:
        return redirect("/autenticacion/cambiar-contrasena/")
    nav = PADRE_PAGES if request.user.rol == Rol.PADRE else ADMIN_PAGES
    item = next((p for p in nav if p[0] == page), None)
    if item is None:
        # Si un PADRE intenta entrar a una página exclusiva de ADMIN_ESCOLAR (ej. /escolar/padres/), responde 403
        if any(p[0] == page for p in ADMIN_PAGES):
            return render(request, "escolar/denegado.html", status=403)
        return render(request, "escolar/denegado.html", status=404)
    return render(request, "escolar/panel.html", {
        "page": page, "title": item[1], "description": item[3],
        "navigation": nav, "preview": getattr(settings, "ESCOLAR_PREVIEW", False),
    })

@never_cache
@ensure_csrf_cookie
@require_GET
def auth_page(request, mode="ingresar"):
    if mode == "cambiar-contrasena" and not request.user.is_authenticated:
        return redirect("/autenticacion/ingresar/")
    titles = {"ingresar": "Inicia sesión", "recuperar": "Recupera tu acceso", "restablecer": "Crea una nueva contraseña", "cambiar-contrasena": "Actualiza tu contraseña"}
    return render(request, "escolar/auth.html", {"mode": mode, "title": titles[mode], "preview": getattr(settings, "ESCOLAR_PREVIEW", False)})


