# Changelog

## Unreleased

- Defined the MVP scope for finding junior backend jobs in Spain, using Python, Django, HTML templates, and SQLite for the local app.
- Implemented stage one with editable, persistent search criteria, public Greenhouse boards for Typeform, Grafana Labs, and Elastic, per-company error messages, and links to the original postings. Remote listings with unclear geographic eligibility are marked as pending confirmation.
- Added this changelog and updated `AGENTS.md` to require a changelog entry for every project change.
- Started version control for the validated first stage and excluded virtual environments, installed dependencies, local databases, and credential files.
- Applied Tailwind to the search screen and added a reproducible CSS build. **View original posting** opens the listing in a new tab.
- Translated the README and changelog into English and documented the English-language convention for code and project documentation in `AGENTS.md`.
- Translated `AGENTS.md` into English and applied the existing English-language convention to that file.
- Added Prima and Lodgify through the public Lever API. Searches use shared criteria, combine results with the same posting URL, and show per-board failures alongside results from available boards.
- Added persistent first-seen dates and new and previous filters for the latest search. Refined technical and junior relevance and added labels for stated, missing, or unclear years of experience.
- Recognized plural graduate job titles as a junior ranking signal.
- Excluded postings with senior titles from search results.
- Grouped clear duplicate vacancies across posting URLs, retained their original source links, and shared first-seen dates with newly discovered links.
- Documented MVP completion, the roadmap for application tracking, CV generation, and hiring news, and the branch workflow for future changes.
- Added persistent application records, canonical posting links, and dated status history for the first stage of application tracking.
- Added an action to mark search results as applied and open their saved application details.
