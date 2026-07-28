import os
import time
from datetime import datetime, timezone
from pathlib import Path, PurePath

import yaml

from table_import import config
from table_import.api_client import ConfigValidationError, DateaubaseClient
from table_import.data_file import (
    DataCombiner,
    DataFile,
    SpectroFile,
    extract_image_timestamp,
    get_file_reader,
)
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

    filtered = df[mask].dropna(subset=["Value"])
    return [
        {
            "timestamp": unix_seconds_to_iso(row["Timestamp"]),
            "value": row["Value"] * conversion_factor
            if row["Value"] is not None
            else None,
            "quality_code": row.get("QualityCode") if hasattr(row, "get") else None,
        }
        for _, row in filtered.iterrows()
    ]


_INGEST_CHUNK_SIZE = 5_000
_VECTOR_CHUNK_SIZE = 100  # vector observations are large (221 bins each)


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
    signal_interface_name: str | None = None,
) -> None:
    """Send payload to the appropriate ingest endpoint in chunks and log the result."""
    if dry_run:
        print(f"[DRY RUN] {label}: would send {len(payload)} rows to API")
        return

    total_written = 0
    channel_id = None
    for i in range(0, max(len(payload), 1), _INGEST_CHUNK_SIZE):
        chunk = payload[i : i + _INGEST_CHUNK_SIZE]
        if not chunk:
            break
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
                values=chunk,
                signal_interface_name=signal_interface_name,
            )
        else:
            result = client.ingest_sensor_values_tagless(
                das_name=das_name,
                equipment_name=equipment_name,
                parameter_name=parameter_name,
                unit_name=unit_name,
                data_provenance_id=data_provenance_id,
                processing_degree_id=processing_degree_id,
                values=chunk,
                signal_interface_name=signal_interface_name,
            )
        total_written += result["rows_written"]
        channel_id = result["channel_id"]
    print(
        f"{label}: wrote {total_written} rows -> channel_id={channel_id}"
    )


# Skip files whose mtime predates the import floor by more than this margin.
# The margin absorbs clock skew / timezone differences between the file server
# and the DB watermark so a file that could still hold new rows is never skipped.
_STALE_FILE_MARGIN_S = 86400.0  # 1 day

# Optional wall-clock budget for a single import run. Set from the
# IMPORTER_MAX_SECONDS env var at the start of main(); when exceeded, the
# file-collection loops stop early and the run ingests whatever it has so far
# (the watermark advances, and the next run resumes). 0/unset = no limit.
_DEADLINE: float | None = None


def _past_deadline() -> bool:
    return _DEADLINE is not None and time.monotonic() > _DEADLINE


def _list_candidate_files(
    directory: str,
    extension: str,
    filename_contains: str | None,
    floor_ts: float,
) -> list[str]:
    """List matching files in ``directory``, skipping ones last modified clearly
    before ``floor_ts`` (the max of the DB watermark and configured
    min_timestamp).

    A file whose mtime predates the floor cannot contain rows at/after it — any
    newer data would have bumped the mtime — so skipping it avoids a needless
    full read over the (slow) SMB share. One os.scandir pass provides the mtime
    with no extra round-trips. Files that can't be stat'd are kept. Exact
    row-level filtering still happens downstream, so this only ever skips reads.
    """
    cutoff = floor_ts - _STALE_FILE_MARGIN_S if floor_ts > 0 else 0.0
    out: list[str] = []
    with os.scandir(directory) as it:
        for entry in it:
            name = entry.name
            if extension not in name:
                continue
            if filename_contains is not None and filename_contains not in name:
                continue
            if cutoff > 0:
                try:
                    if entry.stat().st_mtime < cutoff:
                        continue
                except OSError:
                    pass  # keep the file if its mtime can't be read
            out.append(entry.path)
    return out


def _get_file_values(
    variable: config.BaseVariable,
    file_structure,
    file_reader_class: type[DataFile],
    last_unix_ts: float,
    min_unix_ts: float | None = None,
) -> ValueTable:
    """Load all files for a variable and return deduplicated ValueTable."""
    floor_ts = max(last_unix_ts, min_unix_ts or 0.0)
    filepaths = _list_candidate_files(
        str(PurePath(variable.directory_path)),
        file_structure.extension,
        variable.filename_contains,
        floor_ts,
    )
    # Convert Unix float to naive UTC datetime for DataCombiner compatibility
    last_date = datetime.utcfromtimestamp(last_unix_ts) if last_unix_ts > 0 else None
    combiner = DataCombiner(last_date=last_date)
    for filepath in filepaths:
        if _past_deadline():
            print(
                f"[TIME BUDGET] stopping file scan for {variable.name!r} "
                f"after {len(combiner.files)} files (IMPORTER_MAX_SECONDS reached)"
            )
            break
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
    api_token = os.environ.get("API_SERVICE_TOKEN")

    # Optional wall-clock budget so a slow source (e.g. a large file share) can
    # never run past the scheduled-task time limit and leave a zombie task:
    # the file loops stop early, ingest what they have, and the next run resumes.
    global _DEADLINE
    _max_seconds = float(os.environ.get("IMPORTER_MAX_SECONDS", "0") or 0)
    _DEADLINE = (time.monotonic() + _max_seconds) if _max_seconds > 0 else None

    # Pre-flight: validate every (parameter_name, destination_unit_name) pair before
    # any data is ingested. Raises ConfigValidationError on first invalid pair.
    with DateaubaseClient(api_conf.api_url, token=api_token) as preflight_client:
        all_sources: list = (
            list(settings.file_configs)
            + list(settings.tsdb_configs)
            + list(settings.scada_sql_configs)
            + list(settings.vector_file_configs)
            + list(settings.image_folder_configs)
        )
        for src in all_sources:
            for variable in src.variables:
                preflight_client.validate_parameter_unit_pair(
                    parameter_name=variable.parameter_name,
                    unit_name=variable.destination_unit_name,
                )

    min_unix_ts: float | None = None
    if api_conf.min_timestamp:
        min_unix_ts = (
            datetime.fromisoformat(api_conf.min_timestamp)
            .replace(tzinfo=timezone.utc)
            .timestamp()
        )

    with DateaubaseClient(api_conf.api_url, token=api_token) as client:
        # ------------------------------------------------------------------
        # File-based sources
        # ------------------------------------------------------------------
        for file_cfg in settings.file_configs:
            file_structure = file_cfg.file_structure
            file_reader_class = get_file_reader(file_cfg.file_reader_type or file_cfg.name)
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
                        signal_interface_name=file_cfg.signal_interface_name,
                    )
                else:
                    channel_id, warnings = client.resolve_channel_tagless(
                        das_name=file_cfg.das_name,
                        equipment_name=variable.equipment_name,
                        parameter_name=variable.parameter_name,
                        unit_name=variable.destination_unit_name,
                        data_provenance_id=variable.data_provenance_id,
                        processing_degree_id=variable.processing_degree_id,
                        signal_interface_name=file_cfg.signal_interface_name,
                        wiring_valid_from=api_conf.min_timestamp,
                    )
                for w in warnings:
                    print(f"[WARNING] {label}: {w}")

                if dry_run:
                    print(f"[DRY RUN] {label}: channel_id={channel_id}, would load from {variable.directory_path!r}")
                    continue

                last_dt = client.get_last_timestamp(channel_id=channel_id)
                last_ts = last_dt.timestamp() if last_dt is not None else 0.0

                data = _get_file_values(
                    variable, file_structure, file_reader_class, last_ts, min_unix_ts
                )
                if data.empty:
                    print(f"No new data for {label}")
                    continue

                payload = build_api_payload(
                    data, last_ts, min_unix_ts, variable.conversion_factor
                )
                if not payload:
                    print(f"No new data for {label} after filtering")
                    continue

                ingest_via_api(
                    client,
                    mode=mode,
                    das_name=file_cfg.das_name,
                    tag=variable.tag if mode == "tagged" else None,
                    signal_port_type=variable.signal_port_type
                    if mode == "tagged"
                    else "value",
                    parent_tag=variable.parent_tag if mode == "tagged" else None,
                    equipment_name=variable.equipment_name
                    if mode == "tagless"
                    else None,
                    parameter_name=variable.parameter_name,
                    unit_name=variable.destination_unit_name,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                    payload=payload,
                    label=label,
                    dry_run=dry_run,
                    signal_interface_name=file_cfg.signal_interface_name,
                )

        # ------------------------------------------------------------------
        # TSDB binary sources
        # ------------------------------------------------------------------
        for tsdb_cfg in settings.tsdb_configs:
            file_reader_class = get_file_reader("tsdb")
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
                        signal_interface_name=tsdb_cfg.signal_interface_name,
                    )
                else:
                    channel_id, warnings = client.resolve_channel_tagless(
                        das_name=tsdb_cfg.das_name,
                        equipment_name=variable.equipment_name,
                        parameter_name=variable.parameter_name,
                        unit_name=variable.destination_unit_name,
                        data_provenance_id=variable.data_provenance_id,
                        processing_degree_id=variable.processing_degree_id,
                        signal_interface_name=tsdb_cfg.signal_interface_name,
                        wiring_valid_from=api_conf.min_timestamp,
                    )
                for w in warnings:
                    print(f"[WARNING] {label}: {w}")

                if dry_run:
                    print(f"[DRY RUN] {label}: channel_id={channel_id}, would load from {variable.directory_path!r}")
                    continue

                last_dt = client.get_last_timestamp(channel_id=channel_id)
                last_ts = last_dt.timestamp() if last_dt is not None else 0.0

                data = _get_file_values(
                    variable, tsdb_cfg.tsdb_structure, file_reader_class, last_ts, min_unix_ts
                )
                if data.empty:
                    print(f"No new data for {label}")
                    continue

                payload = build_api_payload(
                    data, last_ts, min_unix_ts, variable.conversion_factor
                )
                if not payload:
                    print(f"No new data for {label} after filtering")
                    continue

                ingest_via_api(
                    client,
                    mode=mode,
                    das_name=tsdb_cfg.das_name,
                    tag=variable.tag if mode == "tagged" else None,
                    signal_port_type=variable.signal_port_type
                    if mode == "tagged"
                    else "value",
                    parent_tag=variable.parent_tag if mode == "tagged" else None,
                    equipment_name=variable.equipment_name
                    if mode == "tagless"
                    else None,
                    parameter_name=variable.parameter_name,
                    unit_name=variable.destination_unit_name,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                    payload=payload,
                    label=label,
                    dry_run=dry_run,
                    signal_interface_name=tsdb_cfg.signal_interface_name,
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
                    signal_interface_name=scada_cfg.signal_interface_name,
                )
                for w in warnings:
                    print(f"[WARNING] {label}: {w}")

                if dry_run:
                    print(f"[DRY RUN] {label}: channel_id={channel_id}, would query SCADA SQL")
                    continue

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

                payload = build_api_payload(
                    data, last_ts, min_unix_ts, variable.conversion_factor
                )
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
                    signal_interface_name=scada_cfg.signal_interface_name,
                )

        # ------------------------------------------------------------------
        # Vector file sources
        # ------------------------------------------------------------------
        for vec_cfg in settings.vector_file_configs:
            _ingest_vector_source(client, vec_cfg, min_unix_ts, dry_run, api_conf.min_timestamp)

        # ------------------------------------------------------------------
        # Image folder sources
        # ------------------------------------------------------------------
        for img_cfg in settings.image_folder_configs:
            _ingest_image_source(client, img_cfg, min_unix_ts, dry_run, api_conf.min_timestamp)

        # ------------------------------------------------------------------
        # Matrix file sources (stub — not yet implemented)
        # ------------------------------------------------------------------
        for mat_cfg in settings.matrix_file_configs:
            raise NotImplementedError(
                f"Matrix file ingestion not yet implemented (config: {mat_cfg.name!r}). "
                "Add a sample file to importer/test_data/ and implement the reader first."
            )


def _ingest_vector_source(
    client: DateaubaseClient,
    vec_cfg: config.TaggedVectorFileConfig | config.TaglessVectorFileConfig,
    min_unix_ts: float | None,
    dry_run: bool,
    wiring_valid_from: str | None = None,
) -> None:
    """Process all variables in a tagged or tagless vector file config."""
    mode = vec_cfg.mode
    for variable in vec_cfg.variables:
        label = f"{vec_cfg.name}/{variable.name}"

        # 1. Find-or-create binning axis
        axis_id, created, axis_warnings = client.resolve_binning_axis(
            axis=variable.axis
        )
        if created:
            print(
                f"{label}: created binning axis {variable.axis.name!r} -> axis_id={axis_id}"
            )
        for w in axis_warnings:
            print(f"[WARNING] {label}: {w}")

        # 2. Resolve channel (value_kind_id=2 for Vector)
        if mode == "tagged":
            channel_id, ch_warnings = client.resolve_channel(
                das_name=vec_cfg.das_name,
                tag=variable.tag,
                signal_port_type=variable.signal_port_type,
                parameter_name=variable.parameter_name,
                unit_name=variable.destination_unit_name,
                data_provenance_id=variable.data_provenance_id,
                processing_degree_id=variable.processing_degree_id,
                value_type_id=2,
                signal_interface_name=vec_cfg.signal_interface_name,
            )
        else:
            channel_id, ch_warnings = client.resolve_channel_tagless(
                das_name=vec_cfg.das_name,
                equipment_name=variable.equipment_name,
                parameter_name=variable.parameter_name,
                unit_name=variable.destination_unit_name,
                data_provenance_id=variable.data_provenance_id,
                processing_degree_id=variable.processing_degree_id,
                value_type_id=2,
                signal_interface_name=vec_cfg.signal_interface_name,
                wiring_valid_from=wiring_valid_from,
            )
        for w in ch_warnings:
            print(f"[WARNING] {label}: {w}")

        if dry_run:
            print(f"[DRY RUN] {label}: channel_id={channel_id}, would load vector files from {variable.directory_path!r}")
            continue

        # 3. Watermark
        last_dt = client.get_last_timestamp(channel_id=channel_id)
        last_ts = last_dt.timestamp() if last_dt is not None else 0.0

        # 4. Collect observations from all matching files
        floor_ts = max(last_ts, min_unix_ts or 0.0)
        filepaths = _list_candidate_files(
            str(PurePath(variable.directory_path)),
            vec_cfg.file_structure.extension,
            getattr(variable, "filename_contains", None),
            floor_ts,
        )

        all_observations: list[dict] = []
        for fp in filepaths:
            if _past_deadline():
                print(
                    f"[TIME BUDGET] stopping vector scan for {variable.name!r} "
                    f"after {len(all_observations)} new observations "
                    "(IMPORTER_MAX_SECONDS reached)"
                )
                break
            sf = SpectroFile(fp, vec_cfg.file_structure)
            last_date = sf.get_last_date()
            if last_date is not None and last_date.timestamp() <= last_ts:
                continue  # file entirely before watermark
            obs = sf.observations(
                last_unix_ts=last_ts,
                min_unix_ts=min_unix_ts,
                bins=variable.axis.bins,
                status_map=vec_cfg.file_structure.status_map,
            )
            all_observations.extend(obs)

        if not all_observations:
            print(f"No new data for {label}")
            continue

        # Deduplicate by timestamp (keep first occurrence)
        seen: set[str] = set()
        deduped: list[dict] = []
        for obs in sorted(all_observations, key=lambda o: o["timestamp"]):
            if obs["timestamp"] not in seen:
                seen.add(obs["timestamp"])
                deduped.append(obs)

        if dry_run:
            print(f"[DRY RUN] {label}: would send {len(deduped)} observations to API")
            continue

        total_written = 0
        final_channel_id = None
        for i in range(0, max(len(deduped), 1), _VECTOR_CHUNK_SIZE):
            chunk = deduped[i : i + _VECTOR_CHUNK_SIZE]
            if not chunk:
                break
            if mode == "tagged":
                result = client.ingest_vector_observations(
                    das_name=vec_cfg.das_name,
                    tag=variable.tag,
                    signal_port_type=variable.signal_port_type,
                    parameter_name=variable.parameter_name,
                    unit_name=variable.destination_unit_name,
                    binning_axis_id=axis_id,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                    observations=chunk,
                    signal_interface_name=vec_cfg.signal_interface_name,
                )
            else:
                result = client.ingest_vector_observations_tagless(
                    das_name=vec_cfg.das_name,
                    equipment_name=variable.equipment_name,
                    parameter_name=variable.parameter_name,
                    unit_name=variable.destination_unit_name,
                    binning_axis_id=axis_id,
                    data_provenance_id=variable.data_provenance_id,
                    processing_degree_id=variable.processing_degree_id,
                    observations=chunk,
                    signal_interface_name=vec_cfg.signal_interface_name,
                )
            total_written += result["rows_written"]
            final_channel_id = result["channel_id"]
        print(
            f"{label}: wrote {total_written} observations -> channel_id={final_channel_id}"
        )


def _ingest_image_source(
    client: DateaubaseClient,
    img_cfg: config.TaggedImageFolderConfig | config.TaglessImageFolderConfig,
    min_unix_ts: float | None,
    dry_run: bool,
    wiring_valid_from: str | None = None,
) -> None:
    """Process all variables in a tagged or tagless image folder config."""
    mode = img_cfg.mode

    for variable in img_cfg.variables:
        label = f"{img_cfg.name}/{variable.name}"

        # 1. Resolve channel (value_type_id=4 for Image channels)
        if mode == "tagged":
            channel_id, warnings = client.resolve_channel(
                das_name=img_cfg.das_name,
                tag=variable.tag,
                signal_port_type=variable.signal_port_type,
                parent_tag=variable.parent_tag,
                parameter_name=variable.parameter_name,
                unit_name=variable.destination_unit_name,
                data_provenance_id=variable.data_provenance_id,
                processing_degree_id=variable.processing_degree_id,
                value_type_id=4,
                signal_interface_name=img_cfg.signal_interface_name,
            )
        else:
            channel_id, warnings = client.resolve_channel_tagless(
                das_name=img_cfg.das_name,
                equipment_name=variable.equipment_name,
                parameter_name=variable.parameter_name,
                unit_name=variable.destination_unit_name,
                data_provenance_id=variable.data_provenance_id,
                processing_degree_id=variable.processing_degree_id,
                value_type_id=4,
                signal_interface_name=img_cfg.signal_interface_name,
                wiring_valid_from=wiring_valid_from,
            )
        for w in warnings:
            print(f"[WARNING] {label}: {w}")

        if dry_run:
            print(f"[DRY RUN] {label}: channel_id={channel_id}, would scan image folder {variable.directory_path!r}")
            continue

        # 2. Watermark
        last_dt = client.get_last_timestamp(channel_id=channel_id)
        last_ts = last_dt.timestamp() if last_dt is not None else 0.0

        # 3. List image files
        structure = img_cfg.folder_structure
        extensions = tuple(ext.lower() for ext in structure.extensions)
        filepaths = [
            os.path.join(variable.directory_path, fname)
            for fname in os.listdir(variable.directory_path)
            if os.path.splitext(fname)[1].lower() in extensions
        ]

        sent = 0
        for fp in sorted(filepaths):
            ts_utc = extract_image_timestamp(fp, structure)
            if ts_utc is None:
                print(
                    f"[WARNING] {label}: could not extract timestamp from {fp} — skipped"
                )
                continue

            unix_ts = ts_utc.timestamp()
            if unix_ts <= last_ts:
                continue
            if min_unix_ts is not None and unix_ts < min_unix_ts:
                continue

            if dry_run:
                print(f"[DRY RUN] {label}: would ingest {fp} at {ts_utc.isoformat()}")
                sent += 1
                continue

            result = client.ingest_image(
                das_name=img_cfg.das_name,
                tag=variable.tag if mode == "tagged" else None,
                signal_port_type=variable.signal_port_type,
                equipment_name=variable.equipment_name if mode == "tagless" else None,
                parameter_name=variable.parameter_name,
                unit_name=variable.destination_unit_name,
                timestamp=ts_utc.isoformat(),
                data_provenance_id=variable.data_provenance_id,
                processing_degree_id=variable.processing_degree_id,
                image_path=fp,
                signal_interface_name=img_cfg.signal_interface_name,
            )
            print(
                f"{label}: ingested {os.path.basename(fp)} -> "
                f"channel_id={result['channel_id']} value_image_id={result['value_image_id']}"
            )
            sent += 1

        if sent == 0 and not dry_run:
            print(f"No new images for {label}")


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
    with open(path_obj, encoding="utf-8") as f:
        file_config = yaml.safe_load(f)
    return config.Config(**file_config)


def read_configs_from_dir(dir_path: str) -> config.Config:
    """Merge all *.yaml files in dir_path into a single Config.

    api_config is taken from the first file that defines it.
    All list fields (file_configs, tsdb_configs, etc.) are concatenated.
    """
    path_obj = Path(dir_path)
    if not path_obj.is_dir():
        raise ValueError(f"Could not find config directory at {dir_path}")

    yaml_files = sorted(path_obj.glob("*.yaml"))
    if not yaml_files:
        raise ValueError(f"No *.yaml files found in {dir_path}")

    api_config_raw: dict | None = None
    merged: dict[str, list] = {
        "file_configs": [],
        "tsdb_configs": [],
        "scada_sql_configs": [],
        "vector_file_configs": [],
        "image_folder_configs": [],
        "matrix_file_configs": [],
    }

    for yaml_file in yaml_files:
        with open(yaml_file, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if api_config_raw is None and "api_config" in data:
            api_config_raw = data["api_config"]
        for key in merged:
            merged[key].extend(data.get(key, []))

    if api_config_raw is None:
        raise ValueError(f"No api_config found in any *.yaml file in {dir_path}")

    return config.Config(api_config=api_config_raw, **merged)
