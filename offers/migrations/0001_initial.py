from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="Criteria",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("keywords", models.CharField(default="backend, junior, Python, API, integraciones", max_length=250)),
                ("location", models.CharField(default="España", max_length=100)),
                ("modality", models.CharField(choices=[("all", "Todas"), ("remote", "Remota"), ("hybrid", "Híbrida"), ("onsite", "Presencial")], default="all", max_length=12)),
            ],
        ),
    ]
