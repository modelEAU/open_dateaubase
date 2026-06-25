# Deployment & Operations Guide

## Prerequisites

On the Windows Server, install before running any script:

- **SQL Server 2025** (Standard or Enterprise for backups; Express works for schema-only)
- **SQL Server Management Studio (SSMS) 20+** — provides `sqlcmd.exe` and ODBC Driver 18
- **uv** — Python environment manager (`winget install astral-sh.uv`)
- **NSSM** — Non-Sucking Service Manager, used to wrap Python processes as Windows services (`winget install NSSM.NSSM`)

Clone the repository to your target machine (e.g. `C:\open_dateaubase`).

---

## Environments

Both deploy scripts take a mandatory **`-Environment`** flag (`staging` or `production`).
The environment drives every per-tier default, so you never hand-set database
names, ports, service names or log paths. Everything is namespaced by environment,
which means staging and production are isolated from each other.

| Setting | `staging` | `production` |
|---|---|---|
| Database name | `open_dateaubase_staging` | `open_dateaubase_production` |
| Browser (proxy) port | `8080` | `80` |
| API port | `8010` | `8000` |
| App port | `8511` | `8501` |
| Log viewer port (localhost) | `5090` | `5080` |
| Windows services | `OpenDateaubase-Staging-{API,App,Proxy,LogViewer,LogShip}` | `OpenDateaubase-Production-{API,App,Proxy,LogViewer,LogShip}` |
| Importer task | `OpenDateaubase-Staging-Importer` | `OpenDateaubase-Production-Importer` |
| Log directory | `C:\Logs\open_dateaubase\staging` | `C:\Logs\open_dateaubase\production` |
| Env file (default) | `<InstallDir>\.env.staging` | `<InstallDir>\.env.production` |
| nginx prefix | `<InstallDir>\tools\nginx\staging` | `<InstallDir>\tools\nginx\production` |

Any derived value can be overridden with its explicit flag (`-DatabaseName`,
`-LogDir`, `-EnvFile`, `-ApiPort`, `-AppPort`, `-ProxyPort`).

The profile table lives in one place — `scripts/deploy/EnvironmentProfiles.psm1`.
Add a tier (e.g. a `dev` tier allowed to load seed data) there and in the
`ValidateSet` attributes of the deploy scripts.

> **One environment per host is recommended.** Co-tenanting staging and
> production on a single box is *supported* (names, ports, log dirs and the
> nginx prefix are all environment-scoped, so they will not collide) but not
> encouraged — a staging mistake should not share a host with production.

Create each environment's `.env` file from `.env.example` before deploying its
application tier. The database script prints the exact `DB_*` values to paste in.

---

## 1. Deploy the Database

Run once per environment to create the database and apply the full schema.

```powershell
# From an elevated PowerShell prompt:
.\scripts\deploy\Deploy-Database.ps1 `
    -ServerInstance "DBSERVER2025" `
    -Environment    production `
    -DbPassword     "YourStrongPassword!" `
    -InstallDir     "C:\open_dateaubase" `
    -WithBackupJobs `
    -BackupDir      "D:\Backups"
```

**What it does:**

1. Creates the database (name derived from `-Environment`, e.g. `open_dateaubase_production`)
2. Applies the **v2.0.0 baseline schema** directly (`sql_generation_scripts\v2.0.0_create_mssql.sql`) — v2.0.0 is a fresh-install baseline; there is no v1→v2 migration
3. Applies the **v2.0.0 vocabulary seed** (`sql_generation_scripts\v2.0.0_seed_mssql.sql`)
4. Sets the recovery model to FULL (required for point-in-time restore)
5. Installs SQL Agent backup jobs (`-WithBackupJobs`)

At the end it prints a `.env` snippet — paste those values into the matching
`C:\open_dateaubase\.env.<environment>` file before starting the services.

**Flags:**

| Flag | Purpose |
|------|---------|
| `-WithSeedData` | Load dev/demo data (TEST_ watershed, demo site, sample panels). **Blocked for `staging` and `production`** — the script throws if combined with either. Local Docker dev only. |
| `-WithBackupJobs` | Install SQL Agent backup schedule. Requires Standard/Enterprise. |
| `-Force` | Drop and recreate an existing database. **Destroys all data.** |
| `-WindowsAuth` | Use Windows Authentication instead of a SQL login. |
| `-DatabaseName` | Override the environment-derived database name. |

---

## 2. Deploy the Application Services

Run once per environment after the database is ready. `LogDir`, `EnvFile` and the
ports are all derived from `-Environment`; you only need to point at an importer
config.

```powershell
.\scripts\deploy\Deploy-OpenDateaubase.ps1 `
    -InstallDir      "C:\open_dateaubase" `
    -Environment     production `
    -ImporterConfig  "C:\open_dateaubase\importer\configs\wwtp_plc_scada.yaml"
```

**What it installs as Windows services (auto-restart on failure), for `production`:**

- `OpenDateaubase-Production-API` — FastAPI on port 8000; logs → `C:\Logs\open_dateaubase\production\api\`
- `OpenDateaubase-Production-App` — Streamlit on port 8501; logs → `C:\Logs\open_dateaubase\production\app\`
- `OpenDateaubase-Production-Proxy` — nginx reverse proxy on port 80
- `OpenDateaubase-Production-LogViewer` — OpenObserve log viewer on localhost:5080, exposed via nginx at `/logs/`
- `OpenDateaubase-Production-LogShip` — Vector, tails the log directory and ships to the viewer
- `OpenDateaubase-Production-Importer` — Scheduled Task running the table importer every N minutes
- `OpenDateaubase-Production-LogRotate` — daily 02:00 task that gzips importer logs over 10 MB

(For `staging`, substitute `Staging` and ports 8080/8010/8511, log viewer 5090.)

Skip the log viewer with `-SkipLogViewer`. See
[log-inspection.md](log-inspection.md) for the `/logs/` UI, credentials and the
retention knob.

**To redeploy only one component** (e.g. after updating the API):

```powershell
.\scripts\deploy\Deploy-OpenDateaubase.ps1 `
    -InstallDir "C:\open_dateaubase" -Environment production `
    -ImporterConfig "C:\open_dateaubase\importer\configs\wwtp_plc_scada.yaml" `
    -SkipApp -SkipImporter -SkipProxy
```

**To uninstall one environment** (removes only that tier's services and tasks):

```powershell
.\scripts\deploy\Deploy-OpenDateaubase.ps1 `
    -InstallDir "C:\open_dateaubase" -Environment staging `
    -ImporterConfig "C:\open_dateaubase\importer\configs\wwtp_plc_scada.yaml" `
    -Uninstall
```

---

## 3. Logging

All logs for an environment are centralised on disk under its
`LogDir` (default `C:\Logs\open_dateaubase\<environment>\`):

```text
C:\Logs\open_dateaubase\production\
  api\       stdout.log  stderr.log
  app\       stdout.log  stderr.log
  nginx\     stdout.log  stderr.log  access.log  error.log
  importer\  stdout.log  stderr.log
  logviewer\ stdout.log  stderr.log  credentials.txt
  logship\   stdout.log  stderr.log
  deploy-<timestamp>.log      # full transcript of each deploy run
```

- API / App / nginx services route stdout+stderr via NSSM, which rotates them
  **online at 10 MB**.
- The importer (a Scheduled Task) appends to its own logs; the daily LogRotate
  task gzips any importer log over 10 MB.

These on-disk logs are also indexed for **browser-based search** by the
OpenObserve log viewer (the Vector shipper tails this tree and forwards every
line). Open `http://<host>/logs/` to search/filter instead of RDP-ing in — see
[log-inspection.md](log-inspection.md). The viewer is local to the box; logs are
still not pushed to any third party.

---

## 4. Backups

If you deployed with `-WithBackupJobs`, SQL Server Agent runs four jobs automatically:

| Job | Schedule | Retention |
|-----|----------|-----------|
| Full backup | Sundays 02:00 | 28 days |
| Differential backup | Mon–Sat 02:00 | 14 days |
| Log backup | Every 4 hours | 7 days |
| Cleanup | Daily 03:00 | (enforces above) |

Backup files land in `<BackupDir>\<DatabaseName>\{full,diff,log}\`.

**To verify the jobs are healthy**, run `scripts/maintenance/03_verify_backup_jobs.sql`
in SSMS — it shows job status, last run outcome, and next scheduled runs.

**To restore to a point in time**, use SSMS → Tasks → Restore → Timeline.
Select the full + differential + log chain. The FULL recovery model (set during deploy) is what makes this possible.

---

## 5. Run Migrations

When a new schema version ships, apply it to an existing database without touching
the data. The target database is derived from `-Environment` (or pass `-DatabaseName`).

```powershell
# Preview what would run (no changes made):
.\scripts\deploy\Run-Migrations.ps1 `
    -ServerInstance "DBSERVER2025" `
    -Environment    production `
    -DbPassword     "YourStrongPassword!" `
    -InstallDir     "C:\open_dateaubase" `
    -DryRun

# Apply:
.\scripts\deploy\Run-Migrations.ps1 `
    -ServerInstance "DBSERVER2025" `
    -Environment    production `
    -DbPassword     "YourStrongPassword!" `
    -InstallDir     "C:\open_dateaubase"
```

The script reads the `SchemaVersion` table, skips already-applied migrations, and
asks for confirmation before making changes. The migration catalogue is empty
until the first post-v2.0.0 release ships a migration script.

**Before migrating production**, take a manual backup in SSMS (right-click database → Tasks → Back Up) so you have a clean restore point independent of the scheduled jobs.

**To roll back**: the rollback script (when one exists) is printed at the end of every
migration run. Open it in SSMS and execute it manually — rollbacks are intentionally not automated.
