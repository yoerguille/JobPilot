function enableRemoval(entry) {
    const fields = entry.querySelector("[data-cv-entry-fields]");
    const inputs = fields.querySelectorAll("input, select, textarea");
    const deleteField = entry.querySelector("[data-cv-delete-field]");
    const checkbox = deleteField.querySelector('input[type="checkbox"]');
    const button = entry.querySelector("[data-toggle-cv-entry]");

    function updateRemoval() {
        fields.hidden = checkbox.checked;
        for (const input of inputs) {
            input.disabled = checkbox.checked;
        }
        button.textContent = checkbox.checked ? "Deshacer eliminación" : "Eliminar bloque";
    }

    deleteField.hidden = true;
    button.hidden = false;
    updateRemoval();
    button.addEventListener("click", () => {
        checkbox.checked = !checkbox.checked;
        updateRemoval();
    });
}

for (const button of document.querySelectorAll("[data-add-cv-entry]")) {
    const section = button.closest("[data-cv-section]");
    const total = section.querySelector(`[name="${section.dataset.cvSection}-TOTAL_FORMS"]`);
    const entries = section.querySelector("[data-cv-entries]");
    const template = section.querySelector("[data-cv-entry-template]");

    entries.querySelectorAll("[data-cv-entry]").forEach(enableRemoval);
    button.hidden = false;
    button.addEventListener("click", () => {
        const index = Number(total.value);
        const entry = template.content.cloneNode(true);
        for (const element of entry.querySelectorAll("[id], [name], [for], [aria-describedby]")) {
            for (const attribute of ["id", "name", "for", "aria-describedby"]) {
                if (element.hasAttribute(attribute)) {
                    element.setAttribute(attribute, element.getAttribute(attribute).replaceAll("__prefix__", index));
                }
            }
        }
        const title = entry.querySelector("[data-cv-entry-title]");
        title.textContent = `${title.textContent} ${index + 1}`;
        enableRemoval(entry.querySelector("[data-cv-entry]"));
        const firstField = entry.querySelector('input:not([type="hidden"])');
        entries.append(entry);
        total.value = index + 1;
        firstField.focus();
    });
}
