# Deployment & Operations Guide

## Prerequisites

On the Windows Server, install before running any script:

- **SQL Server 2025** (Standard or Enterprise for backups; Express works for schema-only)
- **SQL Server Management Studio (SSMS) 20+** — provides `sqlcmd.exe` and ODBC Driver 18
- **uv** — Python environment manager (`winget install astral-sh.uv`)
- **NSSM** — Non-Sucking Service Manager, used to wrap Python processes as Windows services (`winget install NSSM.NSSM`)

Clone the repository to your target machine (e.g. `C:\open_dateaubase`) and create a `.env` file from `.env.example`.

---

## 1. Deploy the Database

Run once per environment to create the database and apply the full schema.

```powershell
# From an elevated PowerShell prompt:
.\scripts\deploy\Deploy-Database.ps1 `
    -ServerInstance "DBSERVER2025" `
    -DatabaseName   "open_dateaubase_prod" `
    -DbPassword     "YourStrongPassword!" `
    -InstallDir     "C:\open_dateaubase" `
    -WithBackupJobs `
    -BackupDir      "D:\Backups"
```

**What it does:**

1. Creates the database with your chosen name
2. Applies the v1.0.0 baseline schema
3. Runs the consolidated migration to v2.1.0
4. Sets the recovery model to FULL (required for point-in-time restore)
5. Installs SQL Agent backup jobs (`-WithBackupJobs`)

At the end it prints a `.env` snippet — paste those values into your `C:\open_dateaubase\.env` file before starting the services.

**Flags:**

| Flag | Purpose |
|------|---------|
| `-WithSeedData` | Load reference data (equipment, parameters, sites). Use for dev/staging only. |
| `-WithBackupJobs` | Install SQL Agent backup schedule. Requires Standard/Enterprise. |
| `-Force` | Drop and recreate an existing database. **Destroys all data.** |
| `-WindowsAuth` | Use Windows Authentication instead of a SQL login. |

---

## 2. Deploy the Application Services

Run once per environment after the database is ready.

```powershell
.\scripts\deploy\Deploy-OpenDateaubase.ps1 `
    -InstallDir      "C:\open_dateaubase" `
    -LogDir          "C:\Logs\open_dateaubase" `
    -EnvFile         "C:\open_dateaubase\.env" `
    -ImporterConfig  "C:\open_dateaubase\config\import.yaml"
```

**What it installs as Windows services (auto-restart on failure):**

- `open_dateaubase-api` — FastAPI on port 8000; logs → `C:\Logs\open_dateaubase\api\`
- `open_dateaubase-app` — Streamlit on port 8501; logs → `C:\Logs\open_dateaubase\app\`
- `open_dateaubase-proxy` — nginx reverse proxy on port 80
- A Scheduled Task for the table importer (runs every N minutes)

**To redeploy only one component** (e.g. after updating the API):

```powershell
.\scripts\deploy\Deploy-OpenDateaubase.ps1 ... -SkipApp -SkipImporter -SkipProxy
```

**To uninstall everything:**

```powershell
.\scripts\deploy\Deploy-OpenDateaubase.ps1 ... -Uninstall
```

---

## 3. Backups

If you deployed with `-WithBackupJobs`, SQL Server Agent runs four jobs automatically:

| Job | Schedule | Retention |
|-----|----------|-----------|
| Full backup | Sundays 02:00 | 28 days |
| Differential backup | Mon–Sat 02:00 | 14 days |
| Log backup | Every 4 hours | 7 days |
| Cleanup | Daily 03:00 | (enforces above) |

Backup files land in `D:\Backups\<DatabaseName>\{full,diff,log}\`.

**To verify the jobs are healthy**, run this in SSMS:

```sql
-- scripts/maintenance/03_verify_backup_jobs.sql
-- Shows job status, last run outcome, and next scheduled runs
```

**To restore to a point in time**, use SSMS → Tasks → Restore → Timeline.
Select the full + differential + log chain. The FULL recovery model (set during deploy) is what makes this possible.

---

## 4. Run Migrations

When a new version of the schema is released, apply it to an existing database without touching the data:

```powershell
# Preview what would run (no changes made):
.\scripts\deploy\Run-Migrations.ps1 `
    -ServerInstance "DBSERVER2025" `
    -DatabaseName   "open_dateaubase_prod" `
    -DbPassword     "YourStrongPassword!" `
    -InstallDir     "C:\open_dateaubase" `
    -DryRun

# Apply:
.\scripts\deploy\Run-Migrations.ps1 `
    -ServerInstance "DBSERVER2025" `
    -DatabaseName   "open_dateaubase_prod" `
    -DbPassword     "YourStrongPassword!" `
    -InstallDir     "C:\open_dateaubase"
```

The script reads the `SchemaVersion` table, skips already-applied migrations, and asks for confirmation before making changes.

**Before migrating production**, take a manual backup in SSMS (right-click database → Tasks → Back Up) so you have a clean restore point independent of the scheduled jobs.

**To roll back** (only if the database contains no v2.x-only data): the rollback script is printed at the end of every migration run. Open it in SSMS and execute it manually — rollbacks are intentionally not automated.
