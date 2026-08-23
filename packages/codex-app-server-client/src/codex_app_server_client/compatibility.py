"""Exact Codex binary and app-server schema compatibility."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any

from .errors import (
    AmbiguousCodexBinaryError,
    CodexBinaryNotFoundError,
    CodexVersionError,
    SchemaMalformedError,
    SchemaMissingError,
    SchemaRootMismatchError,
    UnsupportedFeatureError,
)
from .surface import (
    CallbackCapability,
    FeatureSet,
    NotificationCapability,
    RequestCapability,
    TransportCapability,
)

_VERSION_PATTERN = re.compile(r"codex-cli (?P<version>\d+\.\d+\.\d+)(?:\s+.*)?")
_PROBE_TIMEOUT_SECONDS = 10.0
_GENERATION_TIMEOUT_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class ProtocolTarget:
    codex_version: str
    source_commit: str
    schema_tree_root_sha256: str
    selected_surface_root_sha256: str


@dataclass(frozen=True, slots=True)
class BinaryIdentity:
    path: Path
    reported_version: str
    sha256: str


@dataclass(frozen=True, slots=True)
class CompatibilityResult:
    target: ProtocolTarget
    binary: BinaryIdentity
    semantic_schema_root_sha256: str
    features: FeatureSet


PINNED_PROTOCOL = ProtocolTarget(
    codex_version="0.147.0",
    source_commit="be6e8eac029b183056b7e4402879f15d2c85f61b",
    schema_tree_root_sha256=("eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa"),
    selected_surface_root_sha256=(
        "9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f"
    ),
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _path_candidates(name: str) -> list[Path]:
    suffixes = [""]
    if os.name == "nt":
        suffixes.extend(filter(None, os.environ.get("PATHEXT", "").split(os.pathsep)))
    candidates: dict[Path, Path] = {}
    for directory in os.environ.get("PATH", "").split(os.pathsep):
        base = Path(directory or os.curdir)
        for suffix in suffixes:
            candidate = base / f"{name}{suffix}"
            if candidate.is_file() and os.access(candidate, os.X_OK):
                resolved = candidate.resolve()
                candidates.setdefault(resolved, candidate)
    return sorted(candidates)


def _resolve_path(executable: str | os.PathLike[str] | None) -> Path:
    if executable is not None:
        supplied = Path(executable)
        if supplied.is_absolute() or supplied.parent != Path("."):
            try:
                resolved = supplied.resolve(strict=True)
            except FileNotFoundError as error:
                raise CodexBinaryNotFoundError(f"Codex executable not found: {supplied}") from error
            if not resolved.is_file() or not os.access(resolved, os.X_OK):
                raise CodexBinaryNotFoundError(
                    f"Codex executable is not an executable file: {resolved}"
                )
            return resolved
        name = str(supplied)
    else:
        name = "codex"

    candidates = _path_candidates(name)
    if not candidates:
        raise CodexBinaryNotFoundError(f"Codex executable {name!r} was not found on PATH")
    if len(candidates) > 1:
        joined = ", ".join(str(candidate) for candidate in candidates)
        raise AmbiguousCodexBinaryError(f"Codex executable {name!r} is ambiguous on PATH: {joined}")
    return candidates[0]


def resolve_codex_binary(
    executable: str | os.PathLike[str] | None = None,
) -> BinaryIdentity:
    """Resolve one exact executable and probe its reported Codex version."""

    path = _resolve_path(executable)
    try:
        completed = subprocess.run(
            [str(path), "--version"],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=_PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise CodexVersionError(f"Codex version probe failed for {path}") from error
    output = completed.stdout.strip()
    match = _VERSION_PATTERN.fullmatch(output)
    if completed.returncode != 0 or match is None:
        raise CodexVersionError(
            f"Codex version probe returned an invalid result for {path}: {output!r}"
        )
    return BinaryIdentity(
        path=path,
        reported_version=match.group("version"),
        sha256=_sha256(path.read_bytes()),
    )


def _walk_files(root: Traversable, prefix: str = "") -> list[tuple[str, Traversable]]:
    files: list[tuple[str, Traversable]] = []
    try:
        children = sorted(root.iterdir(), key=lambda child: child.name)
    except (FileNotFoundError, NotADirectoryError) as error:
        raise SchemaMissingError(f"schema root is missing: {root}") from error
    for child in children:
        relative = f"{prefix}/{child.name}" if prefix else child.name
        if child.is_dir():
            files.extend(_walk_files(child, relative))
        elif child.is_file():
            files.append((relative, child))
    return files


def _load_json(file: Traversable, label: str) -> Any:
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise SchemaMissingError(f"required schema is missing: {label}") from error
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SchemaMalformedError(f"schema is malformed: {label}") from error


def _tree_roots(root: Traversable) -> tuple[str, str, int, int]:
    byte_lines: list[str] = []
    semantic_lines: list[str] = []
    total_bytes = 0
    files = _walk_files(root)
    if not files:
        raise SchemaMissingError(f"schema root is empty: {root}")
    for relative, file in files:
        try:
            data = file.read_bytes()
            document = json.loads(data)
        except FileNotFoundError as error:
            raise SchemaMissingError(f"required schema is missing: {relative}") from error
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise SchemaMalformedError(f"schema is malformed: {relative}") from error
        canonical = json.dumps(
            document,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        byte_lines.append(f"{_sha256(data)}  {relative}\n")
        semantic_lines.append(f"{_sha256(canonical)}  {relative}\n")
        total_bytes += len(data)
    return (
        _sha256("".join(byte_lines).encode()),
        _sha256("".join(semantic_lines).encode()),
        len(files),
        total_bytes,
    )


def _methods(document: dict[str, Any], *, definition: str | None = None) -> set[str]:
    if definition is not None:
        try:
            document = document["definitions"][definition]
        except (KeyError, TypeError) as error:
            raise SchemaMalformedError(f"missing schema definition: {definition}") from error
    try:
        variants = document["oneOf"]
        return {
            method for variant in variants for method in variant["properties"]["method"]["enum"]
        }
    except (KeyError, TypeError) as error:
        raise SchemaMalformedError("method union has an invalid structure") from error


def _required_features(protocol_root: Traversable, schema_root: Traversable) -> FeatureSet:
    surface = _load_json(protocol_root.joinpath("supported-surface.json"), "supported surface")
    aggregate = _load_json(
        schema_root.joinpath("codex_app_server_protocol.v2.schemas.json"),
        "v2 aggregate",
    )
    server_requests = _load_json(schema_root.joinpath("ServerRequest.json"), "server requests")
    client_notifications = _load_json(
        schema_root.joinpath("ClientNotification.json"), "client notifications"
    )
    available = {
        "requests": _methods(aggregate, definition="ClientRequest"),
        "notifications": _methods(aggregate, definition="ServerNotification"),
        "callbacks": _methods(server_requests),
        "client_notifications": _methods(client_notifications),
    }
    selected = {
        "requests": set(surface["client_requests"]["public_typed"])
        | set(surface["client_requests"]["internal"]),
        "notifications": set(surface["server_notifications"]["public_typed"]),
        "callbacks": set(surface["server_requests"]["public_policy_neutral"]),
        "client_notifications": set(surface["client_notifications"]["internal"]),
    }
    for family, methods in selected.items():
        missing = methods - available[family]
        if missing:
            raise UnsupportedFeatureError(
                f"selected {family} are missing from the schema: {sorted(missing)}"
            )
    return FeatureSet(
        requests=frozenset(
            RequestCapability(value) for value in surface["client_requests"]["public_typed"]
        ),
        notifications=frozenset(
            NotificationCapability(value)
            for value in surface["server_notifications"]["public_typed"]
        ),
        callbacks=frozenset(
            CallbackCapability(value)
            for value in surface["server_requests"]["public_policy_neutral"]
        ),
        transports=frozenset(
            TransportCapability(value) for value in surface["transports"]["supported"]
        ),
    )


def _packaged_protocol_root() -> Traversable:
    packaged = resources.files("codex_app_server_client").joinpath("_protocol")
    if packaged.joinpath("compatibility.json").is_file():
        return packaged
    development = Path(__file__).resolve().parents[2] / "protocol"
    if development.joinpath("compatibility.json").is_file():
        return development
    return packaged


def inspect_compatibility(
    binary: BinaryIdentity,
    target: ProtocolTarget = PINNED_PROTOCOL,
    *,
    schema_dir: str | os.PathLike[str] | None = None,
) -> CompatibilityResult:
    """Validate exact version, schema roots, and the closed selected surface."""

    if binary.reported_version != target.codex_version:
        raise CodexVersionError(
            f"expected Codex {target.codex_version}, got {binary.reported_version}"
        )
    if target != PINNED_PROTOCOL:
        raise SchemaRootMismatchError("protocol target differs from the frozen package target")

    protocol_root = _packaged_protocol_root()
    compatibility = _load_json(
        protocol_root.joinpath("compatibility.json"), "compatibility metadata"
    )
    if compatibility["schema_tree_root_sha256"] != target.schema_tree_root_sha256:
        raise SchemaRootMismatchError("packaged byte-tree target differs from ProtocolTarget")
    if compatibility["selected_surface_root_sha256"] != target.selected_surface_root_sha256:
        raise SchemaRootMismatchError("packaged selected surface differs from ProtocolTarget")

    external = schema_dir is not None
    schema_root: Traversable
    if external:
        path = Path(schema_dir)
        if not path.is_dir():
            raise SchemaMissingError(f"schema root is missing: {path}")
        schema_root = path
    else:
        schema_root = protocol_root.joinpath("upstream", target.codex_version)
    byte_root, semantic_root, file_count, total_bytes = _tree_roots(schema_root)
    if not external and byte_root != target.schema_tree_root_sha256:
        raise SchemaRootMismatchError(
            "retained schema byte root changed: "
            f"expected {target.schema_tree_root_sha256}, got {byte_root}"
        )
    if semantic_root != compatibility["semantic_schema_root_sha256"]:
        raise SchemaRootMismatchError(
            "schema semantic root changed: "
            f"expected {compatibility['semantic_schema_root_sha256']}, got {semantic_root}"
        )
    if file_count != compatibility["schema_file_count"]:
        raise SchemaRootMismatchError("schema file count changed")
    if not external and total_bytes != compatibility["schema_total_bytes"]:
        raise SchemaRootMismatchError("retained schema byte count changed")
    features = _required_features(protocol_root, schema_root)
    return CompatibilityResult(
        target=target,
        binary=binary,
        semantic_schema_root_sha256=semantic_root,
        features=features,
    )


def _generate_schema_tree(binary: BinaryIdentity, output_dir: Path) -> None:
    """Generate a non-experimental schema tree without starting app-server."""

    if binary.reported_version != PINNED_PROTOCOL.codex_version:
        raise CodexVersionError(
            f"expected Codex {PINNED_PROTOCOL.codex_version}, got {binary.reported_version}"
        )
    if output_dir.exists() and any(output_dir.iterdir()):
        raise SchemaRootMismatchError(f"schema output directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run(
            [
                str(binary.path),
                "app-server",
                "generate-json-schema",
                "--out",
                str(output_dir),
            ],
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=_GENERATION_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise SchemaMissingError("official schema generation failed") from error
    if completed.returncode != 0:
        raise SchemaMissingError(
            f"official schema generation failed with exit {completed.returncode}: "
            f"{completed.stdout.strip()}"
        )
    _tree_roots(output_dir)
