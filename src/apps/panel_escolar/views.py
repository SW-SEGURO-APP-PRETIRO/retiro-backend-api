"""Solo presentación. Las operaciones de negocio siguen en la API existente."""
from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from apps.cuentas.models import Rol
from shared.permissions import EsMiembroInstitucion

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
    ("chat", "Chat con el colegio", "chat", "Sala general de la institución."),
    ("notificaciones", "Notificaciones", "bell", "Avisos de aprobaciones, rechazos y novedades de retiro."),
    ("institucion", "Mi institución", "school", "Información de contacto del colegio de tus hijos."),
]

GUARDIA_PAGES = [
    ("inicio", "Control de puerta", "home", "Supervisión de salidas, puertas y cuidadores autorizados."),
    ("estudiantes", "Estudiantes", "students", "Consulta de matrícula, cursos y horarios de salida."),
    ("cuidadores", "Cuidadores autorizados", "check", "Verifica las personas autorizadas para retirar estudiantes."),
    ("cursos", "Cursos y horarios", "calendar", "Horarios oficiales de salida por curso."),
    ("puertas", "Puertas", "door", "Puntos de salida habilitados en la institución."),
    ("chat", "Chat institucional", "chat", "Sala general de coordinación con la institución."),
    ("notificaciones", "Notificaciones", "bell", "Avisos operativos en tiempo real."),
    ("institucion", "Mi institución", "school", "Información del colegio."),
]

CUIDADOR_PAGES = [
    ("inicio", "Resumen de retiro", "home", "Estudiantes autorizados a tu cargo y horarios de salida."),
    ("estudiantes", "Estudiantes asignados", "students", "Estudiantes que estás autorizado a retirar."),
    ("cuidadores", "Mis autorizaciones", "check", "Estado de tus autorizaciones de retiro."),
    ("chat", "Chat institucional", "chat", "Sala general de la institución."),
    ("notificaciones", "Notificaciones", "bell", "Avisos sobre tus autorizaciones y retiros."),
    ("institucion", "Mi institución", "school", "Información de contacto del colegio."),
]

PAGES_BY_ROLE = {
    Rol.ADMIN_ESCOLAR: ADMIN_PAGES,
    Rol.PADRE: PADRE_PAGES,
    Rol.GUARDIA: GUARDIA_PAGES,
    Rol.CUIDADOR_FIJO: CUIDADOR_PAGES,
}

PAGES = ADMIN_PAGES


@never_cache
@ensure_csrf_cookie
@require_GET
def root_panel(request):
    if not request.user.is_authenticated:
        return redirect("/autenticacion/ingresar/")
    if getattr(request.user, "rol", None) == Rol.ADMIN_SISTEMA:
        return redirect("/sistema/")
    return panel(request, page="inicio")


@never_cache
@ensure_csrf_cookie
@require_GET
def panel(request, page="inicio"):
    if not request.user.is_authenticated:
        return redirect("/autenticacion/ingresar/")
    if not EsMiembroInstitucion().has_permission(request, None):
        return render(request, "escolar/denegado.html", status=403)
    if request.user.contrasena_temporal:
        return redirect("/autenticacion/cambiar-contrasena/")
    nav = PAGES_BY_ROLE.get(request.user.rol, PADRE_PAGES)
    item = next((p for p in nav if p[0] == page), None)
    if item is None:
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


