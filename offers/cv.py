from django import forms
from django.db import transaction
from django.forms import inlineformset_factory
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_safe

from .models import CVEducation, CVExperience, CVProfile, CVProject


class CVProfileForm(forms.ModelForm):
    class Meta:
        model = CVProfile
        fields = ["full_name", "headline", "email", "phone", "location", "portfolio_url", "summary", "skills"]
        labels = {
            "full_name": "Nombre completo",
            "headline": "Título profesional",
            "email": "Correo electrónico",
            "phone": "Teléfono",
            "location": "Ubicación",
            "portfolio_url": "Enlace profesional",
            "summary": "Resumen profesional",
            "skills": "Habilidades",
        }
        help_texts = {"skills": "Escribe una habilidad por línea."}
        widgets = {"summary": forms.Textarea(attrs={"rows": 3}), "skills": forms.Textarea(attrs={"rows": 3})}


ExperienceFormSet = inlineformset_factory(
    CVProfile, CVExperience, fields=["role", "company", "period", "description"],
    labels={"role": "Puesto", "company": "Empresa", "period": "Periodo", "description": "Descripción"},
    widgets={"description": forms.Textarea(attrs={"rows": 3})},
)
ProjectFormSet = inlineformset_factory(
    CVProfile, CVProject, fields=["name", "url", "description"],
    labels={"name": "Nombre del proyecto", "url": "Enlace", "description": "Descripción"},
    widgets={"description": forms.Textarea(attrs={"rows": 3})},
)
EducationFormSet = inlineformset_factory(
    CVProfile, CVEducation, fields=["qualification", "institution", "period", "description"],
    labels={"qualification": "Título o curso", "institution": "Centro", "period": "Periodo",
            "description": "Descripción"},
    widgets={"description": forms.Textarea(attrs={"rows": 3})},
)


@require_http_methods(["GET", "POST"])
def cv_profile(request):
    saved_profile = CVProfile.objects.filter(pk=1).first()
    profile = saved_profile or CVProfile()
    data = request.POST if request.method == "POST" else None
    form = CVProfileForm(data, instance=profile)
    sections = [
        ("Experiencia", ExperienceFormSet(data, instance=profile, prefix="experience")),
        ("Proyectos", ProjectFormSet(data, instance=profile, prefix="projects")),
        ("Formación", EducationFormSet(data, instance=profile, prefix="education")),
    ]
    if request.method == "POST":
        valid = [form.is_valid(), *(formset.is_valid() for _, formset in sections)]
        if all(valid):
            with transaction.atomic():
                profile.pk = 1
                form.save()
                for _, formset in sections:
                    formset.save()
            return redirect(reverse("cv_profile", query={"guardado": "1"}))

    for _, formset in sections:
        for item in formset.forms:
            item.fields["DELETE"].label = "Eliminar esta entrada"
    return render(request, "offers/cv_profile.html", {
        "form": form, "sections": sections, "saved": request.GET.get("guardado") == "1" and data is None,
        "has_profile": saved_profile is not None,
    })


@require_safe
def cv_preview(request):
    profile = CVProfile.objects.filter(pk=1).first()
    if profile is None:
        return render(request, "offers/cv_preview.html")

    return render(request, "offers/cv_preview.html", {
        "profile": profile,
        "experience": profile.experience.order_by("pk"),
        "projects": profile.projects.order_by("pk"),
        "education": profile.education.order_by("pk"),
        "skills": [skill.strip() for skill in profile.skills.splitlines() if skill.strip()],
    })
