from django import forms
from django.utils.formats import date_format
from django.utils.timezone import localtime

from .models import ApplicationStatus, Criteria, CVVersion


class SentCVVersionChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, version):
        saved_at = date_format(localtime(version.created_at), "SHORT_DATETIME_FORMAT")
        return f"CV-{version.pk} · {saved_at}"


class SentCVVersionForm(forms.Form):
    sent_cv_version = SentCVVersionChoiceField(
        queryset=CVVersion.objects.none(),
        label="Versión enviada",
        required=False,
        empty_label="Sin versión vinculada",
        error_messages={"invalid_choice": "Selecciona una versión guardada para esta oferta."},
    )

    def __init__(self, *args, application, **kwargs):
        super().__init__(*args, initial={"sent_cv_version": application.sent_cv_version_id}, **kwargs)
        self.fields["sent_cv_version"].queryset = CVVersion.objects.filter(
            posting_key__in=application.posting_keys.values("key"),
        ).only("created_at").order_by("-created_at", "-pk")


class ApplicationStatusForm(forms.Form):
    status = forms.ChoiceField(
        label="Estado",
        choices=ApplicationStatus.submitted_choices(),
        error_messages={
            "required": "Selecciona un estado.",
            "invalid_choice": "Selecciona un estado válido.",
        },
    )


class CriteriaForm(forms.ModelForm):
    class Meta:
        model = Criteria
        fields = ["keywords", "location", "modality"]
        labels = {"keywords": "Términos", "location": "Ubicación", "modality": "Modalidad"}
        help_texts = {"keywords": "Separa los términos con comas. Basta una coincidencia en el puesto o la descripción."}

    def clean_keywords(self):
        keywords = [term.strip() for term in self.cleaned_data["keywords"].split(",") if term.strip()]
        if not keywords:
            raise forms.ValidationError("Introduce al menos un término.")
        return ", ".join(dict.fromkeys(keywords))
