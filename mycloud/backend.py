"""A fake cloud API backed by a JSON file, so the demo runs anywhere.

In a real CLI this module would be the API client. Because commands only talk
to this class, swapping the JSON file for HTTP calls would not change a single
command.
"""

import json
import logging
import random
from datetime import UTC, datetime
from typing import Any

from mycloud import properties
from mycloud.errors import AlreadyExistsError, InvalidArgumentError, NotFoundError

log = logging.getLogger(__name__)

API_ROOT = "https://mycloud.example.com/v1"
ZONES = {
    "us-east1-b": "us-east1",
    "us-west1-a": "us-west1",
    "europe-west1-b": "europe-west1",
}
MACHINE_TYPES = ("e2-micro", "e2-small", "e2-medium")
BUCKET_LOCATIONS = ("US", "EU")


def list_zones() -> list[dict]:
    return [{"name": z, "region": r, "status": "UP"} for z, r in ZONES.items()]


class Backend:
    """CRUD for one project's instances and buckets."""

    def __init__(self, project: str):
        self.project = project
        self.path = properties.config_dir() / "resources.json"

    # Instances

    def list_instances(self, zones: list[str] | None = None) -> list[dict]:
        instances = list(self._collection(self._load(), "instances").values())
        if zones:
            instances = [i for i in instances if i["zone"] in zones]
        return instances

    def get_instance(self, name: str, zone: str) -> dict:
        self._check_zone(zone)
        instance = self._collection(self._load(), "instances").get(f"{zone}/{name}")
        if instance is None:
            raise NotFoundError(f"The resource [{self._instance_link(name, zone)}] was not found.")
        return instance

    def create_instance(
        self, name: str, zone: str, machine_type: str, labels: dict[str, str]
    ) -> dict:
        self._check_zone(zone)
        state = self._load()
        instances = self._collection(state, "instances")
        link = self._instance_link(name, zone)
        if f"{zone}/{name}" in instances:
            raise AlreadyExistsError(f"The resource [{link}] already exists.")
        instance = {
            "id": str(random.getrandbits(63)),
            "name": name,
            "zone": zone,
            "machineType": machine_type,
            "status": "RUNNING",
            "labels": labels,
            "creationTimestamp": _now(),
            "selfLink": link,
        }
        instances[f"{zone}/{name}"] = instance
        self._save(state)
        return instance

    def set_instance_status(self, name: str, zone: str, status: str) -> dict:
        self.get_instance(name, zone)
        state = self._load()
        instance = self._collection(state, "instances")[f"{zone}/{name}"]
        instance["status"] = status
        self._save(state)
        return instance

    def delete_instance(self, name: str, zone: str) -> str:
        self.get_instance(name, zone)
        state = self._load()
        del self._collection(state, "instances")[f"{zone}/{name}"]
        self._save(state)
        return self._instance_link(name, zone)

    # Buckets

    def list_buckets(self) -> list[dict]:
        return list(self._collection(self._load(), "buckets").values())

    def get_bucket(self, name: str) -> dict:
        bucket = self._collection(self._load(), "buckets").get(name)
        if bucket is None:
            raise NotFoundError(f"The resource [{self._bucket_link(name)}] was not found.")
        return bucket

    def create_bucket(self, name: str, location: str) -> dict:
        state = self._load()
        buckets = self._collection(state, "buckets")
        link = self._bucket_link(name)
        if name in buckets:
            raise AlreadyExistsError(f"The resource [{link}] already exists.")
        bucket = {
            "name": name,
            "location": location,
            "url": f"mc://{name}",
            "creationTimestamp": _now(),
            "selfLink": link,
        }
        buckets[name] = bucket
        self._save(state)
        return bucket

    def delete_bucket(self, name: str) -> str:
        self.get_bucket(name)
        state = self._load()
        del self._collection(state, "buckets")[name]
        self._save(state)
        return self._bucket_link(name)

    # Storage

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def _save(self, state: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2, sort_keys=True))
        log.debug("Saved state to %s", self.path)

    def _collection(self, state: dict[str, Any], kind: str) -> dict[str, dict]:
        return state.setdefault(self.project, {}).setdefault(kind, {})

    def _check_zone(self, zone: str) -> None:
        if zone not in ZONES:
            raise InvalidArgumentError(
                f"Unknown zone [{zone}]. Run `mycloud compute zones list` to see valid zones."
            )

    def _instance_link(self, name: str, zone: str) -> str:
        return f"{API_ROOT}/projects/{self.project}/zones/{zone}/instances/{name}"

    def _bucket_link(self, name: str) -> str:
        return f"{API_ROOT}/projects/{self.project}/buckets/{name}"


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
