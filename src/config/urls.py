from django.db import connection
from django.http import JsonResponse
from django.urls import path


def salud(request):
    """Comprobación de vida para Docker/CI: responde 200 si la app llega a la base de datos."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")
    return JsonResponse({"estado": "ok"})


urlpatterns = [
    path("salud/", salud, name="salud"),
    # Las rutas de cada módulo se incluyen aquí cuando existan sus vistas
]