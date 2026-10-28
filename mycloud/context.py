"""The parsed arguments plus resolved global settings, handed to every command."""

import argparse
from dataclasses import dataclass

from mycloud import properties


@dataclass
class Context:
    args: argparse.Namespace
    quiet: bool

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> "Context":
        quiet = getattr(args, "quiet", False) or properties.get("core/disable_prompts") == "true"
        return cls(args=args, quiet=quiet)

    @property
    def project(self) -> str:
        """Resolved lazily, so only commands that need a project require one."""
        return properties.require("core/project", getattr(self.args, "project", None), "project")
