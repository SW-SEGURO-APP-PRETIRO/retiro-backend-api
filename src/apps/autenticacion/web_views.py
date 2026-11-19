from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from .forms import IngresoForm, NuevaContrasenaForm, RecuperarContrasenaForm, RegistroInstitucionForm
from .services import (
    autenticar,
    confirmar_recuperacion,
    registrar_institucion_con_contrasena,
    solicitar_recuperacion,
    token_recuperacion_valido,
)


def ingresar(request):
    if request.user.is_authenticated:
        return redirect("web-dashboard")
    form = IngresoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        request.data = form.cleaned_data
        usuario, mensaje = autenticar(request, form.cleaned_data["correo"], form.cleaned_data["contrasena"])
        if usuario:
            messages.success(request, "Bienvenido de nuevo.")
            return redirect("web-dashboard")
        form.add_error(None, mensaje)
    return render(request, "authentication/signin.html", {"form": form})


@require_http_methods(["GET", "POST"])
def registrar(request):
    if request.user.is_authenticated:
        return redirect("web-dashboard")
    form = RegistroInstitucionForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        try:
            registrar_institucion_con_contrasena(form.datos_servicio(), form.cleaned_data["contrasena"])
        except IntegrityError:
            form.add_error(None, "Ya existe una institución o cuenta con esos datos.")
        else:
            messages.success(request, "Registro recibido. La institución quedará pendiente de aprobación.")
            return redirect("web-login")
    return render(request, "authentication/signup.html", {"form": form})


def solicitar_recuperacion_web(request):
    form = RecuperarContrasenaForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        token = solicitar_recuperacion(form.cleaned_data["correo"])
        if token:
            enlace = request.build_absolute_uri(
                reverse("web-confirmar-recuperacion") + f"?token={token}"
            )
            send_mail(
                "Recuperación de contraseña",
                f"Use este enlace para cambiar su contraseña: {enlace}",
                None,
                [form.cleaned_data["correo"]],
            )
        messages.success(request, "Si el correo existe, recibirá instrucciones de recuperación.")
        return redirect("web-login")
    return render(request, "authentication/password_reset.html", {"form": form})


def confirmar_recuperacion_web(request):
    token = request.GET.get("token") or request.POST.get("token", "")
    form = NuevaContrasenaForm(request.POST or None)
    if not token or not token_recuperacion_valido(token):
        return render(request, "authentication/password_reset_confirm.html", {"form": form, "token_invalido": True})
    if request.method == "POST" and form.is_valid():
        try:
            confirmar_recuperacion(token, form.cleaned_data["contrasena"])
        except ValueError:
            return render(request, "authentication/password_reset_confirm.html", {"form": form, "token_invalido": True})
        messages.success(request, "Contraseña actualizada correctamente.")
        return redirect("web-login")
    return render(
        request,
        "authentication/password_reset_confirm.html",
        {"form": form, "token": token},
    )


@login_required
def cerrar_sesion_web(request):
    if request.method == "POST":
        logout(request)
        messages.success(request, "Sesión cerrada correctamente.")
        return redirect("web-login")
    return render(request, "authentication/logout.html")