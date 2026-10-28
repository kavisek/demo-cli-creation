"""Entry point: build the command tree, run the chosen command, print its result."""

import argparse
import logging
import sys

from mycloud import __version__, console, output
from mycloud.arguments import HelpFormatter
from mycloud.commands import compute, config, info, storage
from mycloud.context import Context
from mycloud.errors import MycloudError

GROUPS = [compute, storage, config, info]

VERBOSITY = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "none": logging.CRITICAL + 1,
}


def global_flags() -> argparse.ArgumentParser:
    """Flags accepted at every level of the tree, before or after the command.

    Each group and command lists this parser in `parents`. default=SUPPRESS
    stops a subparser from overwriting a value the user gave earlier on the line.
    """
    flags = argparse.ArgumentParser(add_help=False)
    group = flags.add_argument_group("global flags")
    group.add_argument(
        "--project",
        default=argparse.SUPPRESS,
        metavar="PROJECT_ID",
        help="Project to act on. Overrides the core/project property.",
    )
    group.add_argument(
        "--format",
        default=argparse.SUPPRESS,
        metavar="FORMAT",
        help=f"Output format: {', '.join(output.FORMATS)}; "
        "add fields to pick columns, e.g. 'table(name,status)'.",
    )
    group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Never prompt; answer yes to confirmations.",
    )
    group.add_argument(
        "--verbosity",
        choices=list(VERBOSITY),
        default=argparse.SUPPRESS,
        help="Minimum level of log messages printed to stderr (default: warning).",
    )
    return flags


def build_parser() -> argparse.ArgumentParser:
    common = [global_flags()]
    parser = argparse.ArgumentParser(
        prog="mycloud",
        description="mycloud: a gcloud-style CLI for a pretend cloud.",
        epilog="Run `mycloud GROUP --help` for the commands in a group.",
        parents=common,
        formatter_class=HelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"mycloud {__version__}")
    subparsers = parser.add_subparsers(
        title="groups and commands", metavar="GROUP | COMMAND", dest="group", required=True
    )
    for module in GROUPS:
        module.register(subparsers, common)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run mycloud and return the exit code (0 ok, 1 error, 2 bad usage, 130 Ctrl-C)."""
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:  # --help, --version, or a usage error
        return exc.code if isinstance(exc.code, int) else 0

    logging.basicConfig(
        stream=sys.stderr,
        level=VERBOSITY[getattr(args, "verbosity", "warning")],
        format="%(levelname)s: %(message)s",
        force=True,
    )

    try:
        result = args.func(Context.from_args(args))
        _print_result(args, result)
        return 0
    except MycloudError as exc:
        console.error(args.command, exc)
        return exc.exit_code
    except KeyboardInterrupt:
        console.status("\n\nCommand killed by keyboard interrupt.")
        return 130
    except Exception as exc:  # a bug, not a user mistake
        logging.debug("Unexpected error", exc_info=True)
        console.error(args.command, f"{exc}\nRe-run with --verbosity=debug for a stack trace.")
        return 1


def _print_result(args: argparse.Namespace, result) -> None:
    if result is None:
        return
    if isinstance(result, list):
        result = output.select(
            result,
            filter=getattr(args, "filter", None),
            sort_by=getattr(args, "sort_by", None),
            limit=getattr(args, "limit", None),
        )
        if not result:
            console.status("Listed 0 items.")
            return
    spec = getattr(args, "format", None) or args.default_format or "yaml"
    output.render(result, spec)


def run() -> None:
    """Console-script entry point."""
    sys.exit(main())
