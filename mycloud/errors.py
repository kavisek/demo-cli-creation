"""Error types.

Every failure we expect (bad input, missing resource, unset property) is an
MycloudError. The CLI prints it as one clean line, `ERROR: (command) message`,
and exits non-zero. Anything else is a bug and gets a traceback under
--verbosity=debug.
"""


class MycloudError(Exception):
    """Base class for errors shown to the user without a stack trace."""

    exit_code = 1


class InvalidArgumentError(MycloudError):
    """A flag or argument value was rejected after parsing."""

    exit_code = 2


class RequiredPropertyError(MycloudError):
    """A value was needed but neither a flag, env var, nor property set it."""


class NotFoundError(MycloudError):
    """The named resource does not exist."""


class AlreadyExistsError(MycloudError):
    """A resource with that name already exists."""


class PromptError(MycloudError):
    """A confirmation was needed but there is no terminal to ask on."""


class CancelledError(MycloudError):
    """The user answered no at a confirmation prompt."""
