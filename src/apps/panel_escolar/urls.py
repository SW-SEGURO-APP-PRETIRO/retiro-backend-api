from django.urls import path
from .views import auth_page, panel

urlpatterns = [path("", panel), path("escolar/", panel, name="escolar-inicio")]
urlpatterns += [path("escolar/<slug:page>/", panel, name="escolar-pagina")]
urlpatterns += [path(f"autenticacion/{mode}/", auth_page, {"mode": mode}, name=f"web-{mode}") for mode in ("ingresar", "recuperar", "restablecer", "cambiar-contrasena")]
