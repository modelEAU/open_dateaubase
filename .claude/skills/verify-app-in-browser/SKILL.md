---
name: verify-app-in-browser
description: "Protocol for running the open_datEAUbase stack and verifying the Streamlit app in a real browser. Use when asked to run the app, run the e2e/browser tests, smoke-test in a browser, or verify a UI change end-to-end. Covers bringing up MSSQL + demo seed + API + app, running Playwright (-m browser) tests, and driving the live app interactively with the Claude-in-Chrome tools. Triggers: run the app, browser test, e2e, smoke test, verify in browser, does it work in the browser, playwright."
---

# Verify the open_datEAUbase app in a browser

Protocol for running the stack and confirming the app works for real. Pair with
`write-streamlit-tests` (which tier to write) and `dateaubase-app-map` (the flows).

## Tier order — cheap to expensive

1. **Headless first (seconds, no stack):** `uv run pytest tests/app/ tests/unit/`.
   Catches logic/validation regressions before you pay for a browser.
2. **Bring the stack up** (below).
3. **Browser tests:** `uv run pytest tests/e2e/ -m browser`.
4. **Interactive verification** with Claude-in-Chrome when authoring/debugging a flow.

## Bring up the stack

`init.sql` (run by the `init` compose profile) loads schema + vocabulary +
`seed_fixtures.sql` only. The demo data lives in `sql/seed_demo.sql` and must be applied
**on top** — it provides the `TEST_`-prefixed Site / ProcessUnit / Campaign / LabPanel
rows the browser tests rely on.

Use the helper:

```bash
scripts/dev_stack.sh up      # db + init.sql + seed_demo.sql + api(8000) + app(8501)
scripts/dev_stack.sh down    # tear everything down
```

Or manually:

```bash
docker compose up -d db
docker compose --profile init up db-init        # runs sql/init.sql, waits, exits
# apply demo data (depends on vocabulary + fixtures already loaded by init.sql):
docker compose exec -T db /opt/mssql-tools/bin/sqlcmd \
  -S localhost,1433 -U SA -P 'StrongPwd123!' -b -I < sql/seed_demo.sql
uv run uvicorn api.main:app --reload &                # API at :8000
uv run streamlit run app/Home.py &                    # app at :8501
```

App: <http://localhost:8501>  ·  API docs: <http://localhost:8000/docs>

## Run the browser tests

```bash
uv run pytest tests/e2e/ -m browser
```

`tests/e2e/conftest.py` auto-skips (does not fail) when :8501 is unreachable, so this is
safe to leave in CI and safe to run before the stack is up. First run needs the browser
binary: `uv run playwright install chromium`.

## Interactive verification (Claude-in-Chrome)

When a flow is hard to assert blindly, drive the live app and look:

1. Load the chrome tools (`ToolSearch select:mcp__claude-in-chrome__tabs_context_mcp`
   then the navigate/computer/read tools as needed).
2. `tabs_create_mcp` → navigate to `http://localhost:8501`.
3. Walk a flow from `dateaubase-app-map` (e.g. Lab Ingest → series_picker cascade).
   Screenshot key states; use `gif_creator` for multi-step flows worth sharing.
4. `read_console_messages` (filter with a pattern) to catch JS / network / 401 errors.
5. Do **not** trigger native JS dialogs — they freeze the extension.

## On failure

Capture: a screenshot, the console output, and the uvicorn + streamlit logs. Hand the
bundle to the `diagnose` skill. Never report the change verified without a green run —
state plainly what passed, what failed, and what was skipped.
