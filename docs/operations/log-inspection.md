# Log Inspection (OpenObserve)

The stack centralises every service's logs on disk under the per-environment
`LogDir` (see [deployment.md §3](deployment.md#3-logging)). To search and filter
them from a browser instead of RDP-ing into the box, the deploy installs a
small, self-contained log viewer:

- **OpenObserve** (`OpenDateaubase-<Tag>-LogViewer`) — a single binary that is
  the web UI, the store, and a full-text search engine. It binds to
  `127.0.0.1:<LogViewerPort>` (production `5080`, staging `5090`) and is exposed
  **only** through nginx at `/logs/`.
- **Vector** (`OpenDateaubase-<Tag>-LogShip`) — a single binary that tails
  `LogDir\{api,app,nginx,importer}\*.log`, tags each record with `environment`
  and `service` (from the sub-folder), merges multi-line Python tracebacks into
  one event, and ships everything to OpenObserve.

Both are NSSM-managed Windows services, namespaced per environment exactly like
the API/App/Proxy, so staging and production never collide on a shared host.

## Opening the viewer

Browse to **`http://<host>/logs/`** (e.g. `http://<host>:8080/logs/` for
staging, whose proxy port is `8080`).

The data lands in a single stream named **`open_dateaubase`** under the
`default` organization. Filter by the `environment` and `service` fields to
narrow to one tier/component.

## Credentials

The OpenObserve root account and the Vector shipper share one set of
credentials so they always match:

- **User** — `LOGVIEWER_USER` from the `.env` file, or
  `admin@open_dateaubase.local` if unset.
- **Password** — `LOGVIEWER_PASSWORD` from the `.env` file. If unset, the deploy
  generates a strong password on first run and reuses it on subsequent runs
  (re-runs are idempotent). It is written to:

  ```text
  <LogDir>\logviewer\credentials.txt
  ```

  (e.g. `C:\Logs\open_dateaubase\production\logviewer\credentials.txt`). The
  deploy summary prints this path.

To pin your own credentials, set both keys in the environment's `.env` file
(see `.env.example`) before deploying.

## Retention (set-and-forget)

OpenObserve is configured with `ZO_COMPACT_DATA_RETENTION_DAYS=30`, so data older
than 30 days is compacted away automatically and disk self-manages. Change the
window by editing the `ZO_COMPACT_DATA_RETENTION_DAYS` value in the Step 10 block
of `scripts/deploy/Deploy-OpenDateaubase.ps1`
and re-running the deploy.

## Skipping the viewer

Pass `-SkipLogViewer` to `Deploy-OpenDateaubase.ps1` to deploy everything except
the viewer and shipper. The nginx `/logs/` route is omitted when the viewer is
skipped, and `-Uninstall` removes both services along with the rest.

```powershell
.\scripts\deploy\Deploy-OpenDateaubase.ps1 `
    -InstallDir "C:\open_dateaubase" -Environment production `
    -ImporterConfig "C:\open_dateaubase\importer\configs\wwtp_plc_scada.yaml" `
    -SkipLogViewer
```

## On-target verification

1. `Get-Service OpenDateaubase-<Tag>-LogViewer, OpenDateaubase-<Tag>-LogShip`
   both report `Running`.
2. Browse `http://<host>/logs/` and log in (creds file above).
3. `Restart-Service OpenDateaubase-<Tag>-API`, then confirm the restart lines
   appear in the `open_dateaubase` stream within a few seconds.
4. Re-run the deploy — services are reconfigured in place, not duplicated, and
   the generated password is preserved.

> **Note on `ZO_BASE_URI`.** OpenObserve serves under the `/logs` subpath
> (`ZO_BASE_URI=/logs`) so its SPA assets resolve behind nginx. If the UI loads
> blank, confirm assets are requested under `/logs/web/…` and that the nginx
> `location /logs/` block (with WebSocket-upgrade headers) is present in the
> environment's `nginx.conf`. The deploy's HTTP health probe is best-effort: the
> service reaching `Running` is the authoritative liveness signal.

## Local dev (Docker)

A compose override mirrors the prod setup using the same two tools, sourcing
logs from the Docker daemon instead of files:

```bash
docker compose -f docker-compose.yml -f docker-compose.logs.yml up
```

Open `http://localhost:5080` and log in with the `ZO_ROOT_USER_*` credentials
(defaults: `admin@open_dateaubase.local` / `Complexpass#123`; override with
`LOGVIEWER_USER` / `LOGVIEWER_PASSWORD`). Generate traffic by hitting the app and
API, then confirm the `open_dateaubase` stream fills with searchable lines tagged
`environment=docker` and a `service` derived from each container name. The dev
pipeline config is
`scripts/deploy/vector/vector.docker.toml`.
