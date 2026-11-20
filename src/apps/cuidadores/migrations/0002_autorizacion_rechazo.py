from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cuidadores", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="autorizacioncuidador",
            name="rechazada_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="autorizacioncuidador",
            name="rechazada_por_id",
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="autorizacioncuidador",
            name="motivo_rechazo",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name="autorizacioncuidador",
            name="estado",
            field=models.CharField(
                choices=[
                    ("SOLICITADO", "Solicitado por el padre"),
                    ("ACCESO_EMITIDO", "Acceso emitido por el Admin Escolar"),
                    ("ACTIVO", "Activo (primer ingreso hecho)"),
                    ("EXPIRADO", "Expirado"),
                    ("REVOCADO", "Revocado"),
                    ("RECHAZADO", "Rechazado por el administrador escolar"),
                ],
                default="SOLICITADO",
                max_length=15,
            ),
        ),
    ]
