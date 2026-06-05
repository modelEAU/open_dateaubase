#!/usr/bin/env bash
# dev_stack.sh — bring the open_datEAUbase stack up/down for browser (e2e) testing.
#
#   scripts/dev_stack.sh up     # db + init.sql + seed_demo.sql + API(:8000) + app(:8501)
#   scripts/dev_stack.sh down   # stop API/app and tear down containers
#
# init.sql (run by the `init` compose profile) loads schema + vocabulary +
# seed_fixtures.sql. The demo rows (TEST_-prefixed) live in sql/seed_demo.sql and are
# applied on top here — that's the data the browser tests exercise.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

DC="docker compose"
SA_PASS="StrongPwd123!"
PID_DIR=".dev_stack"
mkdir -p "$PID_DIR"

up() {
  echo "==> Starting MSSQL"
  $DC up -d db

  echo "==> Initialising schema (init.sql via init profile)"
  $DC --profile init up db-init

  echo "==> Applying demo seed (sql/seed_demo.sql)"
  $DC exec -T db /opt/mssql-tools/bin/sqlcmd \
    -S localhost,1433 -U SA -P "$SA_PASS" -b -I < sql/seed_demo.sql

  echo "==> Starting API on :8000"
  APP_DEV_AUTO_LOGIN=0 uv run uvicorn api.main:app --port 8000 \
    > "$PID_DIR/api.log" 2>&1 &
  echo $! > "$PID_DIR/api.pid"

  echo "==> Starting Streamlit app on :8501"
  uv run streamlit run app/Home.py --server.port 8501 --server.headless true \
    > "$PID_DIR/app.log" 2>&1 &
  echo $! > "$PID_DIR/app.pid"

  echo "==> Waiting for app on :8501"
  for _ in $(seq 1 60); do
    if curl -sf http://localhost:8501/ >/dev/null 2>&1; then
      echo "Stack up: app http://localhost:8501  ·  API http://localhost:8000/docs"
      return 0
    fi
    sleep 1
  done
  echo "App did not come up in time; see $PID_DIR/app.log" >&2
  return 1
}

down() {
  for name in app api; do
    if [[ -f "$PID_DIR/$name.pid" ]]; then
      kill "$(cat "$PID_DIR/$name.pid")" 2>/dev/null || true
      rm -f "$PID_DIR/$name.pid"
    fi
  done
  echo "==> Stopping containers"
  $DC --profile init down
}

case "${1:-}" in
  up)   up ;;
  down) down ;;
  *)    echo "usage: $0 {up|down}" >&2; exit 2 ;;
esac
