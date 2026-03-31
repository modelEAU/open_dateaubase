import argparse

from table_import.import_script import main, read_config_from_file


def cli() -> None:
    parser = argparse.ArgumentParser(description="Import data from sensor files into datEAUbase via the REST API")
    parser.add_argument("--config", type=str, required=True, help="Path to the YAML configuration file.")
    parser.add_argument("--dry-run", action="store_true", default=False, help="Collect and format data but do not write to the API.")
    parser.add_argument(
        "--min-timestamp",
        metavar="ISO8601",
        default=None,
        help="Earliest timestamp to import (overrides config api_config.min_timestamp).",
    )
    args = parser.parse_args()
    configuration = read_config_from_file(args.config)
    if args.min_timestamp is not None:
        configuration.api_config.min_timestamp = args.min_timestamp
    main(configuration, dry_run=args.dry_run)


if __name__ == "__main__":
    cli()
