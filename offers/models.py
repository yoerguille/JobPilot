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
    INTERESTED = "interested", "Pendiente de aplicar"
    APPLIED = "applied", "Aplicada · Pendiente de respuesta"
    INTERVIEW = "interview", "Entrevista"
    TECHNICAL_INTERVIEW = "technical_interview", "Entrevista técnica"
    TECHNICAL_ASSESSMENT = "technical_assessment", "Prueba técnica"
    OFFER_RECEIVED = "offer_received", "Oferta recibida"
    REJECTED = "rejected", "Descartada"

    @classmethod
    def submitted_choices(cls):
        return [(value, label) for value, label in cls.choices if value != cls.INTERESTED]


class Application(models.Model):
    title = models.TextField()
    company = models.TextField()
    location = models.TextField(blank=True)
    original_links = models.JSONField()
    offer_snapshot = models.JSONField(default=dict, blank=True)
    applied_at = models.DateTimeField(default=timezone.now, null=True, blank=True)
    status = models.CharField(
        max_length=24, choices=ApplicationStatus.choices, default=ApplicationStatus.APPLIED,
    )
    sent_cv_version = models.ForeignKey("CVVersion", on_delete=models.PROTECT, null=True, blank=True)
    prepared_cv_version = models.ForeignKey(
        "CVVersion", on_delete=models.PROTECT, null=True, blank=True, related_name="+",
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


class CVProfile(models.Model):
    full_name = models.CharField(max_length=150)
    headline = models.CharField(max_length=150, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    location = models.CharField(max_length=150, blank=True)
    portfolio_url = models.URLField(blank=True)
    summary = models.TextField(blank=True)
    skills = models.TextField(blank=True)


class CVExperience(models.Model):
    profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name="experience")
    role = models.CharField(max_length=150)
    company = models.CharField(max_length=150)
    period = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)


class CVProject(models.Model):
    profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name="projects")
    name = models.CharField(max_length=150)
    url = models.URLField(blank=True)
    description = models.TextField(blank=True)


class CVEducation(models.Model):
    profile = models.ForeignKey(CVProfile, on_delete=models.CASCADE, related_name="education")
    qualification = models.CharField(max_length=150)
    institution = models.CharField(max_length=150)
    period = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)


class CVOfferDraft(models.Model):
    posting_key = models.CharField(max_length=64, primary_key=True)
    offer_title = models.TextField()
    company = models.TextField()
    content = models.JSONField()


class CVVersion(models.Model):
    posting_key = models.CharField(max_length=64)
    fingerprint = models.CharField(max_length=64)
    offer_title = models.TextField()
    company = models.TextField()
    content = models.JSONField()
    pdf = models.BinaryField(editable=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["posting_key", "fingerprint"], name="unique_cv_version_content"),
        ]
