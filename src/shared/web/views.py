from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.cuentas.models import Rol
from apps.cuentas.services import resumen_global, resumen_institucion
from apps.instituciones.services import nombre_institucion, resumen_instituciones


@login_required
def dashboard(request):
    contexto = {"rol": request.user.rol, "institucion_nombre": ""}
    if request.user.institucion_id:
        contexto["institucion_nombre"] = nombre_institucion(request.user.institucion_id)
        contexto["resumen"] = resumen_institucion(request.user.institucion_id)
    elif request.user.rol == Rol.ADMIN_SISTEMA:
        contexto["resumen"] = resumen_global()
        contexto["instituciones"] = resumen_instituciones()
    return render(request, "dashboard/index.html", contexto)