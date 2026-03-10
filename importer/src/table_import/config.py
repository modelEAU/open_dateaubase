from typing import List

from pydantic import BaseModel


class Variable(BaseModel):
    directory_path: str
    name: str
    variable_name: str
    metadata_id: int
    scaling_factor: float


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


class DatabaseConfig(BaseModel):
    database_name: str
    credentials_path: str
    local_url: str
    remote_url: str


class TsdbFileStructure(BaseModel):
    extension: str = ".tsdb"
    timezone: str  # e.g. "America/Montreal" (for documentation)


class TsdbVariable(BaseModel):
    name: str
    directory_path: str
    metadata_id: int
    scaling_factor: float = 1.0


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
    metadata_id: int
    scaling_factor: float = 1.0


class ScadaSqlSource(BaseModel):
    name: str = "scada_sql"
    scada_structure: ScadaSqlStructure
    variables: List[ScadaVariable]


class Config(BaseModel):
    file_configs: List[FileType]
    database_config: DatabaseConfig
    tsdb_configs: List[TsdbSource] = []
    scada_sql_configs: List[ScadaSqlSource] = []
