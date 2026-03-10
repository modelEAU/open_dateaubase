import argparse

from table_import.import_script import main, read_config_from_file, str_to_bool


def cli() -> None:
    parser = argparse.ArgumentParser(description="Import data from sensor files into datEAUbase")
    parser.add_argument("--config", type=str, required=True, help="Path to the YAML configuration file.")
    parser.add_argument("--local", type=str_to_bool, default=False, help="Use local DB connection (true/false).")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Collect and format data but do not write to the database.")
    args = parser.parse_args()
    configuration = read_config_from_file(args.config)
    main(configuration, args.local, dry_run=args.dry_run)


if __name__ == "__main__":
    cli()
