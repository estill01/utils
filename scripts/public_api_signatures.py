#!/usr/bin/env python3
"""Record or check inspectable signatures without executing a Codex binary."""

from __future__ import annotations

import argparse
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import get_args, get_origin, get_type_hints

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPOSITORY_ROOT / "packages" / "codex-app-server-client"
PROTOCOL_ROOT = PACKAGE_ROOT / "protocol"
PROFILE_ROOTS = {
    "0.147.0": PROTOCOL_ROOT,
    "0.162.1": PROTOCOL_ROOT / "profiles" / "0.162.1",
    "0.156.1": PROTOCOL_ROOT / "profiles" / "0.156.1",
}


def annotation_name(annotation: object) -> str:
    # CPython 3.13 moved this public class to pathlib._local internally.
    # The public API contract must not depend on an interpreter's module layout.
    if annotation is Path:
        return "pathlib.Path"
    origin = get_origin(annotation)
    if origin is not None:
        return (
            annotation_name(origin)
            + "["
            + ", ".join(annotation_name(item) for item in get_args(annotation))
            + "]"
        )
    if isinstance(annotation, type):
        return f"{annotation.__module__}.{annotation.__qualname__}"
    return repr(annotation)


def describe_signature(value: object) -> dict[str, object]:
    signature = inspect.signature(value)
    if isinstance(value, type):
        module = importlib.import_module(value.__module__)
        hints = get_type_hints(value.__init__, globalns=vars(module), localns=vars(module))
    else:
        hints = get_type_hints(value)
    return {
        "signature": str(signature),
        "async": inspect.iscoroutinefunction(value),
        "async_generator": inspect.isasyncgenfunction(value),
        "resolved_annotations": {
            name: annotation_name(annotation) for name, annotation in sorted(hints.items())
        },
    }


def snapshot(api: dict[str, object]) -> dict[str, object]:
    sys.path.insert(0, str(PACKAGE_ROOT / "src"))
    module = importlib.import_module(api["root_module"])
    if sorted(module.__all__) != sorted(api["root_exports"]):
        raise RuntimeError("runtime public exports differ from the frozen API map")
    result: dict[str, object] = {
        "schema_version": 1,
        "root_module": api["root_module"],
        "root_exports": sorted(module.__all__),
        "callables": {},
        "properties": {},
        "capability_enums": {},
    }
    callables = result["callables"]
    for name in api["compatibility_functions"]:
        callables[name] = describe_signature(getattr(module, name))
    for dotted in api["lifecycle"]:
        owner, name = dotted.split(".", 1)
        value = getattr(getattr(module, owner), name)
        if isinstance(value, property):
            result["properties"][dotted] = describe_signature(value.fget)
        else:
            callables[dotted] = describe_signature(value)
    for name in api["session_operations"]:
        callables[f"AppServerSession.{name}"] = describe_signature(
            getattr(module.AppServerSession, name)
        )
    constructors = set(api["configuration_models"]) | set(api["schema_models"])
    constructors.update(api["notification_models"].values())
    constructors.update(("StdioTransport", "UnixSocketTransport", "InjectedTransport"))
    if "LocalWebSocketTransport" in api["root_exports"]:
        constructors.add("LocalWebSocketTransport")
    constructors.discard("BackoffHook")
    for callback in api["callback_models"].values():
        constructors.update((callback["params"], callback["response"]))
        name = callback["callback"]
        callables[f"{name}.respond"] = describe_signature(getattr(module, name).respond)
    for name in sorted(constructors):
        callables[name] = describe_signature(getattr(module, name))
    for name in api["capability_enums"]:
        result["capability_enums"][name] = {item.name: item.value for item in getattr(module, name)}
    return result


def check_signatures(profile_root: Path, api: dict[str, object]) -> None:
    path = profile_root / "public-api-signatures.json"
    recorded = json.loads(path.read_text(encoding="utf-8"))
    if snapshot(api) != recorded:
        raise RuntimeError(f"runtime public API signatures differ from frozen {api['root_module']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=(*PROFILE_ROOTS, "all"), default="all")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    for version, root in PROFILE_ROOTS.items():
        if args.profile not in (version, "all"):
            continue
        api = json.loads((root / "public-api.json").read_text(encoding="utf-8"))
        if args.write:
            (root / "public-api-signatures.json").write_text(
                json.dumps(snapshot(api), indent=2, sort_keys=True) + "\n", encoding="utf-8"
            )
        else:
            check_signatures(root, api)
        print(f"{version} public signatures {'recorded' if args.write else 'verified'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
