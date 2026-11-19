from django import forms
from django.contrib.auth.password_validation import validate_password


class IngresoForm(forms.Form):
    correo = forms.EmailField(label="Correo electrónico")
    contrasena = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    codigo_totp = forms.CharField(label="Código TOTP", required=False, max_length=8)


class RegistroInstitucionForm(forms.Form):
    nombre = forms.CharField(label="Nombre de la institución", max_length=200)
    ruc = forms.CharField(label="RUC", max_length=13)
    direccion = forms.CharField(label="Dirección", max_length=255)
    telefono = forms.CharField(label="Teléfono", max_length=20)
    correo = forms.EmailField(label="Correo institucional")
    responsable = forms.CharField(label="Responsable", max_length=150)
    admin_correo = forms.EmailField(label="Correo del administrador")
    admin_cedula = forms.CharField(label="Cédula del administrador", max_length=10)
    admin_nombres = forms.CharField(label="Nombres del administrador", max_length=100)
    admin_apellidos = forms.CharField(label="Apellidos del administrador", max_length=100)
    admin_telefono = forms.CharField(label="Teléfono del administrador", max_length=20, required=False)
    contrasena = forms.CharField(label="Contraseña", widget=forms.PasswordInput)
    confirmar_contrasena = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("contrasena") != cleaned.get("confirmar_contrasena"):
            self.add_error("confirmar_contrasena", "Las contraseñas no coinciden.")
        if cleaned.get("contrasena"):
            try:
                validate_password(cleaned["contrasena"])
            except forms.ValidationError as exc:
                self.add_error("contrasena", exc)
        return cleaned

    def datos_servicio(self):
        return {
            "nombre": self.cleaned_data["nombre"],
            "ruc": self.cleaned_data["ruc"],
            "direccion": self.cleaned_data["direccion"],
            "telefono": self.cleaned_data["telefono"],
            "correo": self.cleaned_data["correo"],
            "responsable": self.cleaned_data["responsable"],
            "admin_escolar": {
                "correo": self.cleaned_data["admin_correo"],
                "cedula": self.cleaned_data["admin_cedula"],
                "nombres": self.cleaned_data["admin_nombres"],
                "apellidos": self.cleaned_data["admin_apellidos"],
                "telefono": self.cleaned_data["admin_telefono"],
            },
        }


class RecuperarContrasenaForm(forms.Form):
    correo = forms.EmailField(label="Correo electrónico")


class NuevaContrasenaForm(forms.Form):
    contrasena = forms.CharField(label="Nueva contraseña", widget=forms.PasswordInput)
    confirmar_contrasena = forms.CharField(label="Confirmar contraseña", widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("contrasena") != cleaned.get("confirmar_contrasena"):
            self.add_error("confirmar_contrasena", "Las contraseñas no coinciden.")
        if cleaned.get("contrasena"):
            try:
                validate_password(cleaned["contrasena"])
            except forms.ValidationError as exc:
                self.add_error("contrasena", exc)
        return cleaned