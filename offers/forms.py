from django import forms

from .models import ApplicationStatus, Criteria


class ApplicationStatusForm(forms.Form):
    status = forms.ChoiceField(
        label="Estado",
        choices=ApplicationStatus.choices,
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
