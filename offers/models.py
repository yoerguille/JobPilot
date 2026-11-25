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


class SeenPosting(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    first_seen_at = models.DateTimeField()
    first_search = models.UUIDField()


class SearchSnapshot(models.Model):
    data = models.JSONField()
