from django.db import models
from django.utils import timezone


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


class ApplicationStatus(models.TextChoices):
    APPLIED = "applied", "Aplicada"
    INTERVIEW = "interview", "Entrevista"
    TECHNICAL_INTERVIEW = "technical_interview", "Entrevista técnica"
    TECHNICAL_ASSESSMENT = "technical_assessment", "Prueba técnica"
    OFFER_RECEIVED = "offer_received", "Oferta recibida"
    REJECTED = "rejected", "Descartada"


class Application(models.Model):
    title = models.TextField()
    company = models.TextField()
    location = models.TextField(blank=True)
    original_links = models.JSONField()
    applied_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(
        max_length=24, choices=ApplicationStatus.choices, default=ApplicationStatus.APPLIED,
    )


class ApplicationPosting(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="posting_keys")


class ApplicationStatusEvent(models.Model):
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name="status_history")
    status = models.CharField(max_length=24, choices=ApplicationStatus.choices)
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["occurred_at", "pk"]
