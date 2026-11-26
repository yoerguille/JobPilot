# JobPilot

## MVP scope

- Gather job postings from multiple sources in a single search with saved criteria. Show the source, mark postings that are new since the last search, and link to the original posting so the user can decide whether to apply.
- Prioritize junior backend roles involving Python, APIs, and integrations. Exclude postings with clearly senior titles. Label postings that ask for two or three years of experience and flag postings that do not specify how much experience they require.
- Search for roles in Spain across all work arrangements. Include remote openings at foreign companies if they allow working from Spain. If the posting does not make clear where the applicant can work from, mark eligibility as pending confirmation.
- The MVP covers job discovery. See the README for planned modules and source integrations.

## Implementation

- Use Python, Django, HTML templates, and SQLite for the local app.
- Give each source its own connector and return the same posting fields from each connector. Use documented integrations and apply the same search criteria across sources.
- Group duplicates when the match is clear. If a source fails, retain results from the other sources and identify the source that could not be consulted.
- Use explicit rules for filtering and prioritization. Briefly explain why each posting appears and flag any missing information.

## Workflow

- Record every project change in `CHANGELOG.md` as part of the same delivery. Add a brief entry under “Unreleased” describing the change.

Follow this sequence for every implementation stage:

1. Create a new Git branch from the latest `main` before editing project files.
2. Implement and verify the stage on that branch. Share the changes and verification results for review before committing.
3. After the user approves the changes, commit them, push the branch, and open a pull request targeting `main`.
4. Merge through the pull request after the user approves the merge and any required checks pass. Start the next stage from the updated `main`.

## Language

- Write code identifiers, comments, docstrings, and project documentation, including this file, in English.
- Keep the interface and user-facing messages in Spanish.
