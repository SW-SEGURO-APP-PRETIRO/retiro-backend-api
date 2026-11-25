"""Formulario de registro (SignUp) renderizado en el servidor.

La validación ocurre dos veces: en el navegador (atributos HTML5: required, pattern, minlength, maxlength)
y aquí en el servidor, que es la que decide. Nunca se confía solo en la pantalla.
"""
from django import forms
from django.contrib.auth.password_validation import validate_password

from apps.cuentas.services import correo_en_uso
from apps.instituciones.services import correo_institucion_en_uso, ruc_en_uso
from shared.utils.validadores import validar_cedula_ec, validar_ruc_ec

TELEFONO_PATTERN = "[0-9]{7,10}"
TELEFONO_AYUDA = "Solo números, de 7 a 10 dígitos."


def _texto(label, max_length, *, required=True, **attrs):
    return forms.CharField(
        label=label,
        max_length=max_length,
        required=required,
        widget=forms.TextInput(attrs=attrs),
    )


def _correo(label, **attrs):
    return forms.EmailField(label=label, max_length=254, widget=forms.EmailInput(attrs=attrs))


class RegistroInstitucionForm(forms.Form):
    """Una persona del colegio se registra como Administrador Escolar junto con su institución.

    Ambos quedan pendientes hasta que el Administrador del Sistema aprueba la solicitud.
    """

    # --- Paso 1: datos de la persona (será el Administrador Escolar)
    admin_nombres = _texto("Nombres", 100, autocomplete="given-name", placeholder="María José")
    admin_apellidos = _texto("Apellidos", 100, autocomplete="family-name", placeholder="Cárdenas Ortiz")
    admin_cedula = _texto(
        "Cédula", 10,
        pattern="[0-9]{10}", minlength="10", inputmode="numeric", placeholder="10 dígitos",
        title="La cédula tiene exactamente 10 dígitos.",
    )
    admin_telefono = _texto(
        "Teléfono celular", 10, required=False,
        pattern=TELEFONO_PATTERN, inputmode="numeric", autocomplete="tel", placeholder="0991234567",
        title=TELEFONO_AYUDA,
    )
    admin_correo = _correo("Correo personal", autocomplete="username", placeholder="tu.nombre@correo.com")

    # --- Paso 2: datos de la institución
    nombre = _texto("Nombre de la institución", 200, autocomplete="organization", placeholder="Unidad Educativa …")
    ruc = _texto(
        "RUC", 13,
        # Misma regla que el servidor: provincia (01-24 o 30) + tercer dígito (0-6 o 9) + 10 dígitos
        pattern="(0[1-9]|1[0-9]|2[0-4]|30)[0-69][0-9]{10}", minlength="13", inputmode="numeric",
        placeholder="Ej.: 1791234567001",
        title="El RUC tiene 13 dígitos, empieza con el código de provincia (01-24 o 30) y termina en 001.",
    )
    responsable = _texto("Representante legal", 150, placeholder="Nombre del rector o rectora")
    telefono = _texto(
        "Teléfono de la institución", 10,
        pattern=TELEFONO_PATTERN, inputmode="numeric", placeholder="022345678", title=TELEFONO_AYUDA,
    )
    correo = _correo("Correo institucional", placeholder="secretaria@colegio.edu.ec")
    direccion = _texto("Dirección", 255, autocomplete="street-address", placeholder="Av. Principal y calle secundaria")

    # --- Paso 3: acceso
    contrasena = forms.CharField(
        label="Contraseña", min_length=10, max_length=128, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "minlength": "10"}),
        help_text="Mínimo 10 caracteres. Evita contraseñas comunes o solo numéricas.",
    )
    confirmar_contrasena = forms.CharField(
        label="Confirma la contraseña", max_length=128, strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "minlength": "10"}),
    )

    PERSONA = ("admin_nombres", "admin_apellidos", "admin_cedula", "admin_telefono", "admin_correo")
    INSTITUCION = ("nombre", "ruc", "responsable", "telefono", "correo", "direccion")
    ACCESO = ("contrasena", "confirmar_contrasena")
    ANCHO_COMPLETO = {"admin_correo", "nombre", "direccion"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nombre, field in self.fields.items():
            # Mismos mensajes que muestra el navegador (registro.js), para que la experiencia sea coherente
            field.error_messages["required"] = f"{field.label} es obligatorio."
            if isinstance(field, forms.EmailField):
                field.error_messages["invalid"] = "Escribe un correo válido, por ejemplo nombre@dominio.com."
            if field.required:
                field.widget.attrs["required"] = True
            field.widget.attrs.setdefault("maxlength", field.max_length)
            field.ancho_completo = nombre in self.ANCHO_COMPLETO

    def secciones(self):
        """[(número, título, descripción, campos)] para pintar el formulario por pasos."""
        return [
            ("1", "Tus datos", "Serás el Administrador Escolar de tu institución.",
             [self[n] for n in self.PERSONA]),
            ("2", "Tu institución", "Datos oficiales del colegio que administrarás.",
             [self[n] for n in self.INSTITUCION]),
            ("3", "Tu acceso", "Usarás tu correo personal y esta contraseña para iniciar sesión.",
             [self[n] for n in self.ACCESO]),
        ]

    # ------------------------------------------------------------------ validaciones de servidor
    def clean_admin_cedula(self):
        cedula = self.cleaned_data["admin_cedula"].strip()
        validar_cedula_ec(cedula)
        return cedula

    def clean_admin_correo(self):
        correo = self.cleaned_data["admin_correo"].strip().lower()
        if correo_en_uso(correo):
            raise forms.ValidationError("Ya existe una cuenta con este correo.")
        return correo

    def clean_ruc(self):
        ruc = self.cleaned_data["ruc"].strip()
        validar_ruc_ec(ruc)
        if ruc_en_uso(ruc):
            raise forms.ValidationError("Ya existe una institución registrada con este RUC.")
        return ruc

    def clean_correo(self):
        correo = self.cleaned_data["correo"].strip().lower()
        if correo_institucion_en_uso(correo):
            raise forms.ValidationError("Ya existe una institución registrada con este correo.")
        return correo

    @staticmethod
    def _telefono(valor):
        valor = (valor or "").strip()
        if valor and not (valor.isdigit() and 7 <= len(valor) <= 10):
            raise forms.ValidationError(TELEFONO_AYUDA)
        return valor

    def clean_admin_telefono(self):
        return self._telefono(self.cleaned_data.get("admin_telefono"))

    def clean_telefono(self):
        return self._telefono(self.cleaned_data.get("telefono"))

    def clean(self):
        cleaned = super().clean()
        contrasena = cleaned.get("contrasena")
        if contrasena and contrasena != cleaned.get("confirmar_contrasena"):
            self.add_error("confirmar_contrasena", "Las contraseñas no coinciden.")
        if contrasena and not self.has_error("contrasena"):
            try:
                validate_password(contrasena)
            except forms.ValidationError as exc:
                self.add_error("contrasena", exc)
        if cleaned.get("correo") and cleaned.get("correo") == cleaned.get("admin_correo"):
            self.add_error("admin_correo", "Usa tu correo personal, distinto al correo institucional.")
        return cleaned

    def datos_servicio(self):
        d = self.cleaned_data
        return {
            "nombre": d["nombre"].strip(),
            "ruc": d["ruc"],
            "direccion": d["direccion"].strip(),
            "telefono": d["telefono"],
            "correo": d["correo"],
            "responsable": d["responsable"].strip(),
            "admin_escolar": {
                "correo": d["admin_correo"],
                "cedula": d["admin_cedula"],
                "nombres": d["admin_nombres"].strip(),
                "apellidos": d["admin_apellidos"].strip(),
                "telefono": d.get("admin_telefono", ""),
            },
        }
