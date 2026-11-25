# JobPilot

Aplicación local para buscar ofertas de backend en Greenhouse y abrir el anuncio original. Guarda un conjunto de criterios en SQLite para las siguientes visitas.

## Arranque local

Desde la raíz del proyecto, con Python 3.10 o posterior. En este directorio compartido, ejecuta los comandos desde WSL.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Abre [JobPilot](http://127.0.0.1:8000/). **Guardar criterios** guarda el formulario sin consultar Greenhouse. **Buscar ofertas** guarda los criterios y consulta las bolsas configuradas. El título de cada resultado abre el anuncio original.

## Criterios y cobertura

- La búsqueda empieza en España, con todas las modalidades y los términos backend, junior, Python, API e integraciones. Se puede cambiar la ubicación, la modalidad y la lista de términos separados por comas.
- Coincidir con un término completo en el título o la descripción basta para pasar el filtro de texto. La ordenación da prioridad a la ubicación confirmada, las coincidencias en el título y las señales de nivel junior.
- Para España se reconocen el país y un conjunto de ciudades y regiones habituales. Las ofertas remotas con ubicación genérica, como «Remote» o «EMEA», se muestran como pendientes de confirmar. Al elegir una modalidad concreta se incluyen solo anuncios donde se reconoce esa modalidad. La ubicación y la modalidad se extraen de texto libre, así que su cobertura depende de cómo se redacte el anuncio.
- Edita `GREENHOUSE_BOARDS` en `jobpilot/settings.py` para cambiar el conjunto de empresas. La clave es el identificador de la bolsa pública y el valor es el nombre que se muestra. La selección inicial contiene Typeform, Grafana Labs y Elastic. Cada consulta usa un tiempo de espera de cinco segundos para operaciones de red y los fallos se muestran por empresa. [Documentación de Job Board API](https://docs.greenhouse.io/job-board.html)

## Pruebas

```sh
.venv/bin/python manage.py test
.venv/bin/python manage.py check
```

La suite sustituye el acceso a la red por respuestas de prueba. Para comprobar la integración real, pulsa **Buscar ofertas** con conexión a Greenhouse y abre el título de un resultado.
