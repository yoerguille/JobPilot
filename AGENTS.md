# JobPilot

## Alcance del MVP

- Reúne ofertas de varias fuentes en una sola búsqueda con criterios guardados. Muestra la fuente, marca las ofertas nuevas desde la última búsqueda y enlaza al anuncio original para que el usuario decida si quiere aplicar.
- Prioriza backend junior con Python, APIs e integraciones. Muestra identificadas las ofertas que piden dos o tres años de experiencia y señala cuándo el anuncio no indica cuánta experiencia exige.
- Busca puestos en España en cualquier modalidad. Incluye ofertas remotas de empresas extranjeras si admiten trabajar desde España. Si el anuncio no aclara desde dónde se puede trabajar, muéstralo como pendiente de confirmar.
- Deja la adaptación del CV, el envío de candidaturas y su seguimiento para etapas posteriores.

## Implementación

- Usa Python, Django, plantillas HTML y SQLite para la aplicación local.
- Cada fuente debe tener su propio conector y devolver los mismos campos de oferta. Usa integraciones documentadas y mantén los criterios de búsqueda comunes a todas las fuentes.
- Agrupa duplicados cuando la coincidencia sea clara. Si una fuente falla, conserva los resultados de las demás e indica qué fuente quedó sin consultar.
- Usa reglas explícitas para el filtrado y la priorización. Muestra una razón breve de por qué aparece cada oferta y señala la información que falte.

## Historial de cambios

- Registra cada cambio del proyecto en `CHANGELOG.md` como parte de la misma entrega. Añade una entrada breve en «Unreleased» que describa el cambio.

## Idioma

- Escribe en inglés los identificadores, comentarios y docstrings del código, y la documentación del proyecto. Mantén este archivo en español.
- Mantén en español la interfaz y los mensajes dirigidos al usuario.
