# JobPilot

A local app for finding backend jobs on Greenhouse and Lever and opening the original postings. The job-search MVP is complete. It saves search criteria in SQLite, flags new matches, and groups clear duplicates while keeping their source links.

## Roadmap

1. **Application tracking.** Save an offer by marking it as applied. Keep a dated status history in a dedicated view, including interviews, technical assessments, and rejections.
2. **CV tailoring and generation.** Create a base profile with verified experience, projects, and education. Generate and review a CV for an offer using an agreed structure and predefined styles. Export and save versions, and link each application to the exact version sent.
3. **Hiring news.** Add a separate view for technology hiring announcements in Spain. Show the headline, date, source, short excerpt, and link to the original article. Mark new items and use a thumbnail when the source provides one for that use. Evaluate [Xataka's RSS](https://www.xataka.com/xataka/suscribete-a-xataka) and [RTVE's Economy RSS](https://www.rtve.es/rss/) first. [RTVE's employment portal](https://www.rtve.es/aqui-hay-trabajo/), [NoticiasTrabajo](https://www.noticiastrabajo.es/), and [Europa Press Economía](https://www.europapress.es/economia/) are candidates pending verification of a suitable feed or API. Link to the original company announcement when available.

The InfoJobs integration is on hold while its developer portal is closed to new application registrations. Adzuna is a candidate for a search trial to assess Spanish coverage and the detail its API returns. Automated application submission remains outside the current roadmap.

## Run locally

Use Python 3.10 or later. Run these commands from the project root. In the shared workspace, use WSL.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Open [JobPilot](http://127.0.0.1:8000/). **Save criteria** (`Guardar criterios`) saves the form without querying the sources. **Search jobs** (`Buscar ofertas`) saves the criteria and queries the configured boards. **View original posting** (`Ver anuncio original`) opens the listing in a new tab.

## Search criteria and coverage

- The default search covers Spain and all work arrangements, using the terms backend, junior, Python, API, and integrations. You can change the location, work arrangement, and comma-separated search terms.
- One whole-term match in the title or description is enough to pass the text filter. Postings with senior titles are excluded from every search. Results prioritize confirmed locations, relevant technical and title matches, junior titles, and clearly stated experience around two or three years. The result explains the matching terms and any ranking signals used.
- For Spain, the app recognizes the country and a set of common cities and regions. Remote listings with broad locations such as “Remote” or “EMEA” are marked as pending confirmation. Selecting a specific work arrangement includes only postings where the app recognizes that arrangement. The app uses structured source data when available and falls back to free text, so coverage depends on the information each posting provides.
- Edit `GREENHOUSE_BOARDS` in `jobpilot/settings.py` to change the set of companies. Each key is the public board identifier and each value is the name to display. The initial selection is Typeform, Grafana Labs, and Elastic. [Greenhouse Job Board API documentation](https://docs.greenhouse.io/job-board.html)
- Edit `LEVER_BOARDS` in the same file to configure Lever. Each key is the public site identifier, and each value contains the company name and API region (`global` or `eu`). The initial boards are Lodgify (global) and Prima (EU). [Lever Postings API documentation](https://github.com/lever/postings-api)
- Both sources use the same search criteria. Results sharing a canonical posting URL or a company and vacancy reference are grouped. Without a shared reference, postings from different sources must match on company, title, location, and known work arrangement and have closely matching descriptions (at least 30 words each and 97% word-sequence similarity). Conflicting references keep distinct URLs separate. Each group retains the original links and their sources.
- Each board request uses a five-second network timeout by default. If a board fails, the app identifies its source and company and shows any matches from successful boards.

## New and previous results

Each canonical posting URL is recorded the first time it matches a search. A group uses the earliest first-seen date among its links, and newly discovered links in that group inherit that date. The first search marks all its matches as new. A posting remains new within the saved results of the search that first found it. On later searches it appears as previous when it matches again, even if a board was temporarily unavailable or the criteria changed.

Use **All** (`Todas`), **New** (`Nuevas`), or **Previous** (`Anteriores`) to filter the latest results. Reloading or changing this filter does not query the sources again. A failed board's matches may be absent from the latest results, while previously recorded first-seen dates are preserved.

Experience labels distinguish explicit years and ranges, missing years, and ambiguous statements. A posting with conflicting or unclear numbers is flagged for confirmation. The labels reflect the wording recognized in the posting.

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

The test suite uses fixture responses in place of network requests. To verify the live integration, select **Search jobs** with access to Greenhouse and Lever and then select **View original posting** on a result from each source.
