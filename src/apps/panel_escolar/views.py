"""Solo presentación. Las operaciones de negocio siguen en la API existente."""
from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from shared.permissions import EsAdminEscolar

PAGES = [
    ("inicio", "Resumen", "home", "Tu institución, al día."),
    ("estudiantes", "Estudiantes", "students", "Matrícula, cursos y horarios de salida."),
    ("padres", "Padres y representantes", "people", "Cuentas de las familias de tu institución."),
    ("guardias", "Guardias", "shield", "Personal responsable del control en las puertas."),
    ("asignaciones", "Asignaciones", "link", "Vínculos oficiales entre estudiantes y representantes."),
    ("cuidadores", "Cuidadores", "check", "Revisa las solicitudes y emite el acceso de los cuidadores."),
    ("cursos", "Cursos y horarios", "calendar", "Organiza los cursos y su hora de salida."),
    ("puertas", "Puertas", "door", "Puntos de salida de tu institución."),
    ("bitacora", "Bitácora operativa", "history", "Registro de eventos de tu institución. Solo lectura."),
    ("notificaciones", "Notificaciones", "bell", "Novedades y solicitudes que requieren tu atención."),
    ("institucion", "Mi institución", "school", "Información de contacto del colegio."),
]

@never_cache
@ensure_csrf_cookie
@require_GET
def panel(request, page="inicio"):
    if not request.user.is_authenticated:
        return redirect("/autenticacion/ingresar/")
    if not EsAdminEscolar().has_permission(request, None):
        return render(request, "escolar/denegado.html", status=403)
    if request.user.contrasena_temporal:
        return redirect("/autenticacion/cambiar-contrasena/")
    item = next((p for p in PAGES if p[0] == page), None)
    if item is None:
        return render(request, "escolar/denegado.html", status=404)
    return render(request, "escolar/panel.html", {
        "page": page, "title": item[1], "description": item[3],
        "navigation": PAGES, "preview": getattr(settings, "ESCOLAR_PREVIEW", False),
    })

@never_cache
@ensure_csrf_cookie
@require_GET
def auth_page(request, mode="ingresar"):
    if mode == "cambiar-contrasena" and not request.user.is_authenticated:
        return redirect("/autenticacion/ingresar/")
    titles = {"ingresar": "Inicia sesión", "recuperar": "Recupera tu acceso", "restablecer": "Crea una nueva contraseña", "cambiar-contrasena": "Actualiza tu contraseña"}
    return render(request, "escolar/auth.html", {"mode": mode, "title": titles[mode], "preview": getattr(settings, "ESCOLAR_PREVIEW", False)})
