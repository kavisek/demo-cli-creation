"""Everything the CLI says to a human goes through here, on stderr.

stdout is reserved for the command's result, so `mycloud ... --format=json | jq`
and `$(mycloud ... --format='value(name)')` always receive clean data.
"""

import sys

from mycloud.errors import CancelledError, PromptError


def status(message: str) -> None:
    """Print a progress or result message for humans, e.g. `Created [...]`."""
    print(message, file=sys.stderr)


def error(command: str, message: object) -> None:
    """Print an error in gcloud's `ERROR: (command) message` shape."""
    print(f"ERROR: ({command}) {message}", file=sys.stderr)


def confirm(message: str, quiet: bool) -> None:
    """Ask before a destructive action. --quiet answers yes on the user's behalf.

    With no terminal attached (CI, a pipe) we refuse rather than guess, so a
    script can never delete something without saying --quiet explicitly.
    """
    if quiet:
        return
    status(message)
    if not sys.stdin.isatty():
        raise PromptError(
            "This command needs confirmation, but stdin is not a terminal. "
            "Re-run with --quiet to proceed without prompting."
        )
    sys.stderr.write("Do you want to continue (Y/n)?  ")
    sys.stderr.flush()
    answer = sys.stdin.readline().strip().lower()
    if answer not in ("", "y", "yes"):
        raise CancelledError("Aborted by user.")
