# Writing Documentation

This site is built with [MkDocs](https://www.mkdocs.org/) and the Material theme. Most of it you edit by hand, but three parts are generated, so it pays to know which is which before you start changing files.

## What is generated vs. handwritten

| Part | Source | Edit by hand? |
| --- | --- | --- |
| Schema reference (tables, views, value sets, ERD, SQL) | `schema_dictionary/` YAML | No — edit the YAML |
| API reference (`reference/api/openapi.json`) | FastAPI app in `api/main.py` | No — change the API |
| Everything else (tutorials, how-to, explanation) | Markdown in `docs/` | Yes |

The generated files are produced by the pre-build hook in `docs/hooks/call_orchestrator.py` every time MkDocs builds. Do not commit edits to the generated Markdown or `openapi.json` — they will be overwritten on the next build.

## Build and preview

```bash
uv run mkdocs serve   # live preview at http://localhost:8000
uv run mkdocs build   # static site to site/
```

Run the strict build before you push — it is what CI enforces, and it fails on broken internal links:

```bash
uv run mkdocs build --strict
```

## Adding a page

1. Create the Markdown file under the right Diátaxis section:
    - `tutorials/` — learning by doing, start to finish.
    - `how-to/` — a recipe for one specific goal.
    - `reference/` — facts to look up (most of this is generated).
    - `explanation/` — why the model works the way it does.
2. Add it to the `nav` in `mkdocs.yml`.
3. Use relative links to other pages so `--strict` can verify them.

## Voice

Write like a grad student explaining the project to a labmate: short active sentences, concrete examples (`WWTP-IN-01`, `TSS`, `mg/L`), the *why* in one line before the *how*. Skip generic benefit lists and filler.
