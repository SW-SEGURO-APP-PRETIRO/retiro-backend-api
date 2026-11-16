from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("instituciones", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="institucion",
            name="creada_por_id",
            field=models.PositiveBigIntegerField(
                blank=True,
                null=True,
            ),
        ),
    ]
