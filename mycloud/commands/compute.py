"""`mycloud compute`: create and manage virtual machine instances."""

from mycloud import console, properties
from mycloud.arguments import (
    add_command,
    add_group,
    add_list_flags,
    comma_list,
    key_value_dict,
    resource_name,
)
from mycloud.backend import MACHINE_TYPES, Backend, list_zones

NAME = "compute"
INSTANCE_TABLE = "table(name,zone,machineType,status)"


def register(subparsers, common):
    compute = add_group(
        subparsers, NAME, common=common, help="Create and manage virtual machine instances."
    )
    instances = add_group(
        compute, "instances", common=common, help="Create, inspect, and delete instances."
    )

    p = add_command(
        instances,
        "list",
        common=common,
        func=list_instances,
        command="compute.instances.list",
        help="List instances in the project.",
        default_format=INSTANCE_TABLE,
        examples="""
            To list running instances in one zone:

              $ mycloud compute instances list --zones=us-east1-b --filter=status=RUNNING

            To print only names, one per line, for use in a script:

              $ mycloud compute instances list --format='value(name)'
        """,
    )
    add_list_flags(p)
    p.add_argument(
        "--zones",
        type=comma_list,
        metavar="ZONE,[ZONE,...]",
        help="Only list instances in these zones.",
    )

    p = add_command(
        instances,
        "describe",
        common=common,
        func=describe_instance,
        command="compute.instances.describe",
        help="Show every field of one instance.",
        default_format="yaml",
        examples="""
            $ mycloud compute instances describe web-1 --zone=us-east1-b
        """,
    )
    p.add_argument("name", type=resource_name, metavar="NAME", help="Name of the instance.")
    _add_zone_flag(p)

    p = add_command(
        instances,
        "create",
        common=common,
        func=create_instances,
        command="compute.instances.create",
        help="Create one or more instances.",
        default_format=INSTANCE_TABLE,
        examples="""
            $ mycloud compute instances create web-1 web-2 --zone=us-east1-b \\
                --machine-type=e2-medium --labels=env=dev,team=data
        """,
    )
    p.add_argument(
        "names", nargs="+", type=resource_name, metavar="NAME", help="Names of the instances."
    )
    _add_zone_flag(p)
    p.add_argument(
        "--machine-type",
        choices=MACHINE_TYPES,
        default="e2-small",
        help="Machine type (default: %(default)s).",
    )
    p.add_argument(
        "--labels",
        type=key_value_dict,
        default={},
        metavar="KEY=VALUE,[...]",
        help="Labels to attach to the instances.",
    )

    for verb, func, status in (
        ("delete", delete_instances, "Delete"),
        ("start", start_instances, "Start"),
        ("stop", stop_instances, "Stop"),
    ):
        p = add_command(
            instances,
            verb,
            common=common,
            func=func,
            command=f"compute.instances.{verb}",
            help=f"{status} one or more instances.",
            examples=f"""
                $ mycloud compute instances {verb} web-1 web-2 --zone=us-east1-b
            """,
        )
        p.add_argument(
            "names", nargs="+", type=resource_name, metavar="NAME", help="Names of the instances."
        )
        _add_zone_flag(p)

    zones = add_group(compute, "zones", common=common, help="Browse the zones you can use.")
    p = add_command(
        zones,
        "list",
        common=common,
        func=lambda _ctx: list_zones(),
        command="compute.zones.list",
        help="List zones.",
        default_format="table(name,region,status)",
    )
    add_list_flags(p)


def _add_zone_flag(parser):
    parser.add_argument(
        "--zone", help="Zone of the instances. Overrides the compute/zone property."
    )


def _zone(ctx) -> str:
    return properties.require("compute/zone", ctx.args.zone, "zone")


def list_instances(ctx):
    return Backend(ctx.project).list_instances(zones=ctx.args.zones)


def describe_instance(ctx):
    return Backend(ctx.project).get_instance(ctx.args.name, _zone(ctx))


def create_instances(ctx):
    backend, zone = Backend(ctx.project), _zone(ctx)
    created = []
    for name in ctx.args.names:
        instance = backend.create_instance(name, zone, ctx.args.machine_type, ctx.args.labels)
        console.status(f"Created [{instance['selfLink']}].")
        created.append(instance)
    return created


def delete_instances(ctx):
    backend, zone = Backend(ctx.project), _zone(ctx)
    targets = "\n".join(f" - [{name}] in [{zone}]" for name in ctx.args.names)
    console.confirm(f"The following instances will be deleted:\n{targets}\n", ctx.quiet)
    for name in ctx.args.names:
        console.status(f"Deleted [{backend.delete_instance(name, zone)}].")


def start_instances(ctx):
    _set_status(ctx, "RUNNING")


def stop_instances(ctx):
    _set_status(ctx, "TERMINATED")


def _set_status(ctx, status):
    backend, zone = Backend(ctx.project), _zone(ctx)
    for name in ctx.args.names:
        instance = backend.set_instance_status(name, zone, status)
        console.status(f"Updated [{instance['selfLink']}].")
