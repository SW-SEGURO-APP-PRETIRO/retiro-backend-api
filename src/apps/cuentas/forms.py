from django import forms

from apps.instituciones.models import Curso

from .models import Estudiante


class EstudianteForm(forms.ModelForm):
    curso_id = forms.TypedChoiceField(label="Curso", coerce=int, empty_value=None)

    class Meta:
        model = Estudiante
        fields = ["cedula", "nombres", "apellidos", "fecha_nacimiento", "curso_id", "hora_salida_especial", "estado"]
        widgets = {
            "fecha_nacimiento": forms.DateInput(attrs={"type": "date"}),
            "hora_salida_especial": forms.TimeInput(attrs={"type": "time"}),
        }

    def __init__(self, *args, institucion_id=None, **kwargs):
        super().__init__(*args, **kwargs)
        cursos = Curso._base_manager.filter(
            institucion_id=institucion_id,
        ).filter(activo=True).order_by("nombre")
        self.fields["curso_id"].choices = [(curso.pk, curso.nombre) for curso in cursos]