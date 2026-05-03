import argparse
import sys
from pathlib import Path

from table_import.import_script import (
    main as import_main,
    read_config_from_file,
    read_configs_from_dir,
)


def _cmd_import(args: argparse.Namespace) -> None:
    if args.config_dir is not None:
        configuration = read_configs_from_dir(args.config_dir)
    else:
        if args.config is None:
            raise SystemExit("error: one of --config or --config-dir is required")
        configuration = read_config_from_file(args.config)
    if args.min_timestamp is not None:
        configuration.api_config.min_timestamp = args.min_timestamp
    if args.api_url is not None:
        configuration.api_config.api_url = args.api_url
    import_main(configuration, dry_run=args.dry_run)


def _cmd_l5x(args: argparse.Namespace) -> None:
    from xml.etree import ElementTree as ET

    from table_import.api_client import DateaubaseClient
    from table_import.l5x_loader import apply_l5x_load, plan_l5x_load

    tree = ET.parse(args.l5x_file)
    root = tree.getroot()

    plan = plan_l5x_load(
        root,
        args.signal_interface,
        das_name=args.das_name,
        si_type_name=args.si_type,
    )

    if args.dry_run:
        from table_import.l5x_loader import _print_plan

        _print_plan(plan)
    else:
        api_url = args.api_url or "http://localhost:8000"
        with DateaubaseClient(api_url) as client:
            result = apply_l5x_load(plan, client)
            print(f"SignalInterface ID:  {result.signal_interface_id}")
            print(f"Ports created:       {result.ports_created}")
            print(f"Channels created:    {result.channels_created}")
            print(f"Port histories:      {result.port_histories_opened}")


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="open_datEAUbase import tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ---- import subcommand (original behaviour) ----
    p_import = sub.add_parser("import", help="Import sensor data from a YAML config file or directory")
    p_import.add_argument("--config", default=None, help="Path to a single YAML configuration file")
    p_import.add_argument("--config-dir", default=None, metavar="DIR",
                          help="Directory of *.yaml config files (merged at runtime)")
    p_import.add_argument("--api-url", default=None, metavar="URL",
                          help="Override api_config.api_url from the config file(s)")
    p_import.add_argument("--dry-run", action="store_true", default=False,
                          help="Collect and format data but do not write to the API")
    p_import.add_argument("--min-timestamp", metavar="ISO8601", default=None,
                          help="Earliest timestamp to import (overrides config api_config.min_timestamp)")

    # ---- l5x subcommand ----
    p_l5x = sub.add_parser("l5x", help="Load a Logix5000 L5X file into datEAUbase")
    p_l5x.add_argument("l5x_file", type=Path, metavar="FILE.L5X",
                        help="Path to the .L5X export file")
    p_l5x.add_argument("--signal-interface", required=True, metavar="NAME",
                        help="Name of the SignalInterface to create or reuse")
    p_l5x.add_argument("--das-name", default=None, metavar="NAME",
                        help="DataAcquisitionSystem name (defaults to --signal-interface)")
    p_l5x.add_argument("--si-type", default="PLC", metavar="TYPE",
                        help="SignalInterfaceType name (default: PLC)")
    p_l5x.add_argument("--api-url", default=None, metavar="URL",
                        help="datEAUbase API base URL (default: http://localhost:8000)")
    p_l5x.add_argument("--dry-run", action="store_true", default=False,
                        help="Print the load plan without writing to the API")

    # Backward compatibility: if --config is the first flag (no subcommand given), treat as 'import'
    if len(sys.argv) > 1 and sys.argv[1] == "--config":
        sys.argv.insert(1, "import")

    args = parser.parse_args()

    if args.command == "import":
        _cmd_import(args)
    elif args.command == "l5x":
        _cmd_l5x(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli()
