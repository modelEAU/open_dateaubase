import os
from datetime import datetime, timezone
from pathlib import Path, PurePath

import yaml

from table_import import config
from table_import.api_client import DateaubaseClient
from table_import.data_file import DataCombiner, DataFile, get_file_reader
from table_import.scada_sql_source import SqlServerSource, _build_scada_engine
from table_import.tables import ValueTable


def unix_seconds_to_iso(unix_ts: float) -> str:
    """Convert a Unix-seconds float to an ISO 8601 UTC string."""
    return datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()


def build_api_payload(
    df: ValueTable,
    last_unix_ts: float,
    min_unix_ts: float | None,
    conversion_factor: float,
) -> list[dict]:
    """Filter df and convert rows to API value dicts.

    Keeps rows where Timestamp > last_unix_ts and (if min_unix_ts is set)
    Timestamp >= min_unix_ts. Applies conversion_factor to Value.
    """
    mask = df["Timestamp"] > last_unix_ts
    if min_unix_ts is not None:
        mask &= df["Timestamp"] >= min_unix_ts

    filtered = df[mask]
    return [
        {
            "timestamp": unix_seconds_to_iso(row["Timestamp"]),
            "value": row["Value"] * conversion_factor if row["Value"] is not None else None,
        }
        for _, row in filtered.iterrows()
    ]


def ingest_via_api(
    client: DateaubaseClient,
    *,
    equipment_id: int,
    parameter_id: int,
    unit_id: int,
    data_provenance_id: int,
    processing_degree_id: int,
    payload: list[dict],
    label: str,
    dry_run: bool = False,
) -> None:
    """Send payload to POST /api/v1/ingest/sensor and log the result."""
    if dry_run:
        print(f"[DRY RUN] {label}: would send {len(payload)} rows to API")
        return
    result = client.ingest_sensor_values(
        equipment_id=equipment_id,
        parameter_id=parameter_id,
        unit_id=unit_id,
        data_provenance_id=data_provenance_id,
        processing_degree_id=processing_degree_id,
        values=payload,
    )
    print(f"{label}: wrote {result['rows_written']} rows → channel_id={result['channel_id']}")


def _resolve_variable_ids(
    client: DateaubaseClient,
    variable: config.Variable | config.TsdbVariable | config.ScadaVariable,
) -> tuple[int, int, int]:
    """Resolve names to (equipment_id, parameter_id, channel_unit_id)."""
    equipment_id = client.resolve_equipment_id(variable.equipment_name)
    parameter_id = client.resolve_parameter_id(variable.parameter_name)
    unit_id = client.resolve_unit_id(variable.channel_unit_name)
    return equipment_id, parameter_id, unit_id


def _last_unix_ts(
    client: DateaubaseClient,
    equipment_id: int,
    parameter_id: int,
    data_provenance_id: int,
    processing_degree_id: int,
) -> float:
    """Return the last ingested timestamp as a Unix float (0.0 if none)."""
    last_dt = client.get_last_timestamp(
        equipment_id=equipment_id,
        parameter_id=parameter_id,
        data_provenance_id=data_provenance_id,
        processing_degree_id=processing_degree_id,
    )
    return last_dt.timestamp() if last_dt is not None else 0.0


def _get_file_values(
    variable: config.Variable | config.TsdbVariable,
    file_structure: config.FileStructure | config.TsdbFileStructure,
    file_reader_class: type[DataFile],
    last_unix_ts: float,
) -> ValueTable:
    """Load all files for a variable and return deduplicated ValueTable."""
    path = PurePath(variable.directory_path)
    filepaths = [
        str(path.joinpath(x))
        for x in os.listdir(str(path))
        if file_structure.extension in x
    ]
    # Convert Unix float to naive UTC datetime for DataCombiner compatibility
    last_date = (
        datetime.utcfromtimestamp(last_unix_ts) if last_unix_ts > 0 else None
    )
    combiner = DataCombiner(last_id=0, last_date=last_date)
    for filepath in filepaths:
        file_obj = file_reader_class(
            filepath=filepath,
            file_structure=file_structure,
            variable=variable,
        )
        combiner.add_file(file_obj)
    return combiner.values


def main(settings: config.Config, dry_run: bool = False) -> None:
    """Import sensor data from all configured sources via the REST API.

    Steps:
    1. Connect to the API and pre-resolve all name→ID mappings (fail-fast).
    2. For each variable, determine the last ingested timestamp (watermark).
    3. Read new data from source files / SCADA SQL.
    4. Apply conversion_factor and global min_timestamp filter.
    5. POST to /api/v1/ingest/sensor (or log in dry-run mode).
    """
    print(datetime.now())
    api_conf = settings.api_config

    min_unix_ts: float | None = None
    if api_conf.min_timestamp:
        min_unix_ts = datetime.fromisoformat(api_conf.min_timestamp).replace(
            tzinfo=timezone.utc
        ).timestamp()

    with DateaubaseClient(api_conf.api_url) as client:
        # ------------------------------------------------------------------
        # File-based sources
        # ------------------------------------------------------------------
        for file_config in settings.file_configs:
            file_structure = file_config.file_structure
            file_reader_class = get_file_reader(file_config.name)

            for variable in file_config.variables:
                equipment_id, parameter_id, unit_id = _resolve_variable_ids(client, variable)
                last_ts = _last_unix_ts(
                    client, equipment_id, parameter_id,
                    variable.data_provenance_id, variable.processing_degree_id,
                )
                data = _get_file_values(variable, file_structure, file_reader_class, last_ts)

                if data.empty:
                    print(f"No new data for {file_config.name}/{variable.name}")
                    continue

                payload = build_api_payload(data, last_ts, min_unix_ts, variable.conversion_factor)
                if not payload:
                    print(f"No new data for {file_config.name}/{variable.name} after filtering")
                    continue

                ingest_via_api(
                    client,
                    equipment_id=equipment_id,
                    parameter_id=parameter_id,
                    unit_id=unit_id,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                    payload=payload,
                    label=f"{file_config.name}/{variable.name}",
                    dry_run=dry_run,
                )

        # ------------------------------------------------------------------
        # TSDB binary sources
        # ------------------------------------------------------------------
        for tsdb_config in settings.tsdb_configs:
            file_reader_class = get_file_reader(tsdb_config.name)

            for variable in tsdb_config.variables:
                equipment_id, parameter_id, unit_id = _resolve_variable_ids(client, variable)
                last_ts = _last_unix_ts(
                    client, equipment_id, parameter_id,
                    variable.data_provenance_id, variable.processing_degree_id,
                )
                data = _get_file_values(variable, tsdb_config.tsdb_structure, file_reader_class, last_ts)

                if data.empty:
                    print(f"No new data for {tsdb_config.name}/{variable.name}")
                    continue

                payload = build_api_payload(data, last_ts, min_unix_ts, variable.conversion_factor)
                if not payload:
                    print(f"No new data for {tsdb_config.name}/{variable.name} after filtering")
                    continue

                ingest_via_api(
                    client,
                    equipment_id=equipment_id,
                    parameter_id=parameter_id,
                    unit_id=unit_id,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                    payload=payload,
                    label=f"{tsdb_config.name}/{variable.name}",
                    dry_run=dry_run,
                )

        # ------------------------------------------------------------------
        # SCADA SQL sources
        # ------------------------------------------------------------------
        for scada_config in settings.scada_sql_configs:
            scada_engine = _build_scada_engine(scada_config.scada_structure)

            for variable in scada_config.variables:
                equipment_id, parameter_id, unit_id = _resolve_variable_ids(client, variable)
                last_ts = _last_unix_ts(
                    client, equipment_id, parameter_id,
                    variable.data_provenance_id, variable.processing_degree_id,
                )
                source = SqlServerSource(
                    structure=scada_config.scada_structure,
                    variable=variable,
                    engine=scada_engine,
                )
                data = source.get_values_since(last_ts)

                if data.empty:
                    print(f"No new data for {scada_config.name}/{variable.name}")
                    continue

                payload = build_api_payload(data, last_ts, min_unix_ts, variable.conversion_factor)
                if not payload:
                    print(f"No new data for {scada_config.name}/{variable.name} after filtering")
                    continue

                ingest_via_api(
                    client,
                    equipment_id=equipment_id,
                    parameter_id=parameter_id,
                    unit_id=unit_id,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                    payload=payload,
                    label=f"{scada_config.name}/{variable.name}",
                    dry_run=dry_run,
                )


def str_to_bool(s: str) -> bool:
    """Helper function to parse boolean flags received from the command line."""
    if s.lower() in {"y", "yes", "true"}:
        return True
    if s.lower() in {"n", "no", "false"}:
        return False
    raise ValueError(f"Argument value {s} is neither 'true' or 'false'")


def read_config_from_file(path: str) -> config.Config:
    """Load configuration settings from a YAML file into a Config object."""
    path_obj = Path(path)
    if not path_obj.is_file():
        raise ValueError(f"Could not find config file at {path}")
    with open(path_obj) as f:
        file_config = yaml.safe_load(f)
    return config.Config(**file_config)
