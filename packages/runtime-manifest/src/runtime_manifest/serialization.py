"""Strict canonical serialization for runtime manifests."""

from __future__ import annotations

import json

from .model import (
    Capability,
    Component,
    ManifestDecodeError,
    ManifestError,
    RuntimeManifest,
    Sha256Root,
    UnsupportedSchemaError,
)
from .model import Protocol as ProtocolRecord

MAX_DOCUMENT_UTF8_BYTES = 524_288


def _root_text(root: Sha256Root) -> str:
    return f"sha256:{root.value}"


def _root_from_text(value: object, field: str) -> Sha256Root:
    if type(value) is not str or not value.startswith("sha256:"):
        raise ManifestDecodeError(f"{field} must use the sha256:<hex> form")
    try:
        return Sha256Root(value.removeprefix("sha256:"))
    except ManifestError as error:
        raise ManifestDecodeError(f"{field} is invalid") from error


def _component_dict(component: Component) -> dict[str, object]:
    return {
        "content_root": _root_text(component.content_root),
        "name": component.name,
        "version": component.version,
    }


def _manifest_dict(manifest: RuntimeManifest) -> dict[str, object]:
    if type(manifest) is not RuntimeManifest:
        raise TypeError("manifest must be an exact RuntimeManifest")
    return {
        "capabilities": [
            {"name": capability.name, "version": capability.version}
            for capability in manifest.capabilities
        ],
        "component": _component_dict(manifest.component),
        "dependencies": [_component_dict(dependency) for dependency in manifest.dependencies],
        "protocols": [
            {
                "features": list(protocol.features),
                "name": protocol.name,
                "schema_root": _root_text(protocol.schema_root),
                "version": protocol.version,
            }
            for protocol in manifest.protocols
        ],
        "schema_version": manifest.schema_version,
    }


def canonical_json(manifest: RuntimeManifest) -> str:
    """Return sorted compact UTF-8 JSON text with one terminal LF."""

    return (
        json.dumps(
            _manifest_dict(manifest),
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestDecodeError(f"duplicate JSON field: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ManifestDecodeError(f"non-finite JSON number is prohibited: {value}")


def _exact_object(value: object, keys: set[str], field: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ManifestDecodeError(f"{field} must be an object")
    actual = set(value)
    if actual != keys:
        missing = sorted(keys - actual)
        extra = sorted(actual - keys)
        raise ManifestDecodeError(f"{field} fields disagree: missing={missing}, extra={extra}")
    return value


def _exact_array(value: object, field: str) -> list[object]:
    if type(value) is not list:
        raise ManifestDecodeError(f"{field} must be an array")
    return value


def _component_from_dict(value: object, field: str) -> Component:
    row = _exact_object(value, {"name", "version", "content_root"}, field)
    try:
        return Component(
            name=row["name"],
            version=row["version"],
            content_root=_root_from_text(row["content_root"], f"{field}.content_root"),
        )
    except ManifestError as error:
        raise ManifestDecodeError(f"{field} is invalid") from error


def parse_manifest(document: str | bytes) -> RuntimeManifest:
    """Decode one exact schema-v1 manifest and reject unknown fields."""

    if type(document) is bytes:
        if len(document) > MAX_DOCUMENT_UTF8_BYTES:
            raise ManifestDecodeError("manifest exceeds the UTF-8 byte limit")
        try:
            text = document.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ManifestDecodeError("manifest bytes must be UTF-8") from error
    elif type(document) is str:
        try:
            encoded = document.encode("utf-8")
        except UnicodeEncodeError as error:
            raise ManifestDecodeError(
                "manifest text must contain only Unicode scalar values"
            ) from error
        if len(encoded) > MAX_DOCUMENT_UTF8_BYTES:
            raise ManifestDecodeError("manifest exceeds the UTF-8 byte limit")
        text = document
    else:
        raise TypeError("document must be str or bytes")
    try:
        decoded = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except ManifestDecodeError:
        raise
    except (json.JSONDecodeError, RecursionError, TypeError, ValueError) as error:
        raise ManifestDecodeError("manifest is not strict JSON") from error
    root = _exact_object(
        decoded,
        {"schema_version", "component", "protocols", "capabilities", "dependencies"},
        "manifest",
    )
    if type(root["schema_version"]) is not int:
        raise ManifestDecodeError("schema_version must be an integer")
    if root["schema_version"] != 1:
        raise UnsupportedSchemaError("unsupported runtime-manifest schema version")
    protocols = []
    for index, value in enumerate(_exact_array(root["protocols"], "protocols")):
        field = f"protocols[{index}]"
        row = _exact_object(value, {"name", "version", "schema_root", "features"}, field)
        features = _exact_array(row["features"], f"{field}.features")
        try:
            protocols.append(
                ProtocolRecord(
                    name=row["name"],
                    version=row["version"],
                    schema_root=_root_from_text(row["schema_root"], f"{field}.schema_root"),
                    features=tuple(features),
                )
            )
        except ManifestError as error:
            raise ManifestDecodeError(f"{field} is invalid") from error
    capabilities = []
    for index, value in enumerate(_exact_array(root["capabilities"], "capabilities")):
        field = f"capabilities[{index}]"
        row = _exact_object(value, {"name", "version"}, field)
        try:
            capabilities.append(Capability(name=row["name"], version=row["version"]))
        except ManifestError as error:
            raise ManifestDecodeError(f"{field} is invalid") from error
    dependencies = tuple(
        _component_from_dict(value, f"dependencies[{index}]")
        for index, value in enumerate(_exact_array(root["dependencies"], "dependencies"))
    )
    try:
        return RuntimeManifest(
            component=_component_from_dict(root["component"], "component"),
            protocols=tuple(protocols),
            capabilities=tuple(capabilities),
            dependencies=dependencies,
            schema_version=root["schema_version"],
        )
    except UnsupportedSchemaError:
        raise
    except ManifestError as error:
        raise ManifestDecodeError("manifest values are invalid") from error
