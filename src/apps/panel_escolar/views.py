"""Solo presentación. Las operaciones de negocio siguen en la API existente."""
from django.conf import settings
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET
from apps.autenticacion.services import (
    CLAVE_SESION_RECUPERACION,
    obtener_hash_token_recuperacion,
)
from apps.cuentas.models import Rol
from shared.permissions import EsAdminEscolar

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

PAGES_BY_ROLE = {
    Rol.ADMIN_ESCOLAR: ADMIN_PAGES,
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
    if getattr(request.user, "rol", None) != Rol.ADMIN_ESCOLAR:
        return render(request, "escolar/denegado.html", status=403)
    return panel(request, page="inicio")


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
    nav = PAGES_BY_ROLE.get(request.user.rol, [])
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
    reset_token_valid = False
    if mode == "restablecer":
        token = request.GET.get("token")
        if token is not None:
            request.session.pop(CLAVE_SESION_RECUPERACION, None)
            token_hash = obtener_hash_token_recuperacion(token)
            if token_hash:
                request.session.cycle_key()
                request.session[CLAVE_SESION_RECUPERACION] = token_hash
                request.session.set_expiry(30 * 60)
                reset_token_valid = True
            response = redirect(request.path)
            response["Referrer-Policy"] = "no-referrer"
            return response
        reset_token_valid = bool(request.session.get(CLAVE_SESION_RECUPERACION))

    response = render(
        request,
        "escolar/auth.html",
        {
            "mode": mode,
            "title": titles[mode],
            "preview": getattr(settings, "ESCOLAR_PREVIEW", False),
            "reset_token_valid": reset_token_valid,
        },
    )
    if mode == "restablecer":
        response["Referrer-Policy"] = "no-referrer"
    return response


