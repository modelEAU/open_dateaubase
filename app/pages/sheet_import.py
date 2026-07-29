"""Spreadsheet-first import — see the sheet, point at the header and the data.

Upload a workbook, pick a sheet, click the row holding your column names and
the first row of real data. Everything between is skipped. The cleaned block
renders beside the raw sheet and its cells are editable. Each column is then
mapped — in the vocabulary of the user's own work — from a field catalogue
derived from the ingest payload schemas, keyed by column index so repeated
header names stay independent. A span of columns selected in the raw sheet
takes one bulk action; fields the sheet does not contain take typed constants;
each measurement group carries its own parameter, unit, laboratory and
location.
"""

from __future__ import annotations

import datetime as dt
import io
import sys
import zoneinfo
from pathlib import Path

_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import pandas as pd
import streamlit as st

from app import api_client as api
from app.components import schema_registry
from app.components.column_mapping import (
    BULK_IGNORE,
    BULK_SET_FIELD,
    BULK_VALUE_EACH,
    BULK_VALUE_SAME,
    IDENTITY_FIELDS,
    IGNORE,
    apply_bulk,
    empty_spec,
    groups_lacking,
    groups_of,
    mapping_frame,
    missing_required,
    source_for,
    spec_from_frame,
    validate,
    with_constant,
    with_group_constant,
    without_constant,
    without_group_constant,
)
from app.components.datetime_parse import (
    FORMAT_PRESETS,
    detect_format,
    dst_gaps,
    parse_values,
    to_utc,
)
from app.components.field_catalogue import GROUPS, catalogue
from app.components.measurement_builder import (
    BuildResult,
    MeasurementCandidate,
    build,
    sample_key,
)
from app.components.sheet_block import SheetBlock, extract_block, read_grids
from app.components.timezone_select import timezone_selector

_CUSTOM = "Custom…"
_CHOOSE = "— choose a format —"

_BULK_LABELS = {
    "Ignore all": BULK_IGNORE,
    "All Value — one group each": BULK_VALUE_EACH,
    "All Value — same group": BULK_VALUE_SAME,
    "Set field to…": BULK_SET_FIELD,
}


@st.cache_data(show_spinner="Reading the file…")
def _grids(payload: bytes, filename: str) -> dict[str, pd.DataFrame]:
    return read_grids(io.BytesIO(payload), filename)


@st.cache_data(show_spinner=False)
def _raw_view(grid: pd.DataFrame) -> pd.DataFrame:
    """The grid as plain text, so nothing is interpreted before the user says so."""
    return grid.fillna("").astype(str)


def _sheet_ui(sheet: str, grid: pd.DataFrame) -> None:
    header_key = f"sheet_header_row::{sheet}"
    data_key = f"sheet_data_row::{sheet}"
    raw_col, clean_col = st.columns(2)

    with raw_col:
        st.subheader("Raw sheet")
        st.caption(f"{len(grid)} rows × {len(grid.columns)} columns, nothing interpreted.")
        event = st.dataframe(
            _raw_view(grid),
            key=f"sheet_raw::{sheet}",
            on_select="rerun",
            selection_mode=["multi-row", "multi-column"],
            height=400,
        )
        picked = list((event or {}).get("selection", {}).get("rows", []))
        selected_columns = []
        for c in (event or {}).get("selection", {}).get("columns", []):
            try:
                selected_columns.append(int(c))
            except (TypeError, ValueError):
                pass  # selection reports column names; the raw view's are ints
        left, right = st.columns(2)
        if left.button(
            "☝️ This is my header row",
            key=f"sheet_pick_header::{sheet}",
            disabled=not picked,
            width="stretch",
        ):
            st.session_state[header_key] = picked[0]
            st.rerun()
        if right.button(
            "👇 This is my first data row",
            key=f"sheet_pick_data::{sheet}",
            disabled=not picked,
            width="stretch",
        ):
            st.session_state[data_key] = picked[0]
            st.rerun()

    with clean_col:
        st.subheader("Cleaned block")
        header_row = st.session_state.get(header_key)
        data_row = st.session_state.get(data_key)
        st.caption(
            f"Header row: {header_row if header_row is not None else '—'} · "
            f"first data row: {data_row if data_row is not None else '—'}"
        )
        if header_row is None or data_row is None:
            st.info(
                "Select a row on the left, then say whether it is the header row "
                "or the first data row."
            )
            return
        if data_row <= header_row:
            st.warning("The first data row must be below the header row.")
            return

        block = extract_block(grid, header_row, data_row)
        edited = st.data_editor(
            block.data.set_axis(block.labels(), axis=1),
            key=f"sheet_clean::{sheet}",
            height=400,
        )
        edited_indexed = edited.set_axis(list(block.columns), axis=1)
        st.session_state[f"sheet_block::{sheet}"] = edited_indexed
        native = sorted(block.datetime_columns)
        st.caption(
            f"{len(edited)} rows × {len(block.columns)} columns. "
            + (
                f"Columns {native} already hold real datetimes."
                if native
                else "No column holds native datetimes."
            )
        )
        _mapping_section(sheet, block, sorted(selected_columns))
        _datetime_section(sheet, block, edited_indexed)
        _submit_section(sheet, block)


def _mapping_section(sheet: str, block: SheetBlock, selected_columns: list[int]) -> None:
    """One row per column: what the column holds, keyed by column index."""
    st.divider()
    st.subheader("🧭 Map the columns")
    cat = catalogue()
    spec_key = f"sheet_mapping::{sheet}"
    gen_key = f"sheet_map_gen::{sheet}"
    spec = st.session_state.get(spec_key)
    if spec is None or tuple(m.column for m in spec.mappings) != block.columns:
        spec = empty_spec(block)  # first visit, or the block was re-pointed
        st.session_state[spec_key] = spec
        st.session_state[gen_key] = st.session_state.get(gen_key, 0) + 1
        for key in [k for k in st.session_state if k.startswith(f"sheet_gconst::{sheet}::")]:
            del st.session_state[key]

    _bulk_bar(sheet, block, cat, spec, selected_columns)

    edited = st.data_editor(
        mapping_frame(block, cat, spec),
        key=f"sheet_map::{sheet}::{st.session_state.get(gen_key, 0)}",
        disabled=["Header", "Banner"],
        column_config={
            "Header": st.column_config.TextColumn(
                "Header", help="The column's header, collapsed to one line."
            ),
            "Banner": st.column_config.TextColumn(
                "Banner",
                help="The grouping banners above this column, forward-filled "
                "from the rows above the header. Read-only context — this is "
                "how repeated headers are told apart.",
            ),
            "Maps to": st.column_config.SelectboxColumn(
                "Maps to",
                options=[IGNORE, *cat.option_labels()],
                help="What this column holds, in the vocabulary of your work. "
                "Every column starts ignored.",
                width="large",
            ),
            "Group": st.column_config.NumberColumn(
                "Group",
                min_value=0,
                step=1,
                help="Columns sharing a group compose one measurement — the "
                "value column plus its qualifiers. Only meaningful for "
                "measurement fields; blank keeps each in its own group.",
            ),
        },
        height=400,
    )
    spec = spec_from_frame(block, cat, edited, previous=spec)
    st.session_state[spec_key] = spec

    _constants_editor(sheet, cat, spec)
    _groups_panel(sheet, block, cat, spec)

    for error in validate(spec, block, cat):
        st.warning(error.message)
    started = bool(spec.mapped()) or any(
        c.field != "sample.replicate" for c in spec.constants
    )
    missing = missing_required(spec, cat)
    if started and missing:
        st.caption(
            "Still needed before this can import: "
            + ", ".join(_missing_label(spec, cat, f) for f in missing)
            + "."
        )
    elif started:
        st.caption("Every required field has a source.")
    else:
        st.caption(
            "Every column is ignored — pick what each column holds above, or "
            "select a span of columns in the raw sheet and apply one action to "
            "all of them. Columns you leave ignored are simply not imported."
        )
    _catalogue_browser(cat)


def _missing_label(spec, cat, field) -> str:
    """A missing field's plain-language label, naming uncovered groups when partial."""
    if field.scope == "measurement":
        total = groups_of(spec, cat)
        lacking = groups_lacking(spec, cat, field.key)
        if total and 0 < len(lacking) < len(total):
            names = " and ".join(f"group {g}" for g in lacking)
            return f"{field.label} (missing in {names})"
    return field.label


def _bulk_bar(sheet: str, block: SheetBlock, cat, spec, selected_columns: list[int]) -> None:
    """One action applied to every column selected in the raw sheet."""
    n = len(selected_columns)
    if n:
        shown = ", ".join(str(c) for c in selected_columns[:8])
        st.caption(
            f"{n} column(s) selected in the raw sheet ({shown}"
            + ("…" if n > 8 else "")
            + ") — one action applies to all of them."
        )
    else:
        st.caption(
            "Select columns in the raw sheet above (drag across their headers), "
            "then apply one action to all of them here."
        )
    left, mid, right = st.columns([2, 3, 2])
    action_label = left.selectbox(
        "Bulk action",
        options=list(_BULK_LABELS),
        key=f"sheet_bulk_action::{sheet}",
        help="'All Value — one group each' makes every selected column its own "
        "measurement. 'All Value — same group' composes one measurement out of "
        "the selection — set the qualifier columns to their real fields next.",
    )
    field_key = None
    if _BULK_LABELS[action_label] == BULK_SET_FIELD:
        options = cat.option_labels()
        picked = mid.selectbox(
            "Field to set",
            options=list(options),
            key=f"sheet_bulk_field::{sheet}",
        )
        field_key = options[picked]
    if right.button(
        f"Apply to {n} column(s)",
        key=f"sheet_bulk_apply::{sheet}",
        disabled=not n,
        width="stretch",
    ):
        st.session_state[f"sheet_mapping::{sheet}"] = apply_bulk(
            spec, block, cat, selected_columns, _BULK_LABELS[action_label], field=field_key
        )
        gen_key = f"sheet_map_gen::{sheet}"
        st.session_state[gen_key] = st.session_state.get(gen_key, 0) + 1
        st.rerun()


def _constant_input(sheet: str, field) -> object | None:
    """The typed input for one field's constant; None when nothing was entered.

    A foreign-key field takes the *name* as the database knows it — names are
    resolved at submit, loudly, exactly like the values in a mapped column.
    """
    key = f"sheet_const_value::{sheet}::{field.key}"
    if field.fk_table:
        text = st.text_input(
            f"{field.label} — name in {field.fk_table}",
            key=key,
            help="The exact name as the database knows it (e.g. Field, VdQ). "
            "Unmatched names fail loudly at submit and name themselves.",
        )
        return text.strip() or None
    if field.value_type == "integer":
        return int(st.number_input(field.label, step=1, key=key, help=field.help or None))
    if field.value_type == "number":
        return float(st.number_input(field.label, step=0.1, key=key, help=field.help or None))
    if field.value_type == "datetime":
        left, right = st.columns(2)
        day = left.date_input(f"{field.label} — date", key=f"{key}::date")
        moment = right.time_input(f"{field.label} — time", key=f"{key}::time")
        return dt.datetime.combine(day, moment)
    text = st.text_input(field.label, key=key, help=field.help or None)
    return text.strip() or None


def _constants_editor(sheet: str, cat, spec) -> None:
    """Constants: a value the sheet does not contain, applied to every row."""
    with st.expander("🔧 Constants — values your sheet does not contain", expanded=True):
        for c in spec.constants:
            try:
                field = cat.by_key(c.field)
                label, scope, hint = field.label, field.scope, field.help
            except KeyError:
                label, scope, hint = c.field, "?", ""
            name_col, value_col, scope_col, del_col = st.columns([3, 3, 2, 1])
            name_col.markdown(f"**{label}**", help=hint or None)
            value_col.markdown(str(c.value))
            scope_col.caption(f"{scope} scope")
            if del_col.button("✕", key=f"sheet_const_del::{sheet}::{c.field}"):
                st.session_state[f"sheet_mapping::{sheet}"] = without_constant(spec, c.field)
                st.rerun()
        st.caption(
            "A constant gives one field the same value everywhere — sample kind "
            "'Field', a campaign, the field replicate (already set to 1)."
        )
        field_col, value_col, add_col = st.columns([3, 3, 1])
        options = cat.option_labels()
        picked = field_col.selectbox(
            "Field", options=list(options), key=f"sheet_const_field::{sheet}"
        )
        key = options[picked]
        with value_col:
            value = _constant_input(sheet, cat.by_key(key))
        if add_col.button("Set", key=f"sheet_const_add::{sheet}", width="stretch"):
            if value is not None:
                st.session_state[f"sheet_mapping::{sheet}"] = with_constant(spec, key, value)
                st.rerun()


def _sync_group_constant(spec_key: str, group: int, field: str, wkey: str) -> None:
    """Write a group-identity widget back into the spec (empty text clears it)."""
    spec = st.session_state.get(spec_key)
    if spec is None:
        return
    text = str(st.session_state.get(wkey, "")).strip()
    st.session_state[spec_key] = (
        with_group_constant(spec, group, field, text)
        if text
        else without_group_constant(spec, group, field)
    )


def _groups_panel(sheet: str, block: SheetBlock, cat, spec) -> None:
    """Each measurement group's own identity: parameter, unit, laboratory, location."""
    groups = groups_of(spec, cat)
    if not groups:
        return
    spec_key = f"sheet_mapping::{sheet}"
    labels = block.labels()
    columns = list(block.columns)
    with st.expander(f"🧪 Measurement groups ({len(groups)}) — each group's identity", expanded=True):
        st.caption(
            "Columns sharing a group compose one measurement. Parameter, unit, "
            "laboratory and location belong to the group, set independently of "
            "every other group — type the name as the database knows it. A "
            "location left empty inherits the sample's."
        )
        for group in groups:
            members = [
                m
                for m in spec.mapped()
                if (m.group if m.group is not None else m.column) == group
            ]
            names = ", ".join(
                f"'{labels[columns.index(m.column)]}' → {cat.by_key(m.field).label}"
                if m.field in {f.key for f in cat.fields}
                else f"'{labels[columns.index(m.column)]}'"
                for m in members
            )
            st.markdown(f"**Group {group}** — {names}")
            cells = st.columns(len(IDENTITY_FIELDS))
            for cell, key in zip(cells, IDENTITY_FIELDS):
                field = cat.by_key(key)
                source = source_for(spec, cat, group, key)
                global_value = next(
                    (c.value for c in spec.constants if c.field == key), None
                )
                group_value = next(
                    (c.value for c in spec.group_constants if (c.group, c.field) == (group, key)),
                    None,
                )
                if source and source[0] == "column" and group_value is None:
                    cell.caption(
                        f"**{field.label}** — from column "
                        f"'{labels[columns.index(source[1])]}'"
                    )
                    continue
                wkey = f"sheet_gconst::{sheet}::{group}::{key}"
                if wkey not in st.session_state:
                    st.session_state[wkey] = str(group_value) if group_value is not None else ""
                cell.text_input(
                    f"{field.label} (group {group})",
                    key=wkey,
                    placeholder=f"all groups: {global_value}" if global_value is not None else "—",
                    help=(
                        f"Set for group {group} only."
                        + (f" All groups take '{global_value}' unless a group overrides."
                           if global_value is not None else "")
                        + (f" {field.help}" if field.help else "")
                    ),
                    on_change=_sync_group_constant,
                    kwargs=dict(spec_key=spec_key, group=group, field=key, wkey=wkey),
                )


def _catalogue_browser(cat) -> None:
    """The full field vocabulary, grouped by activity — scope shown, never editable."""
    with st.expander("📖 Field catalogue — everything the import accepts"):
        st.caption(
            "Grouped by what you did, not by which table a field lives in. "
            "The scope — file, row or measurement — is a property of the "
            "field, never something you choose."
        )
        for group in GROUPS:
            st.markdown(f"**{group}**")
            for f in cat.in_group(group):
                line = (
                    f"- **{f.label}** — `{f.ref}` · {f.scope} scope"
                    + (" · required" if f.required else "")
                )
                if f.fk_table:
                    line += f" · picks from {f.fk_table}"
                st.markdown(line)
                if f.help:
                    st.caption(f.help)


def _show(moment) -> str:
    """A timestamp for the preview table, or a dash when there is none."""
    return "—" if pd.isna(moment) else moment.strftime("%Y-%m-%d %H:%M")


def _datetime_section(sheet: str, block: SheetBlock, data: pd.DataFrame) -> None:
    """Timezone, format and dual local/UTC preview for one date/time column."""
    st.divider()
    st.subheader("🕒 Dates & times")
    tz = timezone_selector(
        key=f"sheet_tz::{sheet}",
        label="File timezone",
        help="The timezone the file's times are written in. Parsed times preview "
        "below in both this zone and UTC, so a wrong pick is visible immediately.",
    )
    columns = list(block.columns)
    labels = block.labels()
    native_first = sorted(
        columns, key=lambda c: (c not in block.datetime_columns, columns.index(c))
    )
    column = st.selectbox(
        "Date/time column",
        options=native_first,
        format_func=lambda c: labels[columns.index(c)],
        key=f"sheet_dt_col::{sheet}",
        help="Which column holds each row's date/time. Columns already holding "
        "real dates sort first. Only one column previews at a time.",
    )
    values = data[column]

    if column in block.datetime_columns:
        st.info(
            "This column already holds real dates/times from the spreadsheet, so "
            "there is no format to choose — they are read as wall-clock times in "
            "the file timezone above."
        )
        parsed = parse_values(values, None)
    else:
        detection = detect_format(values)
        if detection.format is not None:
            st.success(f"Detected format: {detection.label}")
        else:
            st.warning("The date format cannot be told from the data — choose one yourself.")
        for line in detection.evidence:
            st.markdown(f"- {line}")
        options = [*FORMAT_PRESETS, _CUSTOM]
        if detection.label is not None:
            index = options.index(detection.label)
        else:
            options = [_CHOOSE, *options]
            index = 0
        choice = st.selectbox(
            "Date format",
            options=options,
            index=index,
            key=f"sheet_dt_fmt::{sheet}::{column}",
            help="How day, month and year are ordered in this column. Detection "
            "proposes a format when the evidence is clear and refuses when it "
            "is not — it never guesses.",
        )
        if choice == _CHOOSE:
            st.info("Choose a format to see the parsed times. Nothing is parsed until you do.")
            return
        if choice == _CUSTOM:
            fmt = st.text_input(
                "Custom format (strptime)",
                key=f"sheet_dt_custom::{sheet}::{column}",
                placeholder="%d/%m/%Y %H:%M",
                help="A Python strptime string, e.g. %d.%m.%Y %H:%M reads "
                "03.04.2026 14:30.",
            )
            if not fmt.strip():
                st.info("Enter a format to see the parsed times.")
                return
        else:
            fmt = FORMAT_PRESETS[choice]
        parsed = parse_values(values, fmt)

    if parsed.failures:
        st.warning(
            f"{len(parsed.failures)} value(s) would not parse — listed here, never "
            "dropped. Fix them in the cleaned table above or pick another format."
        )
        st.dataframe(
            pd.DataFrame(parsed.failures[:50], columns=["row", "value"]),
            hide_index=True,
        )
    utc = to_utc(parsed.wall_clock, tz)
    gaps = dst_gaps(parsed.wall_clock, utc)
    if gaps:
        st.warning(
            f"{len(gaps)} value(s) do not exist, or happen twice, in {tz.key} — "
            "the clocks changed. Correct them in the sheet, or choose a zone "
            "without daylight saving if the file is already in one."
        )
        st.dataframe(
            pd.DataFrame(gaps[:50], columns=["row", "local time"]),
            hide_index=True,
        )
    rows = list(values.index[:8])
    st.caption(
        f"First {len(rows)} of {len(values)} rows — wall-clock time in the file "
        "zone, and the UTC instant it becomes:"
    )
    st.dataframe(
        pd.DataFrame(
            {
                "row": rows,
                "value": [str(values.loc[row]) for row in rows],
                f"local ({tz.key})": [_show(parsed.wall_clock.loc[row]) for row in rows],
                "UTC": [_show(utc.loc[row]) for row in rows],
            }
        ),
        hide_index=True,
    )


def _column_formats(sheet: str, block: SheetBlock) -> dict[int, str | None]:
    """Every non-native column's chosen strptime format, per the dates section above."""
    formats: dict[int, str | None] = {}
    for column in block.columns:
        if column in block.datetime_columns:
            continue
        choice = st.session_state.get(f"sheet_dt_fmt::{sheet}::{column}")
        if choice in (None, _CHOOSE):
            continue
        if choice == _CUSTOM:
            custom = str(st.session_state.get(f"sheet_dt_custom::{sheet}::{column}", "")).strip()
            if custom:
                formats[column] = custom
            continue
        formats[column] = FORMAT_PRESETS[choice]
    return formats


def _api_lookup(table: str) -> list[dict]:
    """The candidate rows for a foreign-key table, via its auto-derived api_client function."""
    return getattr(api, schema_registry.fk_lookup_fn(table))()


def _serialize(values: dict) -> dict:
    """A payload dict ready for the wire — datetimes become ISO text."""
    return {k: (v.isoformat() if isinstance(v, dt.datetime) else v) for k, v in values.items()}


def _measurement_payload(m: MeasurementCandidate, sample_id: int) -> dict:
    return _serialize(
        {
            "parameter_id": m.parameter_id,
            "sampling_point_id": m.sampling_point_id,
            "unit_id": m.unit_id,
            "value_kind_id": 1,
            "series_name": m.series_name,
            "laboratory_id": m.laboratory_id,
            "sample_id": sample_id,
            "value": m.value,
            "replicate": m.replicate,
            "analyst_person_id": m.analyst_person_id,
            "procedure_id": m.procedure_id,
            "analysis_datetime": m.analysis_datetime,
            "quality_code_id": m.quality_code_id,
            "notes": m.notes,
        }
    )


def _submit_section(sheet: str, block: SheetBlock) -> None:
    st.divider()
    st.subheader("🚀 Submit")
    spec = st.session_state.get(f"sheet_mapping::{sheet}")
    tz_name = st.session_state.get(f"sheet_tz::{sheet}")
    if spec is None or tz_name is None:
        st.info("Map the columns and set a file timezone above before submitting.")
        return
    tz = zoneinfo.ZoneInfo(tz_name)

    try:
        result = build(spec, block, catalogue(), _api_lookup, tz, _column_formats(sheet, block))
    except api.APIError as exc:
        st.warning(f"Could not check names against the database yet: {exc}")
        return
    for error in result.errors:
        st.error(error.message)
    if result.errors:
        return
    for collision in result.collisions:
        st.error(collision.message)

    counts = result.counts()
    st.info(
        f"Ready to write **{counts['experiments']}** experiment, "
        f"**{counts['samples']}** sample(s), **{counts['series']}** series, "
        f"**{counts['measurements']}** measurement(s)."
    )
    if st.button(
        "Submit to /ingest/lab",
        key=f"sheet_submit::{sheet}",
        type="primary",
        disabled=bool(result.collisions),
        width="stretch",
    ):
        _do_submit(result)


def _do_submit(result: BuildResult) -> None:
    """Submit the whole import: one request for its samples, one for its measurements.

    Source rows sharing a sample identity — a long-format sheet puts one
    parameter per row — describe one physical sample and are submitted once.
    """
    identities = list(dict.fromkeys(sample_key(row.sample) for row in result.rows))
    first_row = {sample_key(row.sample): row.sample for row in reversed(result.rows)}

    status = st.status(f"Creating {len(identities)} sample(s)…", expanded=True)
    try:
        sample_ids = api.create_samples([_serialize(first_row[k]) for k in identities])["sample_ids"]
    except Exception as exc:
        status.update(label="Nothing was written.", state="error")
        st.error(f"Could not create the samples: {exc}")
        return
    by_identity = dict(zip(identities, sample_ids))

    measurements = [
        _measurement_payload(m, by_identity[sample_key(row.sample)])
        for row in result.rows
        for m in row.measurements
    ]
    status.update(label=f"Writing {len(measurements)} measurement(s)…")
    payload = {"measurements": measurements, **_serialize(result.experiment or {})}
    try:
        response = api.ingest_lab(payload)
    except Exception as exc:
        status.update(label="The samples were created, but no measurements were written.", state="error")
        st.error(
            f"{exc}\n\nThe {len(sample_ids)} sample(s) above were created. Submitting "
            "again will report them as already on record — remove them first, or "
            "attach the measurements from the lab ingest page."
        )
        return
    status.update(label="Submitted.", state="complete")
    st.success(
        f"Wrote {response.get('rows_written')} measurement(s) across "
        f"{len(sample_ids)} sample(s) into experiment "
        f"{response.get('lab_experiment_id')}."
    )


def sheet_import_page() -> None:
    st.title("📗 Import Data (Sheet)")
    st.caption(
        "Upload a spreadsheet and point at your table. The old mapper page is "
        "still available while this one settles in."
    )
    upload = st.file_uploader(
        "CSV or Excel workbook",
        type=["csv", "xlsx", "xlsm", "xls"],
        help="Every worksheet of a workbook becomes a tab. Nothing is read as a table until you point at your header row.",
    )
    if upload is None:
        st.info("Upload a file to begin.")
        return

    grids = _grids(upload.getvalue(), upload.name)
    names = list(grids)
    for tab, name in zip(st.tabs(names), names):
        with tab:
            _sheet_ui(name, grids[name])


sheet_import_page()
