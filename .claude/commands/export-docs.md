Build the MkDocs documentation site with fresh run data.

Run these steps in order:
1. `python scripts/export_runs.py` — exports `run_history.json` → `docs/data/runs.json`
2. `mkdocs build` — builds the static site to `./site/`

Report the result of each step. If `scripts/export_runs.py` doesn't exist yet, say so and note that the docs site setup from `docs/PLAN_DOCS_SITE.md` hasn't been implemented yet.

If `mkdocs` is not installed, suggest: `pip install -e ".[docs]"`

To serve locally instead of building, the user can run: `mkdocs serve`
