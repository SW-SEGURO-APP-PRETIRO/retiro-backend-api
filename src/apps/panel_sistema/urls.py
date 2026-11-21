from django.urls import path
from .views import auth_sistema_page, panel_sistema

urlpatterns = [
    path("sistema/", panel_sistema, name="sistema-inicio"),
    path(
        "sistema/autenticacion/<slug:mode>/",
        auth_sistema_page,
        name="sistema-auth",
    ),
    path("sistema/<slug:page>/", panel_sistema, name="sistema-pagina"),
]
