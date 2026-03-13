from typing import List

from pydantic import BaseModel


class Variable(BaseModel):
    directory_path: str
    name: str
    variable_name: str
    equipment_name: str
    parameter_name: str
    source_unit_name: str
    channel_unit_name: str
    conversion_factor: float = 1.0
    data_provenance_id: int = 1
    processing_degree_id: int = 1
    metadata_id: int = 0  # used internally by source readers to populate ValueTable; not sent to API


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


class FileType(BaseModel):
    name: str
    file_structure: FileStructure
    variables: List[Variable]


class ApiConfig(BaseModel):
    api_url: str
    min_timestamp: str | None = None  # ISO 8601 global cutoff (e.g. "2024-01-01T00:00:00")


class TsdbFileStructure(BaseModel):
    extension: str = ".tsdb"
    timezone: str  # e.g. "America/Montreal" (for documentation)


class TsdbVariable(BaseModel):
    name: str
    directory_path: str
    equipment_name: str
    parameter_name: str
    source_unit_name: str
    channel_unit_name: str
    conversion_factor: float = 1.0
    data_provenance_id: int = 1
    processing_degree_id: int = 1
    metadata_id: int = 0


class TsdbSource(BaseModel):
    name: str = "tsdb"
    tsdb_structure: TsdbFileStructure
    variables: List[TsdbVariable]


class ScadaSqlStructure(BaseModel):
    server: str
    database: str
    credentials_path: str  # plain-text file: line 1 = user, line 2 = password
    table: str = "FloatTable_hedi"
    datetime_column: str = "DateAndTime"
    tag_index_column: str = "TagIndex"
    value_column: str = "Val"
    timezone: str  # timezone of the SCADA timestamps


class ScadaVariable(BaseModel):
    name: str
    tag_index: int  # filters table by TagIndex column
    equipment_name: str
    parameter_name: str
    source_unit_name: str
    channel_unit_name: str
    conversion_factor: float = 1.0
    data_provenance_id: int = 1
    processing_degree_id: int = 1
    metadata_id: int = 0


class ScadaSqlSource(BaseModel):
    name: str = "scada_sql"
    scada_structure: ScadaSqlStructure
    variables: List[ScadaVariable]


class Config(BaseModel):
    file_configs: List[FileType]
    api_config: ApiConfig
    tsdb_configs: List[TsdbSource] = []
    scada_sql_configs: List[ScadaSqlSource] = []
