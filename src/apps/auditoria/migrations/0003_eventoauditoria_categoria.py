from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("auditoria", "0002_bitacora_inmutable"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventoauditoria",
            name="categoria",
            field=models.CharField(
                choices=[("TECNICA", "Técnica"), ("OPERATIVA", "Operativa")],
                default="OPERATIVA",
                max_length=9,
            ),
        ),
    ]
