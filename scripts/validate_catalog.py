from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
CHANNELS = ("stable", "beta")
COMPONENT_ID = re.compile(r"^[a-z][a-z0-9-]{1,31}$")
SEMANTIC_VERSION = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
SHA256 = re.compile(r"^[a-f0-9]{64}$")
REQUIRED_CATALOG_FIELDS = {
    "schemaVersion",
    "product",
    "channel",
    "revision",
    "generatedAt",
    "components",
    "signature",
}
REQUIRED_COMPONENT_FIELDS = {
    "version",
    "packageUrl",
    "packageSize",
    "packageSha256",
    "minimumUpdaterVersion",
    "mandatory",
}
OPTIONAL_COMPONENT_FIELDS = {"releaseNotesUrl", "requires"}


class CatalogError(ValueError):
    pass


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise CatalogError(f"missing file: {path.relative_to(ROOT)}") from error
    except json.JSONDecodeError as error:
        raise CatalogError(
            f"invalid JSON in {path.relative_to(ROOT)}:{error.lineno}:{error.colno}: {error.msg}"
        ) from error


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CatalogError(message)


def validate_timestamp(value: Any, context: str) -> None:
    require(isinstance(value, str), f"{context} must be a string")
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise CatalogError(f"{context} must be an ISO-8601 timestamp") from error
    require(timestamp.utcoffset() is not None, f"{context} must include a timezone")


def validate_component(component_id: str, component: Any) -> None:
    context = f"component {component_id!r}"
    require(COMPONENT_ID.fullmatch(component_id) is not None, f"invalid {context} ID")
    require(isinstance(component, dict), f"{context} must be an object")

    missing = REQUIRED_COMPONENT_FIELDS - component.keys()
    require(not missing, f"{context} is missing fields: {', '.join(sorted(missing))}")
    unexpected = component.keys() - REQUIRED_COMPONENT_FIELDS - OPTIONAL_COMPONENT_FIELDS
    require(not unexpected, f"{context} has unexpected fields: {', '.join(sorted(unexpected))}")

    require(
        isinstance(component["version"], str)
        and SEMANTIC_VERSION.fullmatch(component["version"]) is not None,
        f"{context}.version is not semantic versioning",
    )
    require(
        isinstance(component["minimumUpdaterVersion"], str)
        and SEMANTIC_VERSION.fullmatch(component["minimumUpdaterVersion"]) is not None,
        f"{context}.minimumUpdaterVersion is not semantic versioning",
    )
    require(
        isinstance(component["packageUrl"], str)
        and component["packageUrl"].startswith("https://"),
        f"{context}.packageUrl must use HTTPS",
    )
    require(
        isinstance(component["packageSize"], int)
        and not isinstance(component["packageSize"], bool)
        and component["packageSize"] > 0,
        f"{context}.packageSize must be a positive integer",
    )
    require(
        isinstance(component["packageSha256"], str)
        and SHA256.fullmatch(component["packageSha256"]) is not None,
        f"{context}.packageSha256 must be 64 lowercase hexadecimal characters",
    )
    require(isinstance(component["mandatory"], bool), f"{context}.mandatory must be boolean")

    if "releaseNotesUrl" in component:
        require(
            isinstance(component["releaseNotesUrl"], str)
            and component["releaseNotesUrl"].startswith("https://"),
            f"{context}.releaseNotesUrl must use HTTPS",
        )

    requires = component.get("requires", {})
    require(isinstance(requires, dict), f"{context}.requires must be an object")
    for dependency_id, constraint in requires.items():
        require(
            COMPONENT_ID.fullmatch(dependency_id) is not None,
            f"{context} has invalid dependency ID {dependency_id!r}",
        )
        require(
            isinstance(constraint, str) and bool(constraint.strip()),
            f"{context}.requires[{dependency_id!r}] must be a non-empty string",
        )


def validate_catalog(channel: str) -> None:
    path = ROOT / "updates" / channel / "catalog.json"
    catalog = read_json(path)
    context = str(path.relative_to(ROOT))

    require(isinstance(catalog, dict), f"{context} must contain an object")
    missing = REQUIRED_CATALOG_FIELDS - catalog.keys()
    require(not missing, f"{context} is missing fields: {', '.join(sorted(missing))}")
    unexpected = catalog.keys() - REQUIRED_CATALOG_FIELDS
    require(not unexpected, f"{context} has unexpected fields: {', '.join(sorted(unexpected))}")
    require(catalog["schemaVersion"] == 1, f"{context}.schemaVersion must be 1")
    require(catalog["product"] == "twk-macro-hub", f"{context}.product is invalid")
    require(catalog["channel"] == channel, f"{context}.channel must be {channel!r}")
    require(
        isinstance(catalog["revision"], int)
        and not isinstance(catalog["revision"], bool)
        and catalog["revision"] >= 0,
        f"{context}.revision must be a non-negative integer",
    )
    validate_timestamp(catalog["generatedAt"], f"{context}.generatedAt")

    components = catalog["components"]
    require(isinstance(components, dict), f"{context}.components must be an object")
    for component_id, component in components.items():
        validate_component(component_id, component)

    signature = catalog["signature"]
    require(signature is None or isinstance(signature, str), f"{context}.signature is invalid")
    require(
        not components or isinstance(signature, str) and bool(signature.strip()),
        f"{context} must be signed before it advertises components",
    )

    print(f"validated {context} ({len(components)} components)")


def main() -> int:
    try:
        schema = read_json(ROOT / "schema" / "catalog.schema.json")
        require(isinstance(schema, dict), "schema/catalog.schema.json must contain an object")
        for channel in CHANNELS:
            validate_catalog(channel)
    except CatalogError as error:
        print(f"catalog validation failed: {error}", file=sys.stderr)
        return 1

    print("catalog validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
