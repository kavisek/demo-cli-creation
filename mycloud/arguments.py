"""Building blocks for the command tree, so every command is spelled the same way.

The tree has two kinds of node:
  * groups (nouns): `compute`, `instances` -- they only hold other nodes
  * commands (verbs): `list`, `create` -- leaves that run a handler
"""

import argparse
import re
import textwrap
from collections.abc import Callable

NAME_RE = re.compile(r"^[a-z]([-a-z0-9]{0,61}[a-z0-9])?$")


class HelpFormatter(argparse.RawDescriptionHelpFormatter):
    """Keep the line breaks in EXAMPLES sections."""


def add_group(subparsers, name: str, *, common: list, help: str):
    """Add a noun group and return the subparsers action for its children."""
    parser = subparsers.add_parser(
        name, parents=common, help=help, description=help, formatter_class=HelpFormatter
    )
    return parser.add_subparsers(
        title="commands", metavar="COMMAND", dest=f"{name}_command", required=True
    )


def add_command(
    subparsers,
    name: str,
    *,
    common: list,
    func: Callable,
    command: str,
    help: str,
    examples: str = "",
    default_format: str | None = None,
) -> argparse.ArgumentParser:
    """Add a verb.

    `command` is the dotted path (e.g. `compute.instances.create`) used in error
    messages. `default_format` is how the result prints when --format isn't given.
    """
    epilog = "EXAMPLES\n" + textwrap.indent(textwrap.dedent(examples).strip(), "  ")
    parser = subparsers.add_parser(
        name,
        parents=common,
        help=help,
        description=help,
        epilog=epilog if examples else None,
        formatter_class=HelpFormatter,
    )
    parser.set_defaults(func=func, command=f"mycloud.{command}", default_format=default_format)
    return parser


def add_list_flags(parser: argparse.ArgumentParser) -> None:
    """The flags every `list` command shares."""
    group = parser.add_argument_group("list command flags")
    group.add_argument(
        "--filter",
        metavar="EXPRESSION",
        help="Only show resources that match, e.g. 'status=RUNNING name~^web'. "
        "Operators: = != ~ (regex) : (contains).",
    )
    group.add_argument(
        "--sort-by",
        metavar="FIELD",
        help="Comma-separated fields to sort by. Prefix a field with ~ to reverse it.",
    )
    group.add_argument("--limit", type=positive_int, metavar="N", help="Show at most N resources.")


def resource_name(value: str) -> str:
    if not NAME_RE.match(value):
        raise argparse.ArgumentTypeError(
            f"invalid name [{value}]: use 1-63 lowercase letters, digits, or hyphens, "
            "starting with a letter and not ending with a hyphen"
        )
    return value


def key_value_dict(value: str) -> dict[str, str]:
    """Parse `--labels env=dev,team=data` into a dict."""
    result = {}
    for pair in value.split(","):
        key, sep, val = pair.partition("=")
        if not sep or not key:
            raise argparse.ArgumentTypeError(f"invalid pair [{pair}]: expected KEY=VALUE")
        result[key] = val
    return result


def comma_list(value: str) -> list[str]:
    return [item for item in value.split(",") if item]


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        number = 0
    if number < 1:
        raise argparse.ArgumentTypeError(f"invalid value [{value}]: expected a positive integer")
    return number
