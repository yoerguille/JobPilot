from django import forms

from .models import Criteria


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
