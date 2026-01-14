# datEAUbase

This repo contains the reference implementation of the dat*EAU*base relational database and data model for use in water resource recovery facilities (WRRFs). The purpose of dat*EAU*base is to allow WRRF data to be stored *along with their context* to ensure that they are correctly interpreted in data mining, modelling and decision support activities.

## Repo contents

- `/sql_generation_scripts`: This folder contains the SQL scripts that generate the tables, key constraints and fields defined by the dat*EAU*base data model. The scripts are versioned starting at v0 which corresponds to the version published in [Plana et al. (2019)](https://iwaponline.com/wqrj/article/54/1/1/64706/Towards-a-water-quality-database-for-raw-and). The scripts are refferred to as *"as designed"* (e.g., coming from a documented specification) or *"as built"* (e.g., reflecting the state of the pilEAUte's datEAUbase instance at a given date.) The scripts also vary based on the target database environment (e.g., MSSQL, MYSQL, etc.)

- `/docs`: The folder containing the source files for the official documentation of the datEAUbase project. The files found in `/docs` are processed by the python package `mkdocs` to build the documentation site. 

- `/tests`: Contains a battery of tests to ensure that the documentation generation code responsible for creating the documentation website and the SQL generation scripts are working adequately.

- `/src`: The folder that contains the "source of truth" document for the datEAUbase: the dictionary table. The documentation and SQL statements are generated from the data encoded in this table.

## How to use this repo

### Install `uv`

`uv` is a tool for managing dependencies, virtual encironments and package distribution for Python. Install it with the following commands:

**macOS and Linux:**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Alternatively, you can use package managers:

- macOS: `brew install uv`
- Windows: `winget install --id=astral-sh.uv -e`

### Install locally for development

```uv sync .```

```uv pip install -e .```

To install with development dependencies:

```bash
uv sync --all-extras
```

or

```bash
uv pip install -e ".[dev]"
```

### Run the tests

```uv run pytest```

### Build the docs website and serve it locally

```uv run mkdocs serve```

## License
dat*EAU*base is published under the CC-BY 4.0 license.
