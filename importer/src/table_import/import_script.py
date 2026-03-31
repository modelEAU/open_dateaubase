import os
from datetime import datetime, timezone
from pathlib import Path, PurePath

import yaml

from table_import import config
from table_import.api_client import DateaubaseClient
from table_import.data_file import DataCombiner, DataFile, get_file_reader
from table_import.pilEAUte_scada_source import PilEAUteSCADASource, _build_scada_engine
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
    mode: str,
    das_name: str,
    tag: str | None,
    signal_port_type: str,
    parent_tag: str | None,
    equipment_name: str | None,
    parameter_name: str,
    unit_name: str,
    data_provenance_id: int,
    processing_degree_id: int,
    payload: list[dict],
    label: str,
    dry_run: bool = False,
) -> None:
    """Send payload to the appropriate ingest endpoint and log the result."""
    if dry_run:
        print(f"[DRY RUN] {label}: would send {len(payload)} rows to API")
        return
    if mode == "tagged":
        result = client.ingest_sensor_values(
            das_name=das_name,
            tag=tag,
            signal_port_type=signal_port_type,
            parent_tag=parent_tag,
            parameter_name=parameter_name,
            unit_name=unit_name,
            data_provenance_id=data_provenance_id,
            processing_degree_id=processing_degree_id,
            values=payload,
        )
    else:
        result = client.ingest_sensor_values_tagless(
            das_name=das_name,
            equipment_name=equipment_name,
            parameter_name=parameter_name,
            unit_name=unit_name,
            data_provenance_id=data_provenance_id,
            processing_degree_id=processing_degree_id,
            values=payload,
        )
    print(f"{label}: wrote {result['rows_written']} rows → channel_id={result['channel_id']}")


def _get_file_values(
    variable: config.BaseVariable,
    file_structure,
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
    combiner = DataCombiner(last_date=last_date)
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

    Per-variable flow:
    1. resolve_channel / resolve_channel_tagless  → channel_id (+ log warnings)
    2. get_last_timestamp(channel_id=...)         → watermark datetime
    3. load data from source (files / TSDB / SCADA SQL)
    4. filter by watermark + min_timestamp floor; apply conversion_factor
    5. ingest_sensor_values / ingest_sensor_values_tagless
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
        for file_cfg in settings.file_configs:
            file_structure = file_cfg.file_structure
            file_reader_class = get_file_reader(file_cfg.name)
            mode = file_cfg.mode

            for variable in file_cfg.variables:
                label = f"{file_cfg.name}/{variable.name}"

                if mode == "tagged":
                    channel_id, warnings = client.resolve_channel(
                        das_name=file_cfg.das_name,
                        tag=variable.tag,
                        signal_port_type=variable.signal_port_type,
                        parent_tag=variable.parent_tag,
                        parameter_name=variable.parameter_name,
                        unit_name=variable.destination_unit_name,
                        data_provenance_id=variable.data_provenance_id,
                        processing_degree_id=variable.processing_degree_id,
                    )
                else:
                    channel_id, warnings = client.resolve_channel_tagless(
                        das_name=file_cfg.das_name,
                        equipment_name=variable.equipment_name,
                        parameter_name=variable.parameter_name,
                        unit_name=variable.destination_unit_name,
                        data_provenance_id=variable.data_provenance_id,
                        processing_degree_id=variable.processing_degree_id,
                    )
                for w in warnings:
                    print(f"[WARNING] {label}: {w}")

                last_dt = client.get_last_timestamp(channel_id=channel_id)
                last_ts = last_dt.timestamp() if last_dt is not None else 0.0

                data = _get_file_values(variable, file_structure, file_reader_class, last_ts)
                if data.empty:
                    print(f"No new data for {label}")
                    continue

                payload = build_api_payload(data, last_ts, min_unix_ts, variable.conversion_factor)
                if not payload:
                    print(f"No new data for {label} after filtering")
                    continue

                ingest_via_api(
                    client,
                    mode=mode,
                    das_name=file_cfg.das_name,
                    tag=variable.tag if mode == "tagged" else None,
                    signal_port_type=variable.signal_port_type if mode == "tagged" else "value",
                    parent_tag=variable.parent_tag if mode == "tagged" else None,
                    equipment_name=variable.equipment_name if mode == "tagless" else None,
                    parameter_name=variable.parameter_name,
                    unit_name=variable.destination_unit_name,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                    payload=payload,
                    label=label,
                    dry_run=dry_run,
                )

        # ------------------------------------------------------------------
        # TSDB binary sources
        # ------------------------------------------------------------------
        for tsdb_cfg in settings.tsdb_configs:
            file_reader_class = get_file_reader(tsdb_cfg.name)
            mode = tsdb_cfg.mode

            for variable in tsdb_cfg.variables:
                label = f"{tsdb_cfg.name}/{variable.name}"

                if mode == "tagged":
                    channel_id, warnings = client.resolve_channel(
                        das_name=tsdb_cfg.das_name,
                        tag=variable.tag,
                        signal_port_type=variable.signal_port_type,
                        parent_tag=variable.parent_tag,
                        parameter_name=variable.parameter_name,
                        unit_name=variable.destination_unit_name,
                        data_provenance_id=variable.data_provenance_id,
                        processing_degree_id=variable.processing_degree_id,
                    )
                else:
                    channel_id, warnings = client.resolve_channel_tagless(
                        das_name=tsdb_cfg.das_name,
                        equipment_name=variable.equipment_name,
                        parameter_name=variable.parameter_name,
                        unit_name=variable.destination_unit_name,
                        data_provenance_id=variable.data_provenance_id,
                        processing_degree_id=variable.processing_degree_id,
                    )
                for w in warnings:
                    print(f"[WARNING] {label}: {w}")

                last_dt = client.get_last_timestamp(channel_id=channel_id)
                last_ts = last_dt.timestamp() if last_dt is not None else 0.0

                data = _get_file_values(variable, tsdb_cfg.tsdb_structure, file_reader_class, last_ts)
                if data.empty:
                    print(f"No new data for {label}")
                    continue

                payload = build_api_payload(data, last_ts, min_unix_ts, variable.conversion_factor)
                if not payload:
                    print(f"No new data for {label} after filtering")
                    continue

                ingest_via_api(
                    client,
                    mode=mode,
                    das_name=tsdb_cfg.das_name,
                    tag=variable.tag if mode == "tagged" else None,
                    signal_port_type=variable.signal_port_type if mode == "tagged" else "value",
                    parent_tag=variable.parent_tag if mode == "tagged" else None,
                    equipment_name=variable.equipment_name if mode == "tagless" else None,
                    parameter_name=variable.parameter_name,
                    unit_name=variable.destination_unit_name,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                    payload=payload,
                    label=label,
                    dry_run=dry_run,
                )

        # ------------------------------------------------------------------
        # SCADA SQL sources (always tagged)
        # ------------------------------------------------------------------
        for scada_cfg in settings.scada_sql_configs:
            scada_engine = _build_scada_engine(scada_cfg.scada_structure)

            for variable in scada_cfg.variables:
                label = f"{scada_cfg.name}/{variable.name}"

                channel_id, warnings = client.resolve_channel(
                    das_name=scada_cfg.das_name,
                    tag=variable.tag,
                    signal_port_type=variable.signal_port_type,
                    parent_tag=variable.parent_tag,
                    parameter_name=variable.parameter_name,
                    unit_name=variable.destination_unit_name,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                )
                for w in warnings:
                    print(f"[WARNING] {label}: {w}")

                last_dt = client.get_last_timestamp(channel_id=channel_id)
                last_ts = last_dt.timestamp() if last_dt is not None else 0.0

                source = PilEAUteSCADASource(
                    structure=scada_cfg.scada_structure,
                    variable=variable,
                    engine=scada_engine,
                )
                data = source.get_values_since(last_ts)

                if data.empty:
                    print(f"No new data for {label}")
                    continue

                payload = build_api_payload(data, last_ts, min_unix_ts, variable.conversion_factor)
                if not payload:
                    print(f"No new data for {label} after filtering")
                    continue

                ingest_via_api(
                    client,
                    mode="tagged",
                    das_name=scada_cfg.das_name,
                    tag=variable.tag,
                    signal_port_type=variable.signal_port_type,
                    parent_tag=variable.parent_tag,
                    equipment_name=None,
                    parameter_name=variable.parameter_name,
                    unit_name=variable.destination_unit_name,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                    payload=payload,
                    label=label,
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
