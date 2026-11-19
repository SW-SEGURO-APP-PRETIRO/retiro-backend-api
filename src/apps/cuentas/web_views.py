from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.cuentas.models import Estudiante, Rol

from .forms import EstudianteForm
from .services import eliminar_estudiante, estudiantes_visibles, editar_estudiante, crear_estudiante, representantes_de


def _admin_escolar(user):
    return user.rol == Rol.ADMIN_ESCOLAR and user.institucion_id


@login_required
def estudiantes_lista(request):
    if not request.user.institucion_id:
        raise Http404
    queryset = estudiantes_visibles(request.user).order_by("apellidos", "nombres")
    termino = request.GET.get("q", "").strip()
    if termino:
        queryset = queryset.filter(
            nombres__icontains=termino
        ) | queryset.filter(apellidos__icontains=termino) | queryset.filter(cedula__icontains=termino)
    pagina = Paginator(queryset, 10).get_page(request.GET.get("page"))
    return render(request, "students/list.html", {"pagina": pagina, "termino": termino})


@login_required
def estudiante_detalle(request, pk):
    estudiante = get_object_or_404(estudiantes_visibles(request.user), pk=pk)
    return render(
        request,
        "students/detail.html",
        {"estudiante": estudiante, "representantes": representantes_de(estudiante)},
    )


@login_required
def estudiante_crear(request):
    if not _admin_escolar(request.user):
        raise PermissionDenied("Solo el administrador escolar puede crear estudiantes.")
    form = EstudianteForm(request.POST or None, institucion_id=request.user.institucion_id)
    if request.method == "POST" and form.is_valid():
        try:
            crear_estudiante(request.user, form.cleaned_data)
        except (IntegrityError, ValueError) as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Estudiante creado correctamente.")
            return redirect("web-estudiantes")
    return render(request, "students/form.html", {"form": form, "titulo": "Nuevo estudiante"})


@login_required
def estudiante_editar(request, pk):
    if not _admin_escolar(request.user):
        raise PermissionDenied("Solo el administrador escolar puede editar estudiantes.")
    estudiante = get_object_or_404(Estudiante._base_manager, pk=pk, institucion_id=request.user.institucion_id)
    form = EstudianteForm(
        request.POST or None,
        instance=estudiante,
        institucion_id=request.user.institucion_id,
    )
    if request.method == "POST" and form.is_valid():
        try:
            editar_estudiante(request.user, estudiante, form.cleaned_data)
        except (IntegrityError, ValueError) as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, "Estudiante actualizado correctamente.")
            return redirect("web-estudiante-detalle", pk=pk)
    return render(request, "students/form.html", {"form": form, "titulo": "Editar estudiante"})


@login_required
@require_POST
def estudiante_eliminar(request, pk):
    if not _admin_escolar(request.user):
        raise PermissionDenied("Solo el administrador escolar puede eliminar estudiantes.")
    estudiante = get_object_or_404(Estudiante._base_manager, pk=pk, institucion_id=request.user.institucion_id)
    try:
        eliminar_estudiante(request.user, estudiante)
    except (IntegrityError, PermissionError, ValueError) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Estudiante eliminado correctamente.")
    return redirect("web-estudiantes")