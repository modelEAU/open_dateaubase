# Table Import

A utility that imports sensor, vector, and image data into the open_datEAUbase via its REST API.

## Installation

```bash
# from the importer/ directory
uv sync
```

## Usage

The entry point exposes two subcommands.

### import — ingest sensor data from a YAML config

```bash
uv run table-import import --config /path/to/config.yaml
uv run table-import import --config /path/to/config.yaml --dry-run
uv run table-import import --config /path/to/config.yaml --min-timestamp 2024-01-01T00:00:00
```

`--dry-run` resolves each channel via the API (auto-creating DAS and SignalInterface if absent)
but skips file loading and all write calls.  Use it to validate a new config against a running
database without ingesting any data.

### l5x — load a Logix5000 L5X export

```bash
uv run table-import l5x FILE.L5X --signal-interface <name> [--das-name <name>] [--dry-run]
```

Parses an Allen-Bradley L5X archive, creates the SignalInterface + ports + channels in the
database, and opens ChannelPortHistory rows.  `--dry-run` prints the planned creates without
writing anything.

Example:

```bash
uv run table-import l5x modelEAU_Hedi_Latest260323.L5X \
    --signal-interface hedi_plc \
    --dry-run
```

## YAML configuration

### Root structure

```yaml
api_config:
  api_url: http://localhost:8000/api/v1
  min_timestamp: "2024-01-01T00:00:00"   # optional global cutoff

file_configs: [...]            # tagged or tagless CSV/text files
tsdb_configs: [...]            # WTW TSDB binary files
scada_sql_configs: [...]       # PilEAUte SCADA SQLite/SQL Server
vector_file_configs: [...]     # spectrophotometry / distribution files
image_folder_configs: [...]    # inline camera image folders
```

### Signal Interface field

Every source-level config (under `file_configs`, `tsdb_configs`, etc.) accepts an optional
`signal_interface_name` field at its root, alongside `das_name`:

```yaml
file_configs:
- name: my_sensor
  mode: tagged
  das_name: my_das           # DataAcquisitionSystem — the software/hardware that logs data
  signal_interface_name: my_si  # SignalInterface — the physical instrument bus or port
  ...
```

**When to set it:**

- Each config file typically describes one signal interface (one probe bus, one PLC, one
  SCADA station).  Set `signal_interface_name` to uniquely identify that interface.
- If omitted, the server infers the SignalInterface from the DAS name and tag (legacy mode).

See [configs/examples/](configs/examples/) for three worked examples illustrating the three
common forcing cases.

### Per-variable fields (common)

| Field | Type | Description |
| --- | --- | --- |
| `name` | str | Unique label for this variable in logs |
| `parameter_name` | str | Must match a `Parameter` row in the database |
| `source_unit_name` | str | Unit label of the raw source data (documentation only) |
| `destination_unit_name` | str | Must match a `Unit` row in the database |
| `directory_path` | str | Path to the folder containing data files |
| `tag` | str | TagName used to resolve/create the Channel (tagged mode) |
| `equipment_name` | str | Equipment Identifier (tagless mode) |
| `signal_port_type` | str | `value` (default), `status`, `alarm`, or `uncertainty` |
| `conversion_factor` | float | Multiply raw values before ingest (default 1.0) |

## Example configs

Three examples are provided under [configs/examples/](configs/examples/):

| File | DAS | Signal Interface | Pattern |
| --- | --- | --- | --- |
| `monEAU_iqsensor.yaml` | `monEAU_box` | `iqsensor_net_bus` | IQSensor Net digital bus, one SI per bus |
| `sc1000_via_plc.yaml` | `hedi_plc` | `sc1000_ammonium` | Hach SC1000 read via PLC; SI = controller unit |
| `logix5000_direct.yaml` | `hedi_plc` | `hedi_plc` | PLC is the interface; DAS == SI name |

Validate any example against a running database:

```bash
uv run table-import import --config configs/examples/monEAU_iqsensor.yaml --dry-run
```
