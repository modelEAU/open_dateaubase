# AGENTS.md

## Commands
- **Install**: `uv sync --all-extras`
- **Test all**: `uv run pytest`
- **Test single**: `uv run pytest tests/test_models.py::TestKeyPart::test_valid_key`
- **Build docs**: `uv run mkdocs build`
- **Serve docs**: `uv run mkdocs serve`

## Code Style
- **Python**: 3.12+, use `uv` for dependency management
- **Imports**: Group stdlib, third-party, local imports; use `from pathlib import Path` for paths
- **Types**: Full type hints required, use Pydantic models with discriminated unions
- **Naming**: 
  - Classes: PascalCase
  - Functions/variables: snake_case
  - Constants: UPPER_SNAKE_CASE
  - Keys: end with `_ID`, tables: lowercase_with_underscores, value sets: end with `_set`
- **Error handling**: Use Pydantic validators, raise ValueError with descriptive messages
- **Models**: Use frozen ConfigDict for immutable data, populate_by_name for alias support