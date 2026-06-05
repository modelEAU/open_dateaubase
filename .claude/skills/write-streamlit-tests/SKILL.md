---
name: write-streamlit-tests
description: "Protocol for writing tests for the open_datEAUbase Streamlit app. Use when asked to write, add, or improve tests for a page or component under app/. Covers choosing the tier (headless streamlit.testing.v1.AppTest vs Playwright browser test), the project's AppTest harness + mock pattern, where files go, and how to self-check. Triggers: write a test for the app, test this page, test the series picker, add app coverage, AppTest, streamlit testing, playwright test."
---

# Writing tests for the open_datEAUbase Streamlit app

Protocol an agent follows to add a test. Pair with `dateaubase-app-map` (what the app is)
and `verify-app-in-browser` (how to run browser tests).

## Two tiers — pick deliberately

| Tier | Use for | Lives in | Marker | Needs running stack? |
|---|---|---|---|---|
| **AppTest** (`streamlit.testing.v1.AppTest`) | validation logic, session-state transitions, branch/error coverage, "does the script run" | `tests/app/` | none (runs in default unit suite) | No — api_client is mocked |
| **Playwright** (`pytest-playwright`) | real browser render, cross-page nav, true widget DOM, file upload, cascading pickers AppTest can't fully drive | `tests/e2e/` | `@pytest.mark.browser` | Yes — see `verify-app-in-browser` |

Default to **AppTest**. Reach for Playwright only when the thing under test genuinely
requires a browser. Most flows are covered headlessly and far more reliably.

## Protocol A — write the test

1. **Orient.** Read `dateaubase-app-map`. Run the `developing-with-streamlit` discovery
   script (path in that skill) if you need Streamlit mechanics.
2. **Locate the mock surface.** Open the page/component and list *every* `api_client`
   function it imports and calls — both lookups (loaded at top-of-script) and mutations.
   Missing a lookup mock makes the page error before your flow runs.
3. **Choose the tier** from the table above.
4. **Write it** following the established pattern (below).
5. **Self-check:** `uv run pytest tests/app/ tests/unit/` stays green. (Per project
   CLAUDE.md, only run the unit/app tiers by default — integration `-m db` and `-m
   browser` are opt-in.)

## AppTest pattern (copy `tests/app/test_campaign_wizard.py`)

Two pieces:

1. **A harness module** in `tests/app/` (see `wizard_harness.py`): not a test file — a
   tiny script AppTest executes to provide a Streamlit context. It puts the repo root on
   `sys.path`, calls the component's `render_*()`, and nothing else. One harness per
   component you drive.

2. **The test file** — drives `AppTest.from_file(HARNESS)`, pre-seeds
   `at.session_state`, runs, and asserts on `at.<element>`.

```python
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, patch
from streamlit.testing.v1 import AppTest

HARNESS = str(Path(__file__).parent / "lab_ingest_harness.py")
MOD = "app.pages.lab_ingest"   # patch where names are USED, not app.api_client

_LOOKUP_SPECS = [
    (f"{MOD}.list_parameters_lookup", [{"parameter_id": 1, "parameter_name": "pH"}]),
    # ...one entry per lookup the page calls...
]

def _run(seed: dict | None = None):
    at = AppTest.from_file(HARNESS)
    with ExitStack() as stack:
        for target, ret in _LOOKUP_SPECS:
            stack.enter_context(patch(target, return_value=ret))
        # mutations: stack.enter_context(patch(f"{MOD}.ingest_lab", MagicMock(return_value=...)))
        if seed:
            for k, v in seed.items():
                at.session_state[k] = v
        at.run()
    return at
```

**Key rules**
- **Patch where imported.** Target `f"{MOD}.list_parameters_lookup"` (the page's
  namespace), never `app.api_client.list_parameters_lookup`. The page did
  `from app.api_client import list_parameters_lookup`, so that's the binding to replace.
- Pre-seed `session_state` to start mid-flow (e.g. seed `lab_session` with a chosen mode
  and a selected series; seed `spkr_{field}_selected` for the picker).
- Assert on rendered elements (`at.error`, `at.button`, `at.text_input`, `at.selectbox`)
  and on mock call args for mutations. Drive widgets via `.set_value(...).run()` /
  `.click().run()`.
- One distinct branch per test; name tests after the branch (the campaign wizard file's
  coverage-map docstring is the model).

## Playwright pattern (`tests/e2e/`)

- Mark with `@pytest.mark.browser`; use the `page` and `base_url` fixtures from
  `tests/e2e/conftest.py` (auto-skips when the stack is down).
- Drive against seeded demo data (`sql/seed_demo.sql`, `TEST_`-prefixed rows). Select by
  visible text / test ids; prefer `get_by_role`/`get_by_text`.
- Keep these as thin smoke checks (page loads, key flow completes), not exhaustive logic
  coverage — that belongs in AppTest.
- See `verify-app-in-browser` for bringing the stack up.

## Done means
- New test added in the right tier/dir.
- `uv run pytest tests/app/ tests/unit/` green.
- If Playwright: it passes with the stack up and *skips* (not fails) with it down.
