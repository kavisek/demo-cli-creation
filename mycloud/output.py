"""Turn command results into text: --format, --filter, --sort-by and --limit.

Commands return plain dicts and lists and never print their own results. The
CLI formats them here, so every command gets the same scripting flags for free.
"""

import csv
import json
import re
import shlex
import sys
from typing import Any, TextIO

from mycloud.errors import InvalidArgumentError

FORMATS = ("table", "json", "yaml", "csv", "value")

_FORMAT_RE = re.compile(r"^(?P<name>[a-z]+)(?:\((?P<fields>[^()]*)\))?$")
_TERM_RE = re.compile(r"^(?P<key>[A-Za-z_][\w.]*)(?P<op>!=|=|~|:)(?P<value>.*)$")
_PLAIN_YAML_RE = re.compile(r"^[A-Za-z0-9_./@-][A-Za-z0-9_./@:+ -]*$")
_YAML_KEYWORDS = {"true", "false", "null", "yes", "no", "on", "off", "~"}


def parse_format(spec: str) -> tuple[str, list[str]]:
    """Split `table(name,status)` into ("table", ["name", "status"])."""
    match = _FORMAT_RE.match(spec.strip())
    if not match or match["name"] not in FORMATS:
        raise InvalidArgumentError(
            f"Invalid format [{spec}]. Use one of {', '.join(FORMATS)}, "
            "optionally with fields, e.g. 'table(name,status)' or 'value(name)'."
        )
    fields = [f.strip() for f in (match["fields"] or "").split(",") if f.strip()]
    return match["name"], fields


def get_field(record: dict, path: str) -> Any:
    """Look up a dotted path such as `labels.env`."""
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def select(
    records: list[dict],
    filter: str | None = None,
    sort_by: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Apply --filter, then --sort-by, then --limit, in that order."""
    if filter:
        terms = _parse_filter(filter)
        records = [r for r in records if all(_term_matches(r, *t) for t in terms)]
    if sort_by:
        # Sort by the last key first; Python's sort is stable, so earlier keys win.
        for field in reversed(sort_by.split(",")):
            field = field.strip()
            path = field.lstrip("~")
            records = sorted(
                records,
                key=lambda r, p=path: str(get_field(r, p) or ""),
                reverse=field.startswith("~"),
            )
    if limit is not None:
        records = records[:limit]
    return records


def render(result: Any, spec: str, stream: TextIO | None = None) -> None:
    stream = stream or sys.stdout
    name, fields = parse_format(spec)

    if isinstance(result, str):
        stream.write((json.dumps(result) if name == "json" else result) + "\n")
        return

    records = result if isinstance(result, list) else [result]
    if fields:
        records = [{f: get_field(r, f) for f in fields} for r in records]

    if name == "json":
        data = records if isinstance(result, list) else records[0]
        stream.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
    elif name == "yaml":
        for i, record in enumerate(records):
            if i:
                stream.write("---\n")
            stream.write("\n".join(_yaml_lines(record)) + "\n")
    elif name == "value":
        for record in records:
            stream.write("\t".join(_cell(v) for v in record.values()) + "\n")
    elif name == "csv":
        columns = list(records[0]) if records else []
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows([_cell(r.get(c)) for c in columns] for r in records)
    else:
        _write_table(records, stream)


def _parse_filter(expression: str) -> list[tuple[str, str, Any]]:
    try:
        words = shlex.split(expression)
    except ValueError as exc:
        raise InvalidArgumentError(f"Invalid filter [{expression}]: {exc}.") from exc
    terms = []
    for word in words:
        match = _TERM_RE.match(word)
        if not match:
            raise InvalidArgumentError(
                f"Invalid filter term [{word}]. "
                "Use KEY=VALUE, KEY!=VALUE, KEY~REGEX, or KEY:SUBSTRING."
            )
        value: Any = match["value"]
        if match["op"] == "~":
            try:
                value = re.compile(value)
            except re.error as exc:
                raise InvalidArgumentError(f"Invalid regex in filter [{word}]: {exc}.") from exc
        terms.append((match["key"], match["op"], value))
    return terms


def _term_matches(record: dict, key: str, op: str, expected: Any) -> bool:
    actual = _cell(get_field(record, key))
    if op == "=":
        return actual.lower() == expected.lower()
    if op == "!=":
        return actual.lower() != expected.lower()
    if op == "~":
        return expected.search(actual) is not None
    return expected.lower() in actual.lower()  # ":" means "contains"


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, dict):
        return ";".join(f"{k}={v}" for k, v in sorted(value.items()))
    if isinstance(value, list):
        return ",".join(_cell(v) for v in value)
    return str(value)


def _header(field: str) -> str:
    """`machineType` -> `MACHINE_TYPE`, `labels.env` -> `ENV`, like gcloud tables."""
    name = field.split(".")[-1]
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).upper()


def _write_table(records: list[dict], stream: TextIO) -> None:
    columns = list(records[0])
    rows = [[_header(c) for c in columns]]
    rows += [[_cell(r.get(c)) for c in columns] for r in records]
    widths = [max(len(cell) for cell in column) for column in zip(*rows, strict=True)]
    for row in rows:
        line = "  ".join(cell.ljust(width) for cell, width in zip(row, widths, strict=True))
        stream.write(line.rstrip() + "\n")


def _yaml_lines(value: Any, indent: int = 0) -> list[str]:
    """A tiny YAML writer for the JSON-shaped data our commands return."""
    pad = "  " * indent
    lines = []
    if isinstance(value, dict):
        for key in sorted(value):
            item = value[key]
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key}:")
                lines.extend(_yaml_lines(item, indent + 1))
            else:
                lines.append(f"{pad}{key}: {_yaml_scalar(item)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, (dict, list)) and item:
                nested = _yaml_lines(item, indent + 1)
                lines.append(f"{pad}- {nested[0].lstrip()}")
                lines.extend(nested[1:])
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
    else:
        lines.append(pad + _yaml_scalar(value))
    return lines


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        return "{}"
    if isinstance(value, list):
        return "[]"
    text = str(value)
    looks_like_other_type = text.lower() in _YAML_KEYWORDS or re.fullmatch(r"[\d.eE+-]+", text)
    if _PLAIN_YAML_RE.match(text) and not looks_like_other_type and ": " not in text:
        return text
    return json.dumps(text)
