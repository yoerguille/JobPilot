from django.db import models


class Criteria(models.Model):
    keywords = models.CharField(max_length=250, default="backend, junior, Python, API, integraciones")
    location = models.CharField(max_length=100, default="España")
    modality = models.CharField(max_length=12, default="all", choices=[
        ("all", "Todas"),
        ("remote", "Remota"),
        ("hybrid", "Híbrida"),
        ("onsite", "Presencial"),
    ])
