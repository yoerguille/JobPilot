# JobPilot

A local app for finding backend jobs on Greenhouse and opening the original postings. It saves one set of search criteria in SQLite for future visits.

## Run locally

Use Python 3.10 or later. Run these commands from the project root. In the shared workspace, use WSL.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Open [JobPilot](http://127.0.0.1:8000/). **Save criteria** (`Guardar criterios`) saves the form without querying Greenhouse. **Search jobs** (`Buscar ofertas`) saves the criteria and queries the configured boards. **View original posting** (`Ver anuncio original`) opens the listing in a new tab.

## Search criteria and coverage

- The default search covers Spain and all work arrangements, using the terms backend, junior, Python, API, and integrations. You can change the location, work arrangement, and comma-separated search terms.
- One whole-term match in the title or description is enough to pass the text filter. Results prioritize confirmed locations, title matches, and signs of junior seniority.
- For Spain, the app recognizes the country and a set of common cities and regions. Remote listings with broad locations such as “Remote” or “EMEA” are marked as pending confirmation. Selecting a specific work arrangement includes only postings where the app recognizes that arrangement. Location and work arrangement are inferred from free text, so coverage depends on how each posting is written.
- Edit `GREENHOUSE_BOARDS` in `jobpilot/settings.py` to change the set of companies. Each key is the public board identifier and each value is the name to display. The initial selection is Typeform, Grafana Labs, and Elastic. Each request uses a five-second network timeout, and failures are shown by company. [Greenhouse Job Board API documentation](https://docs.greenhouse.io/job-board.html)

## Build the styles

The compiled CSS is included. To rebuild it after editing the templates or `assets/jobpilot.css`, use Node.js 24 and npm from the project root.

```sh
npm ci
npm run build:css
```

## Tests

```sh
.venv/bin/python manage.py test
.venv/bin/python manage.py check
```

The test suite uses fixture responses in place of network requests. To verify the live integration, select **Search jobs** with access to Greenhouse and then select **View original posting** on a result.
