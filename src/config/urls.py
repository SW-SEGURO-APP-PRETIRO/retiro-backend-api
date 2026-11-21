from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView


def salud(request):
    """Comprobación de vida para Docker/CI: responde 200 si la app llega a la base de datos."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"estado": "ok"})


urlpatterns = [
    path("", include("apps.panel_escolar.urls")),
    path("", include("apps.panel_sistema.urls")),
    path("salud/", salud, name="salud"),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/v1/autenticacion/", include("apps.autenticacion.urls")),
    path("api/v1/instituciones/", include("apps.instituciones.urls")),
    path("api/v1/cuentas/", include("apps.cuentas.urls")),
    path("api/v1/cuidadores/", include("apps.cuidadores.urls")),
    path("api/v1/auditoria/", include("apps.auditoria.urls")),
    path("api/v1/notificaciones/", include("apps.chat.urls")),
    path("api/v1/chat/", include("apps.chat.urls")),
    # Las rutas de cada módulo se incluyen aquí cuando existan sus vistas
]
