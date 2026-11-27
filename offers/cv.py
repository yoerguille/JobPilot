import json
import re
from hashlib import sha256

from django import forms
from django.db import transaction
from django.forms import BaseInlineFormSet, inlineformset_factory
from django.forms.formsets import DELETION_FIELD_NAME
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods, require_POST, require_safe

from .cv_ai import text_sections
from .cv_pdf import PDF_STYLE_VERSION, render_cv_pdf
from .matching import normalize, posting_identity
from .models import CVEducation, CVExperience, CVOfferDraft, CVProfile, CVProject, CVVersion, SearchSnapshot


class CVProfileForm(forms.ModelForm):
    class Meta:
        model = CVProfile
        fields = [
            "full_name", "headline", "email", "phone", "location", "portfolio_url", "linkedin_url", "github_url",
            "summary", "skills", "languages", "additional_context",
        ]
        labels = {
            "full_name": "Nombre completo",
            "headline": "Título profesional",
            "email": "Correo electrónico",
            "phone": "Teléfono",
            "location": "Ubicación",
            "portfolio_url": "Enlace profesional",
            "linkedin_url": "Enlace a LinkedIn",
            "github_url": "Enlace a GitHub",
            "summary": "Resumen profesional",
            "skills": "Habilidades",
            "languages": "Idiomas y niveles",
            "additional_context": "Notas para adaptar el CV",
        }
        help_texts = {
            "skills": "Escribe una habilidad por línea.",
            "languages": "Escribe un idioma y su nivel por línea, por ejemplo, Inglés B2.",
            "additional_context": "Añade logros, contexto o preferencias que quieras que la IA tenga en cuenta al adaptar tu CV.",
        }
        widgets = {
            field: forms.Textarea(attrs={"rows": 3})
            for field in ("summary", "skills", "languages", "additional_context")
        }


class CVEntryFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.fields[DELETION_FIELD_NAME].label = "Eliminar esta entrada"


ExperienceFormSet = inlineformset_factory(
    CVProfile, CVExperience, fields=["role", "company", "period", "description"],
    formset=CVEntryFormSet,
    labels={"role": "Puesto", "company": "Empresa", "period": "Periodo", "description": "Descripción"},
    widgets={"description": forms.Textarea(attrs={"rows": 3})},
)
ProjectFormSet = inlineformset_factory(
    CVProfile, CVProject, fields=["name", "url", "description"],
    formset=CVEntryFormSet,
    labels={"name": "Nombre del proyecto", "url": "Enlace", "description": "Descripción"},
    widgets={"description": forms.Textarea(attrs={"rows": 3})},
)
EducationFormSet = inlineformset_factory(
    CVProfile, CVEducation, fields=["qualification", "institution", "period", "description"],
    formset=CVEntryFormSet,
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
    if data is None:
        for _, formset in sections:
            formset.extra = 0 if formset.initial_form_count() else 1
    if request.method == "POST":
        valid = [form.is_valid(), *(formset.is_valid() for _, formset in sections)]
        if all(valid):
            with transaction.atomic():
                profile.pk = 1
                form.save()
                for _, formset in sections:
                    formset.save()
            return redirect(reverse("cv_profile", query={"guardado": "1"}))

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
        "skills": profile_skills(profile),
    })


def profile_skills(profile):
    return list(dict.fromkeys(skill.strip() for skill in profile.skills.splitlines() if skill.strip()))


def draft_keywords(text):
    return {word for word in re.findall(r"\w+", normalize(text)) if len(word) >= 5 or word in {"api", "apis", "sql"}}


class CVOfferDraftForm(forms.Form):
    summary = forms.CharField(
        label="Resumen profesional", required=False, widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, data, profile, offer):
        super().__init__(data, initial={"summary": profile.summary})
        self.entries = {
            "experience": list(profile.experience.order_by("pk").values("id", "role", "company", "period", "description")),
            "projects": list(profile.projects.order_by("pk").values("id", "name", "url", "description")),
            "education": list(profile.education.order_by("pk").values(
                "id", "qualification", "institution", "period", "description",
            )),
            "skills": [{"id": skill, "name": skill} for skill in profile_skills(profile)],
        }
        labels = {
            "experience": ("Experiencia", ("role", "company")),
            "projects": ("Proyectos", ("name",)),
            "education": ("Formación", ("qualification", "institution")),
            "skills": ("Habilidades", ("name",)),
        }
        keywords = draft_keywords(f'{offer["title"]} {offer.get("description", "")}')
        for section, entries in self.entries.items():
            if not entries:
                continue
            label, title_fields = labels[section]
            scored = []
            for entry in entries:
                title = " · ".join(entry[field] for field in title_fields)
                score = len(keywords & draft_keywords(f'{title} {entry.get("description", "")}'))
                scored.append((score, str(entry["id"]), title))
            scored.sort(key=lambda item: -item[0])
            by_id = {str(entry["id"]): entry for entry in entries}
            self.entries[section] = [by_id[key] for _, key, _ in scored]
            self.fields[section] = forms.MultipleChoiceField(
                label=label, required=False, widget=forms.CheckboxSelectMultiple,
                choices=[(key, title) for _, key, title in scored],
                error_messages={"invalid_choice": "Selecciona una entrada válida del perfil."},
            )
            self.initial[section] = [key for score, key, _ in scored if score or not scored[0][0]]

    def content(self, profile, selection):
        contact_fields = (
            "full_name", "headline", "location", "email", "phone", "portfolio_url", "linkedin_url", "github_url",
        )
        content = {
            "profile": {field: getattr(profile, field) for field in contact_fields} | {"summary": selection["summary"]},
        }
        for section, entries in self.entries.items():
            selected = set(selection.get(section, []))
            content[section] = [entry for entry in entries if str(entry["id"]) in selected]
        content["skills"] = [entry["name"] for entry in content["skills"]]
        content["languages"] = [line.strip() for line in profile.languages.splitlines() if line.strip()]
        return content

    def load_selection(self, content):
        self.initial["summary"] = content["profile"]["summary"]
        for section in ("experience", "projects", "education"):
            self.initial[section] = [str(entry["id"]) for entry in content[section]]
        self.initial["skills"] = content["skills"]


@require_http_methods(["GET", "POST"])
def cv_offer_draft(request, posting):
    approved = CVOfferDraft.objects.filter(pk=posting).first()
    snapshot = SearchSnapshot.objects.filter(pk=1).first()
    offer = next((
        match["offer"] for match in snapshot.data["matches"]
        if posting_identity(match["offer"]["url"]) == posting
    ), None) if snapshot else None
    if request.method == "GET" and approved and (request.GET.get("editar") != "1" or offer is None):
        return render(request, "offers/cv_preview.html", {
            **approved.content, "target": {"title": approved.offer_title, "company": approved.company},
            "approved": True, "can_edit": offer is not None, "draft_fingerprint": draft_fingerprint(approved),
            "posting": posting,
        })
    if offer is None:
        raise Http404("La oferta ya no está en los resultados de la última búsqueda.")
    profile = CVProfile.objects.filter(pk=1).first()
    if profile is None:
        return render(request, "offers/cv_preview.html", {"target": offer})

    data = request.POST if request.method == "POST" else None
    form = CVOfferDraftForm(data, profile, offer)
    if approved:
        form.load_selection(approved.content)
    selection = form.initial
    if form.is_valid():
        selection = form.cleaned_data
        if request.POST.get("action") == "approve":
            CVOfferDraft.objects.update_or_create(pk=posting, defaults={
                "offer_title": offer["title"], "company": offer["company"], "content": form.content(profile, selection),
            })
            return redirect("cv_offer_draft", posting=posting)
    return render(request, "offers/cv_preview.html", {
        **form.content(profile, selection), "target": offer, "draft_form": form,
    })


def cv_fingerprint(title, company, content):
    payload = json.dumps([title, company, content], sort_keys=True)
    return sha256(payload.encode()).hexdigest()


def draft_fingerprint(draft):
    return cv_fingerprint(draft.offer_title, draft.company, draft.content)


def get_or_create_cv_version(posting, title, company, content):
    version, _ = CVVersion.objects.get_or_create(
        posting_key=posting, fingerprint=cv_fingerprint(title, company, content | {"pdf_style": PDF_STYLE_VERSION}),
        defaults={
            "offer_title": title, "company": company, "content": content,
            "pdf": lambda: render_cv_pdf(content),
        },
    )
    return version


@require_POST
def save_cv_version(request, posting):
    draft = get_object_or_404(CVOfferDraft, pk=posting)
    fingerprint = draft_fingerprint(draft)
    if request.POST.get("fingerprint") != fingerprint:
        return HttpResponse("El borrador ha cambiado. Vuelve a abrirlo antes de guardar la versión.", status=409)
    version = get_or_create_cv_version(posting, draft.offer_title, draft.company, draft.content)
    return redirect("cv_version", pk=version.pk)


@require_safe
def cv_versions(request):
    versions = CVVersion.objects.defer("content", "pdf").order_by("-created_at", "-pk")
    return render(request, "offers/cv_versions.html", {"versions": versions})


@require_safe
def cv_version(request, pk):
    version = get_object_or_404(CVVersion.objects.defer("pdf"), pk=pk)
    sections = text_sections(version.content) if "text_sections" in version.content else None
    return render(request, "offers/cv_preview.html", {
        **version.content, "target": {"title": version.offer_title, "company": version.company},
        "version": version, "cv_sections": sections,
    })


@require_safe
def download_cv_version(request, pk):
    version = get_object_or_404(CVVersion.objects.only("pdf"), pk=pk)
    response = HttpResponse(version.pdf, content_type="application/pdf")
    response.headers["Content-Disposition"] = f'attachment; filename="CV-{version.pk}.pdf"'
    return response
