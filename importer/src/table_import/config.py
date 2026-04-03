from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Discriminator


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
# File-based variables
# ---------------------------------------------------------------------------


class TaggedFileVariable(BaseVariable):
    directory_path: str
    source_variable_name: str   # value to match in the file's variable column (row filter)
    tag: str
    parent_tag: str | None = None


class TaglessFileVariable(BaseVariable):
    directory_path: str
    source_variable_name: str
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
# File structure configs (unchanged internally)
# ---------------------------------------------------------------------------


class FileStructure(BaseModel):
    extension: str
    separator: str
    encoding: str
    dt_format: str
    time_column: str
    timezone: str
    value_column: str
    variable_column: str
    validity_column: str
    validity_flag: int
    first_valid_row_idx: int
    last_valid_row_idx: int
    header_row_idx: int


class TsdbFileStructure(BaseModel):
    extension: str = ".tsdb"
    timezone: str  # e.g. "America/Montreal"


# ---------------------------------------------------------------------------
# Source-level configs — mode is the discriminator for file/tsdb sources
# ---------------------------------------------------------------------------


class TaggedFileConfig(BaseModel):
    name: str
    mode: Literal["tagged"]
    das_name: str
    file_structure: FileStructure
    variables: list[TaggedFileVariable]


class TaglessFileConfig(BaseModel):
    name: str
    mode: Literal["tagless"]
    das_name: str
    file_structure: FileStructure
    variables: list[TaglessFileVariable]


class TaggedTsdbConfig(BaseModel):
    name: str
    mode: Literal["tagged"]
    das_name: str
    tsdb_structure: TsdbFileStructure
    variables: list[TaggedTsdbVariable]


class TaglessTsdbConfig(BaseModel):
    name: str
    mode: Literal["tagless"]
    das_name: str
    tsdb_structure: TsdbFileStructure
    variables: list[TaglessTsdbVariable]


class PilEAUteSCADAStructure(BaseModel):
    timezone: str                    # timezone of the SCADA timestamps
    sqlite_path: str | None = None   # use a local SQLite file instead of SQL Server
    server: str | None = None
    database: str | None = None
    credentials_path: str | None = None  # plain-text file: line 1 = user, line 2 = password


class PilEAUteSCADAConfig(BaseModel):
    name: str
    das_name: str
    scada_structure: PilEAUteSCADAStructure
    variables: list[PilEAUteSCADAVariable]


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
