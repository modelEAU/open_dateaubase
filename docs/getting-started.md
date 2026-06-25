# Getting Started

This guide walks you through running open_datEAUbase locally with Docker, entering your first data, and exploring it in the web app. No prior knowledge of the schema is required.

---

## Prerequisites

| Tool | Minimum version | Notes |
| --- | --- | --- |
| [Docker](https://docs.docker.com/get-docker/) | 24.x | Docker Engine or Docker Desktop |
| [Docker Compose](https://docs.docker.com/compose/install/) | v2 (`docker compose`) | Included in Docker Desktop |
| [git](https://git-scm.com/) | any | For cloning the repository |

Verify your installation:

```bash
docker --version
docker compose version
git --version
```

---

## 1. Clone and configure

```bash
git clone https://github.com/modeleau/open_dateaubase.git
cd open_dateaubase
```

Copy the Docker environment file and set a strong password:

```bash
cp .env.docker.example .env.docker
```

Open `.env.docker` in any editor. The only value you must change before a first run is `DB_PASSWORD`:

```
DB_HOST=db
DB_PORT=1433
DB_NAME=open_dateaubase
DB_USER=SA
DB_PASSWORD=StrongPwd123!        # change this to a strong password
DB_DRIVER=ODBC Driver 18 for SQL Server
```

!!! warning "Password requirements"
    SQL Server requires passwords of at least 8 characters containing uppercase, lowercase, digits, and symbols. The default `StrongPwd123!` is acceptable for local development only — never use it in any shared or internet-facing environment.

---

## 2. Start the stack

```bash
docker compose up --build -d
```

This command builds and starts four services:

| Service | Container | What it does |
| --- | --- | --- |
| `db` | `open_dateaubase_db` | SQL Server (Azure SQL Edge) — persists data in the `mssql_data` Docker volume |
| `db-init` | `open_dateaubase_db_init` | Runs once on first start: creates the database, applies all migrations, and loads seed data |
| `api` | `open_dateaubase_api` | FastAPI REST API on port 8000 |
| `app` | `open_dateaubase_app` | Streamlit web app on port 8501 |

The `db-init` container exits automatically once the schema is ready. All subsequent `docker compose up` calls skip it if the database already exists.

To follow startup logs:

```bash
docker compose logs -f api app
```

The API is ready when you see `Application startup complete` in the `api` log.

---

## 3. Verify the stack is running

Open these URLs in a browser:

| URL | What you should see |
| --- | --- |
| `http://localhost:8501` | Streamlit home page with API status metrics |
| `http://localhost:8000/docs` | Swagger UI listing all REST endpoints |
| `http://localhost:8000/` | JSON response: `{"message": "open_datEAUbase API is running.", ...}` |

If the Streamlit home page shows "Cannot reach API", wait 10–15 seconds for the API container to finish its health check and refresh the page.

---

## 4. Key concepts

Understanding these terms will help you navigate the schema and the web app.

**Site**
A physical location where measurements are collected (e.g., "WWTP Inlet", "River Station 3"). All campaigns and equipment deployments are anchored to a site.

**Equipment Model and Equipment**
An `EquipmentModel` is an instrument make/model (e.g., "s::can spectro::lyser V2"). An `Equipment` instance is a specific physical unit identified by serial number or another unique identifier. One model can have many instances.

**Data Acquisition System (DAS)**
A datalogger, SCADA system, or basestation that collects signals from one or more instruments and transmits them to the database.

**SignalPort**
A named output on a DAS (e.g., a SCADA tag, a serial channel). Each port produces exactly one measurement stream. Tagged mode uses the SCADA tag string as the port identifier; tagless mode uses the equipment identifier directly.

**SCADA tag / tagged vs. tagless mode**
In *tagged mode* the DAS assigns a string tag to each signal (e.g., `INFLUENTV160_NH4`). The importer uses this tag to resolve the `SignalPort`. In *tagless mode* the equipment identifier alone is sufficient — the importer links the port directly to an `Equipment` row and opens a `SignalPortEquipmentHistory` record automatically.

**Channel**
The invariant descriptor of a single measurement stream: which `SignalPort` is measuring which `Parameter`, in which `Unit`, at what `ProcessingDegree`, and with what `DataProvenance` (Sensor, Laboratory, Manual, …). A Channel row is created automatically on first ingest and reused forever — you never create one manually.

**Observation and Value**
Each time a measurement is recorded, an `Observation` row is inserted (timestamp + channel + quality code), followed by one value row in the appropriate table:

| Value type | Storage table | When to use |
| --- | --- | --- |
| Scalar | `dbo.Value` | One number per timestamp (pH, TSS, temperature, …) |
| Vector | `dbo.ValueVector` | A 1-D distribution (spectrum, particle size distribution, …) |
| Matrix | `dbo.ValueMatrix` | A 2-D joint distribution (size × velocity, …) |
| Image | `dbo.ValueImage` | Camera or microscope frame stored as a file reference |

**Campaign**
A time-bounded measurement context that answers "what were we trying to do when this data was collected?" A campaign links equipment deployments, lab analyses, and annotations to a shared purpose and start/end window. Campaign types: `Experiment`, `Operations`, `Commissioning`.

---

## 5. First data entry walkthrough

All steps below use the Streamlit web app at `http://localhost:8501`. The same actions can be performed through the REST API at `http://localhost:8000/docs`.

### 5a. Create a Site

1. In the sidebar, navigate to **Administration > Sites**.
2. Click **Add** and fill in at minimum: Name and Site Type.
3. Save. The new site appears in the table.

### 5b. Create an Equipment Model and Equipment instance

1. Navigate to **Administration > Equipment Models**.
2. Click **Add**. Enter the manufacturer and model name (e.g., "s::can spectro::lyser V2"). Save.
3. Navigate to **Administration > Equipment**.
4. Click **Add**. Select the model you just created, enter a unique identifier (serial number or asset tag), and save.

### 5c. Create a Campaign

1. Navigate to **Campaigns**.
2. Click **New Campaign** to open the campaign wizard.
3. Step through the wizard:
   - Select the site you created in step 5a.
   - Choose a campaign type (Operations is appropriate for routine monitoring).
   - Set a name, start date, and optionally an end date.
   - On the equipment step, add the equipment instance from step 5b.
4. Complete the wizard. The campaign is saved and visible in the campaigns table.

### 5d. Set up a Data Acquisition System and Signal Port (optional)

This step is only required if you are importing data via the YAML-based importer in tagged mode. If you plan to use tagless mode or manual entry, skip to step 5e.

1. Navigate to **Administration > Data Acquisition Systems**.
2. Click **Add**. Enter a name for the DAS (e.g., "Basestation-01"). Save.
3. Navigate to **Administration > Signal Ports**.
4. Click **Add**. Select the DAS, enter the tag string exactly as it appears in your data files, and save.

### 5e. Explore data in the Data Explorer

1. Navigate to **Operations > Explore**.
2. Select a site and a date range. Available channels for that site appear as a list.
3. Select one or more channels and click **Plot** to render the time series.

If you have not yet imported data, the explorer will show no channels. Follow the importer section below to load your first dataset.

---

## 6. Running the importer

The importer reads tabular files (CSV, TSV, proprietary sensor formats) and posts their contents to the API. Configuration is a YAML file that maps file columns to database parameters.

### Docker (recommended for production)

Place your data files and a config YAML in accessible directories, then run:

```bash
docker compose run --rm \
  -v /path/to/your/data:/data \
  -v /path/to/your/config.yaml:/config.yaml \
  importer --config /config.yaml
```

### Minimal YAML config example (tagless, scalar)

```yaml
api_config:
  api_url: http://api:8000/api/v1   # use localhost:8000 when running outside Docker

scalar_file_configs:
  - name: my_sensor
    mode: tagless
    das_name: My-DAS
    file_structure:
      extension: .csv
      separator: ","
      encoding: utf-8
      header_row_idx: 0
      dt_column: Timestamp
      dt_format: "%Y-%m-%d %H:%M:%S"
      timezone: UTC
    variables:
      - name: ph_reading
        parameter_name: pH          # must already exist in dbo.Parameter
        source_unit_name: "-"       # must already exist in dbo.Unit
        destination_unit_name: "-"
        directory_path: /data
        equipment_name: my-sensor-001   # must already exist in dbo.Equipment
        value_column: pH_value
```

The importer resolves the `Parameter` and `Unit` from the database by name — these must exist before running. The `DataAcquisitionSystem`, `SignalPort`, and `Channel` rows are created automatically on first import.

For vector (spectral) data or image ingest, see the example configs in `importer/configs/` and the [Ingestion Routing](architecture/ingestion_routing.md) architecture guide.

---

## 7. Troubleshooting

**Database not ready — API fails to start**

The `api` container waits for `db-init` to complete. If `db-init` is still running, the API will retry its health check. Check progress with:

```bash
docker compose logs db-init
```

If `db-init` exits with a non-zero code, the most common cause is a password that does not meet SQL Server complexity requirements. Fix `.env.docker`, then:

```bash
docker compose down -v
docker compose up --build -d
```

The `-v` flag removes the data volume so the database is re-created from scratch.

**Port 8000 or 8501 already in use**

Another process is using the port. Find and stop it, or change the host-side port in `docker-compose.yml`:

```yaml
ports:
  - "8080:8000"   # change 8080 to any free port
```

Then restart: `docker compose up -d`.

**Missing .env.docker file**

The API container requires `.env.docker`. If it is absent, the container exits immediately with:

```
Error: .env.docker not found
```

Run `cp .env.docker.example .env.docker` and restart.

**Importer fails with HTTP 422 on parameter or unit lookup**

The `parameter_name` or `source_unit_name` in your YAML config does not match any row in the database. Navigate to **Administration > Parameters** and **Administration > Units** in the web app to verify the exact names, or add the missing rows there.

**Web app shows "Cannot reach API"**

The Streamlit container connects to the API using the service name `http://api:8000/api/v1` (set automatically by Docker Compose). If you see this error, confirm the API container is running:

```bash
docker compose ps
docker compose logs api
```

---

## Next steps

- [Inserting Data](reference/inserting_data.md) — step-by-step walkthroughs for each value type via the API
- [Ingestion Routing](architecture/ingestion_routing.md) — how Channel resolution and auto-create work
- [Campaigns and Provenance](architecture/campaigns_and_provenance.md) — query patterns for filtering by campaign
- [Sensor Lifecycle](architecture/sensor_lifecycle.md) — calibration events, equipment history, sensor swaps
- [The Dictionary](contributing/dictionary.md) — how to add new parameters, units, and vocabulary terms
