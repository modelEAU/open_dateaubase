from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator, model_validator


# ---------------------------------------------------------------------------
# Quality / status mapping
# ---------------------------------------------------------------------------


class StatusMap(BaseModel):
    """Maps a file's status column values to API quality codes.

    - ``map``: status string → quality code integer (or None for good data).
    - ``default_quality_code``: applied to status values not listed in ``map``.
      If None, unmapped rows are skipped with a warning.
    """

    column: str
    map: dict[str, int | None]
    default_quality_code: int | None = None


# ---------------------------------------------------------------------------
# Axis / bin definitions (used for vector and matrix sources)
# ---------------------------------------------------------------------------


class BinConfig(BaseModel):
    """One bin in a binning axis, referencing a column in the source file.

    Valid states (mirrors DB BinMode):
    - interval: lower_bound + upper_bound (no nominal_value)
    - interval_with_nominal: all three fields set
    - nominal: nominal_value only (no bounds)
    """

    source_column: str
    lower_bound: float | None = None
    upper_bound: float | None = None
    nominal_value: float | None = None

    @model_validator(mode="after")
    def validate_bin_state(self) -> BinConfig:
        has_lower = self.lower_bound is not None
        has_upper = self.upper_bound is not None
        has_nominal = self.nominal_value is not None
        if has_lower != has_upper:
            raise ValueError("lower_bound and upper_bound must both be set or both be null")
        if not has_lower and not has_nominal:
            raise ValueError("At least one of bounds or nominal_value must be provided")
        if has_lower and self.upper_bound <= self.lower_bound:  # type: ignore[operator]
            raise ValueError("upper_bound must be greater than lower_bound")
        return self


class AxisConfig(BaseModel):
    """Inline description of a binning axis for find-or-create resolution.

    ``name`` is the match key: the importer will find an existing axis by this
    name and verify the bin fingerprint, or create a new one if absent.
    ``unit_name`` is resolved to a Unit_ID at runtime (no DB ID needed in the config).
    """

    name: str
    description: str | None = None
    unit_name: str
    bin_mode: Literal["interval", "interval_with_nominal", "nominal"]
    bins: list[BinConfig]


# ---------------------------------------------------------------------------
# Shared base — fields common to all variable types
# ---------------------------------------------------------------------------


class BaseVariable(BaseModel):
    name: str
    parameter_name: str
    source_unit_name: str         # human label for raw unit (aids config authoring)
    destination_unit_name: str    # human label for DB unit (aids config authoring)
    conversion_factor: float = 1.0
    signal_port_type: str = "value"
    data_provenance_id: int = 1
    processing_degree_id: int = 1


# ---------------------------------------------------------------------------
# File-based scalar variables
# ---------------------------------------------------------------------------


class TaggedFileVariable(BaseVariable):
    directory_path: str
    source_variable_name: str | None = None  # row filter: keep rows where variable_column == this
    tag: str
    parent_tag: str | None = None


class TaglessFileVariable(BaseVariable):
    directory_path: str
    source_variable_name: str | None = None
    equipment_name: str


# ---------------------------------------------------------------------------
# TSDB binary variables
# ---------------------------------------------------------------------------


class TaggedTsdbVariable(BaseVariable):
    directory_path: str
    tag: str
    parent_tag: str | None = None


class TaglessTsdbVariable(BaseVariable):
    directory_path: str
    equipment_name: str


# ---------------------------------------------------------------------------
# pilEAUte SCADA variable (always tagged)
# ---------------------------------------------------------------------------


class PilEAUteSCADAVariable(BaseVariable):
    tag: str
    parent_tag: str | None = None


# ---------------------------------------------------------------------------
# Vector file variables (tagged only for now)
# ---------------------------------------------------------------------------


class TaggedVectorFileVariable(BaseVariable):
    directory_path: str
    tag: str
    parent_tag: str | None = None
    axis: AxisConfig


# ---------------------------------------------------------------------------
# Image folder variables
# ---------------------------------------------------------------------------


class TaggedImageFolderVariable(BaseVariable):
    directory_path: str
    tag: str
    parent_tag: str | None = None


class TaglessImageFolderVariable(BaseVariable):
    directory_path: str
    equipment_name: str


# ---------------------------------------------------------------------------
# Matrix file variables (stub — reader not yet implemented)
# ---------------------------------------------------------------------------


class TaggedMatrixFileVariable(BaseVariable):
    directory_path: str
    tag: str
    parent_tag: str | None = None
    row_axis: AxisConfig
    col_axis: AxisConfig


# ---------------------------------------------------------------------------
# File structure configs
# ---------------------------------------------------------------------------


class FileStructure(BaseModel):
    """Structure description for delimited text files (CSV/TSV).

    ``status_map`` replaces the old ``validity_column``/``validity_flag`` pair.
    Omit it to ingest all rows with quality_code=null.
    ``variable_column`` is a row-selector for multi-variable files
    (e.g. files that interleave DO and Temperature rows).
    """

    extension: str
    separator: str
    encoding: str
    dt_format: str
    time_column: str
    timezone: str
    value_column: str
    variable_column: str | None = None  # column used for row selection (multi-variable files)
    status_map: StatusMap | None = None
    first_valid_row_idx: int
    last_valid_row_idx: int
    header_row_idx: int


class TsdbFileStructure(BaseModel):
    extension: str = ".tsdb"
    timezone: str  # e.g. "America/Montreal"


class VectorFileStructure(BaseModel):
    """Structure description for tab-separated spectrophotometry/vector files."""

    extension: str                        # e.g. ".fp", ".par"
    separator: str = "\t"
    encoding: str = "utf-8"
    metadata_rows: int = 1                # rows before the header row to skip
    header_row_idx: int = 1              # 0-based index of the header row
    dt_column: str = "Date/Time"
    dt_format: str = "%Y.%m.%d  %H:%M:%S"
    timezone: str
    status_map: StatusMap | None = None


class TimestampSource(str, Enum):
    """Controls which timestamp extraction strategies are attempted for image files.

    - ``exif``: EXIF DateTimeOriginal/DateTime → filename stem → return None (default)
    - ``filename``: filename stem only → return None
    - ``mtime``: EXIF → filename stem → file mtime (OS modification time)
    """

    exif = "exif"
    filename = "filename"
    mtime = "mtime"


class ImageFolderStructure(BaseModel):
    """Structure description for a folder of instrument images."""

    extensions: list[str] = [".jpg", ".jpeg", ".png", ".tiff"]
    timezone: str
    filename_format: str | None = None   # strptime applied to full filename stem; used if no EXIF
    timestamp_source: TimestampSource = TimestampSource.exif


class MatrixFileStructure(BaseModel):
    """Structure description for 2D matrix data files (stub)."""

    extension: str
    separator: str = "\t"
    encoding: str = "utf-8"
    dt_column: str
    dt_format: str
    timezone: str
    status_map: StatusMap | None = None


# ---------------------------------------------------------------------------
# Source-level configs
# ---------------------------------------------------------------------------


class TaggedFileConfig(BaseModel):
    name: str
    mode: Literal["tagged"]
    das_name: str
    signal_interface_name: str | None = None
    file_reader_type: str | None = None
    file_structure: FileStructure
    variables: list[TaggedFileVariable]


class TaglessFileConfig(BaseModel):
    name: str
    mode: Literal["tagless"]
    das_name: str
    signal_interface_name: str | None = None
    file_reader_type: str | None = None
    file_structure: FileStructure
    variables: list[TaglessFileVariable]


class TaggedTsdbConfig(BaseModel):
    name: str
    mode: Literal["tagged"]
    das_name: str
    signal_interface_name: str | None = None
    tsdb_structure: TsdbFileStructure
    variables: list[TaggedTsdbVariable]


class TaglessTsdbConfig(BaseModel):
    name: str
    mode: Literal["tagless"]
    das_name: str
    signal_interface_name: str | None = None
    tsdb_structure: TsdbFileStructure
    variables: list[TaglessTsdbVariable]


class PilEAUteSCADAStructure(BaseModel):
    timezone: str
    sqlite_path: str | None = None
    server: str | None = None
    database: str | None = None
    credentials_path: str | None = None


class PilEAUteSCADAConfig(BaseModel):
    name: str
    das_name: str
    signal_interface_name: str | None = None
    scada_structure: PilEAUteSCADAStructure
    variables: list[PilEAUteSCADAVariable]


class TaggedVectorFileConfig(BaseModel):
    name: str
    mode: Literal["tagged"] = "tagged"
    das_name: str
    signal_interface_name: str | None = None
    file_structure: VectorFileStructure
    variables: list[TaggedVectorFileVariable]


class TaggedImageFolderConfig(BaseModel):
    name: str
    mode: Literal["tagged"] = "tagged"
    das_name: str
    signal_interface_name: str | None = None
    folder_structure: ImageFolderStructure
    variables: list[TaggedImageFolderVariable]


class TaglessImageFolderConfig(BaseModel):
    name: str
    mode: Literal["tagless"] = "tagless"
    das_name: str
    signal_interface_name: str | None = None
    folder_structure: ImageFolderStructure
    variables: list[TaglessImageFolderVariable]


class TaggedMatrixFileConfig(BaseModel):
    """Matrix file config — reader not yet implemented, raises NotImplementedError at runtime."""

    name: str
    mode: Literal["tagged"] = "tagged"
    das_name: str
    signal_interface_name: str | None = None
    file_structure: MatrixFileStructure
    variables: list[TaggedMatrixFileVariable]


# ---------------------------------------------------------------------------
# API config
# ---------------------------------------------------------------------------


class ApiConfig(BaseModel):
    api_url: str
    min_timestamp: str | None = None  # ISO 8601 global cutoff (e.g. "2024-01-01T00:00:00")


# ---------------------------------------------------------------------------
# Root config
# ---------------------------------------------------------------------------


class Config(BaseModel):
    api_config: ApiConfig
    file_configs: list[
        Annotated[TaggedFileConfig | TaglessFileConfig, Discriminator("mode")]
    ] = []
    tsdb_configs: list[
        Annotated[TaggedTsdbConfig | TaglessTsdbConfig, Discriminator("mode")]
    ] = []
    scada_sql_configs: list[PilEAUteSCADAConfig] = []
    vector_file_configs: list[TaggedVectorFileConfig] = []
    image_folder_configs: list[
        Annotated[TaggedImageFolderConfig | TaglessImageFolderConfig, Discriminator("mode")]
    ] = []
    matrix_file_configs: list[TaggedMatrixFileConfig] = []
