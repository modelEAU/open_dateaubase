import os
from pathlib import Path
from datetime import datetime
from importlib.metadata import version

package_version = version("open-dateaubase")
TARGET_DBS = ["mssql"]


def on_pre_build(config):
    """
    MkDocs hook that runs before build process.
    Calls the orchestrator script to generate all documentation components.
    """
    # Define paths
    project_root = Path(config["config_file_path"]).parent
    json_path = project_root / "src" / "dictionary.json"
    docs_dir = Path(config["docs_dir"])
    output_path = docs_dir / "reference"
    sql_path = project_root / "sql_generation_scripts"
    assets_path = docs_dir / "assets"

    # Call orchestrator script
    scripts_dir = project_root / "scripts"
    orchestrator = scripts_dir / "orchestrate_docs.py"

    # Build command
    cmd = [
        "uv",
        "run",
        "python",
        str(orchestrator),
        str(json_path),
        str(output_path),
        str(sql_path),
        str(assets_path),
    ]

    # Add target databases
    cmd.extend(TARGET_DBS)

    print(f"Running documentation generation orchestrator...")
    print(f"Command: {' '.join(cmd)}")

    # Run orchestrator
    result = os.system(" ".join(cmd))

    if result != 0:
        print("Error: Documentation generation failed!")
        return

    print("Documentation generation completed successfully!")
