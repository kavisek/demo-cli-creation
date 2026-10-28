"""Properties: named settings resolved as flag > environment variable > file.

The file lives at $MYCLOUD_CONFIG/properties (default ~/.config/mycloud) and uses
the same INI layout as gcloud's configuration files:

    [core]
    project = demo-project

    [compute]
    zone = us-east1-b

Each property can also be set with an environment variable named
MYCLOUD_<SECTION>_<NAME>, e.g. MYCLOUD_CORE_PROJECT.
"""

import configparser
import logging
import os
from dataclasses import dataclass
from pathlib import Path

from mycloud.errors import InvalidArgumentError, RequiredPropertyError

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Property:
    help: str
    choices: tuple[str, ...] | None = None


PROPERTIES = {
    "core/project": Property("Project used by commands that act on resources."),
    "core/disable_prompts": Property(
        "If true, never prompt; the same as passing --quiet.", choices=("true", "false")
    ),
    "compute/zone": Property("Default zone for compute instance commands."),
}


def config_dir() -> Path:
    return Path(os.environ.get("MYCLOUD_CONFIG") or Path.home() / ".config" / "mycloud")


def properties_file() -> Path:
    return config_dir() / "properties"


def env_var(key: str) -> str:
    return "MYCLOUD_" + key.replace("/", "_").upper()


def normalize(key: str) -> str:
    """Accept `project` as shorthand for `core/project`, as gcloud does."""
    if "/" not in key:
        key = f"core/{key}"
    if key not in PROPERTIES:
        known = ", ".join(sorted(PROPERTIES))
        raise InvalidArgumentError(f"Unknown property [{key}]. Known properties: {known}.")
    return key


def get(key: str, flag_value: str | None = None) -> str | None:
    """Resolve a property: the flag wins, then the env var, then the file."""
    if flag_value is not None:
        return flag_value
    env_value = os.environ.get(env_var(key))
    if env_value:
        log.debug("Using %s from %s", key, env_var(key))
        return env_value
    section, name = key.split("/")
    return _read().get(section, name, fallback=None)


def require(key: str, flag_value: str | None = None, flag: str | None = None) -> str:
    """Like get(), but tell the user exactly how to fix a missing value."""
    value = get(key, flag_value)
    if value:
        return value
    via_flag = f"pass --{flag}, " if flag else ""
    raise RequiredPropertyError(
        f"The required property [{key}] is not currently set. To fix this, {via_flag}"
        f"set {env_var(key)}, or run:\n  $ mycloud config set {key} VALUE"
    )


def set_value(key: str, value: str) -> None:
    choices = PROPERTIES[key].choices
    if choices and value not in choices:
        raise InvalidArgumentError(
            f"Invalid value [{value}] for [{key}]. Expected one of: {', '.join(choices)}."
        )
    parser = _read()
    section, name = key.split("/")
    if not parser.has_section(section):
        parser.add_section(section)
    parser.set(section, name, value)
    _write(parser)


def unset(key: str) -> None:
    parser = _read()
    section, name = key.split("/")
    if parser.has_section(section):
        parser.remove_option(section, name)
        _write(parser)


def effective() -> dict[str, dict[str, str]]:
    """Every property that has a value, as {section: {name: value}}."""
    result: dict[str, dict[str, str]] = {}
    for key in PROPERTIES:
        value = get(key)
        if value is not None:
            section, name = key.split("/")
            result.setdefault(section, {})[name] = value
    return result


def _read() -> configparser.ConfigParser:
    parser = configparser.ConfigParser()
    parser.read(properties_file())
    return parser


def _write(parser: configparser.ConfigParser) -> None:
    path = properties_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        parser.write(f)
    log.debug("Wrote %s", path)
