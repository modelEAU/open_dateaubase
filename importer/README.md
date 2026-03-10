# Table Import

A utility that lets you import plain-text tabular data into the dat*EAU*base.

## Installation

```bash
# create a virtual environment
python virtualenv ./env

# activate the vurtual environment
# on mac
source ./env/bin/activate

# on windows
./env/Scripts/activate.bat

pip install -r requirements.txt
```

## Running the script

```bash
python src/table_import/import_module.py --config /path/to/config.yaml
```

## Setting up the YAML configuration file

This YAML configuration file is designed for setting up and running an import job into the dat*EAU*base database using the import_script.py script. Paths should be specified relative to the script’s location on the file system. Below is a detailed description of the structure and elements within this configuration file:

### Root Elements

1. database_config: Contains settings related to the database connection.
2. file_configs: Contains configurations for files to be processed.

### database_config Section

- database_name: The name of the database to connect to (dateaubase2020).
- credentials_path: Relative path to the file containing database credentials (../../login.txt).
- local_url: Local URL for the database connection (GCI-PR-DATEAU02\DATEAUBASE).
- remote_url: Remote URL for the database connection (132.203.190.77\DATEAUBASE).

### file_configs Section

This section is a list of file configurations. Each configuration includes details about the file structure and the variables within the file. Here is the structure of each configuration:

- name: Name of the configuration (anapro).
- file_structure: Defines the structure of the file to be processed.
- extension: File extension (e.g., .par).
- separator: Field separator (e.g., "\t" for tab-separated values).
- encoding: File encoding (e.g., ISO-8859-1).
- dt_format: Date and time format (e.g., "%Y.%m.%d  %H:%M:%S").
- time_column: Name of the column containing date/time information (Date/Time).
- timezone: Timezone of the date/time information (US/Eastern).
- value_column: Name of the column containing the values (if applicable).
- variable_column: Name of the column containing variable names (if applicable).
- validity_column: Name of the column containing validity flags (if applicable).
- validity_flag: Value of the validity flag indicating valid data (0).
- first_valid_row_idx: Index of the first row with valid data (2).
- last_valid_row_idx: Index of the last row with valid data (-1).
- header_row_idx: Index of the header row (1).
- variables: List of variables to be processed from the file.
- Each variable includes the following properties:
- name: Name of the variable (e.g., NH4-N).
- directory_path: Path to the directory containing the file (Z:/s-canV5.0/Results/INFLPC2).
- variable_name: Name of the variable as it appears in the file (e.g., NH4-N [mg/L]).
- metadata_id: Metadata identifier for the variable (1).
- scaling_factor: Factor to scale the variable values (0.001).

### Example

Below is an example configuration for a variable:
```yaml
- name: NH4-N
  directory_path: Z:/s-canV5.0/Results/INFLPC2
  variable_name: NH4-N [mg/L]
  metadata_id: 1
  scaling_factor: 0.001
```

## Notes

- Ensure all paths are correctly specified relative to the location of the Import.py script.
- Customize the database_config and file_configs sections to match your specific setup and data files.

This structure provides a flexible and detailed way to configure data import jobs, making it easy to adapt to various data sources and formats.
