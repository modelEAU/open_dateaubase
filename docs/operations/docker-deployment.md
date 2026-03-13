# Docker Deployment

!!! note "Stub"
    This page is a placeholder. Docker deployment documentation will be written here.

## Overview

The `docker-compose.yml` at the project root orchestrates the full stack locally:

- **db** — SQL Server (Azure SQL Edge image)
- **db-init** — one-shot container that applies schema and seed data
- **api** — FastAPI service
- **importer** — table-import service (runs once, then exits)

## Quick Start

```bash
# Copy and fill in credentials
cp .env.docker.example .env.docker

# Start everything
docker compose up -d

# Tail logs
docker compose logs -f api
```

## Topics to document

- [ ] Environment variables and `.env.docker` reference
- [ ] How `db-init` works and how to re-run it against an existing volume
- [ ] Building custom images (`Dockerfile.api`, `Dockerfile.importer`)
- [ ] Persisting data across restarts (`mssql_data` volume)
- [ ] Running the importer on a schedule inside Docker
- [ ] Production considerations (resource limits, healthchecks, secrets management)
- [ ] Differences from the Windows Server deployment
