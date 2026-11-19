from django.urls import path

from .web_views import (
    cerrar_sesion_web,
    confirmar_recuperacion_web,
    ingresar,
    registrar,
    solicitar_recuperacion_web,
)

urlpatterns = [
    path("ingresar/", ingresar, name="web-login"),
    path("registrar/", registrar, name="web-signup"),
    path("recuperar/", solicitar_recuperacion_web, name="web-solicitar-recuperacion"),
    path("recuperar/confirmar/", confirmar_recuperacion_web, name="web-confirmar-recuperacion"),
    path("salir/", cerrar_sesion_web, name="web-logout"),
]