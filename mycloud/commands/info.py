"""`mycloud info` and `mycloud version`: what is installed and how it is configured."""

import platform
import sys

from mycloud import __version__, properties
from mycloud.arguments import add_command

NAME = "info"


def register(subparsers, common):
    add_command(
        subparsers,
        "info",
        common=common,
        func=show_info,
        command="info",
        help="Show the installation, config location, and active properties.",
        default_format="yaml",
    )
    add_command(
        subparsers,
        "version",
        common=common,
        func=lambda _ctx: f"mycloud {__version__}",
        command="version",
        help="Print the mycloud version.",
        default_format="value",
    )


def show_info(ctx):
    return {
        "version": __version__,
        "python": platform.python_version(),
        "platform": sys.platform,
        "configDir": str(properties.config_dir()),
        "properties": properties.effective(),
    }
