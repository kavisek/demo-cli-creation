"""`mycloud config`: view and edit properties."""

from mycloud import console, properties
from mycloud.arguments import add_command, add_group

NAME = "config"


def register(subparsers, common):
    config = add_group(subparsers, NAME, common=common, help="View and edit mycloud properties.")

    p = add_command(
        config,
        "set",
        common=common,
        func=set_property,
        command="config.set",
        help="Set a property.",
        examples="""
            $ mycloud config set project demo-project
            $ mycloud config set compute/zone us-east1-b
        """,
    )
    p.add_argument("property", metavar="SECTION/PROPERTY", help=_property_help())
    p.add_argument("value", metavar="VALUE", help="Value to store.")

    p = add_command(
        config,
        "get",
        common=common,
        func=get_property,
        command="config.get",
        help="Print the value of a property.",
        default_format="value",
    )
    p.add_argument("property", metavar="SECTION/PROPERTY", help=_property_help())

    p = add_command(
        config,
        "unset",
        common=common,
        func=unset_property,
        command="config.unset",
        help="Remove a property from the properties file.",
    )
    p.add_argument("property", metavar="SECTION/PROPERTY", help=_property_help())

    add_command(
        config,
        "list",
        common=common,
        func=list_properties,
        command="config.list",
        help="List every property that has a value, including ones set by env vars.",
        default_format="yaml",
    )


def _property_help() -> str:
    names = ", ".join(sorted(properties.PROPERTIES))
    return f"One of: {names}. A bare name means core/NAME."


def set_property(ctx):
    key = properties.normalize(ctx.args.property)
    properties.set_value(key, ctx.args.value)
    console.status(f"Updated property [{key}].")


def get_property(ctx):
    value = properties.get(properties.normalize(ctx.args.property))
    if value is None:
        console.status("(unset)")
    return value


def unset_property(ctx):
    key = properties.normalize(ctx.args.property)
    properties.unset(key)
    console.status(f"Unset property [{key}].")


def list_properties(ctx):
    return properties.effective()
