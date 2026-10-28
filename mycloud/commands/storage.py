"""`mycloud storage`: create and manage storage buckets."""

from mycloud import console
from mycloud.arguments import add_command, add_group, add_list_flags, resource_name
from mycloud.backend import BUCKET_LOCATIONS, Backend

NAME = "storage"
BUCKET_TABLE = "table(name,location,url)"


def register(subparsers, common):
    storage = add_group(subparsers, NAME, common=common, help="Create and manage storage buckets.")
    buckets = add_group(
        storage, "buckets", common=common, help="Create, inspect, and delete buckets."
    )

    p = add_command(
        buckets,
        "list",
        common=common,
        func=list_buckets,
        command="storage.buckets.list",
        help="List buckets in the project.",
        default_format=BUCKET_TABLE,
        examples="""
            $ mycloud storage buckets list --filter=location=EU --sort-by=~creationTimestamp
        """,
    )
    add_list_flags(p)

    p = add_command(
        buckets,
        "describe",
        common=common,
        func=describe_bucket,
        command="storage.buckets.describe",
        help="Show every field of one bucket.",
        default_format="yaml",
    )
    p.add_argument("name", type=resource_name, metavar="NAME", help="Name of the bucket.")

    p = add_command(
        buckets,
        "create",
        common=common,
        func=create_bucket,
        command="storage.buckets.create",
        help="Create a bucket.",
        default_format=BUCKET_TABLE,
        examples="""
            $ mycloud storage buckets create my-data --location=EU
        """,
    )
    p.add_argument("name", type=resource_name, metavar="NAME", help="Name of the bucket.")
    p.add_argument(
        "--location",
        choices=BUCKET_LOCATIONS,
        default="US",
        help="Where the bucket's data lives (default: %(default)s).",
    )

    p = add_command(
        buckets,
        "delete",
        common=common,
        func=delete_buckets,
        command="storage.buckets.delete",
        help="Delete one or more buckets.",
    )
    p.add_argument(
        "names", nargs="+", type=resource_name, metavar="NAME", help="Names of the buckets."
    )


def list_buckets(ctx):
    return Backend(ctx.project).list_buckets()


def describe_bucket(ctx):
    return Backend(ctx.project).get_bucket(ctx.args.name)


def create_bucket(ctx):
    bucket = Backend(ctx.project).create_bucket(ctx.args.name, ctx.args.location)
    console.status(f"Created [{bucket['selfLink']}].")
    return bucket


def delete_buckets(ctx):
    backend = Backend(ctx.project)
    targets = "\n".join(f" - [{name}]" for name in ctx.args.names)
    console.confirm(f"The following buckets will be deleted:\n{targets}\n", ctx.quiet)
    for name in ctx.args.names:
        console.status(f"Deleted [{backend.delete_bucket(name)}].")
