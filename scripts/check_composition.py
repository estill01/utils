#!/usr/bin/env python3
"""Build the frozen wheels together and run the neutral installed composition."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

import check_package

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPOSITORY_ROOT / "tools" / "composition_matrix.json"
FIXTURE_PATH = REPOSITORY_ROOT / "tests" / "neutral_composition.py"
PACKAGE_MODULES = {
    "codex_app_server_client",
    "embedded_service_contract",
    "embedded_service_contract.testing",
    "runtime_manifest",
}
PUBLIC_MODULE_ATTRIBUTES = {
    "codex_app_server_client": {
        "AppServerClient",
        "BinaryIdentity",
        "ClientIdentity",
        "InjectedTransport",
        "PINNED_PROTOCOL",
        "ThreadListParams",
        "TransportOwnership",
        "__all__",
        "__name__",
        "__version__",
        "inspect_compatibility",
    },
    "embedded_service_contract": {
        "HostShape",
        "__all__",
        "__name__",
        "__version__",
        "assert_lifecycle_conformance",
    },
    "embedded_service_contract.testing": {
        "__all__",
        "__name__",
        "embedded_fixture",
        "service_fixture",
    },
    "runtime_manifest": {
        "Capability",
        "Component",
        "Protocol",
        "RuntimeManifest",
        "Sha256Root",
        "UnavailableKind",
        "__all__",
        "__name__",
        "__version__",
        "canonical_json",
        "compare_manifests",
        "parse_manifest",
    },
}
RESULT_KEYS = {
    "client",
    "incompatible_root_kinds",
    "lifecycle",
    "manifest_compatible",
    "manifest_sha256",
    "packages",
    "protocol",
    "public_modules",
    "schema_version",
}


def require_exact_sha256(value: object, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise RuntimeError(f"{label} must be an exact lowercase SHA-256 value")
    return value


def load_contract(packages: dict[str, dict[str, object]]) -> dict[str, object]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    validate_contract(contract, packages)
    return contract


def validate_contract(
    contract: object,
    packages: dict[str, dict[str, object]],
) -> None:
    if type(contract) is not dict or set(contract) != {"schema_version", "packages", "protocol"}:
        raise RuntimeError("composition contract has an unexpected top-level shape")
    if contract["schema_version"] != 1:
        raise RuntimeError("composition contract has an unsupported schema version")
    records = contract["packages"]
    if type(records) is not dict or set(records) != set(packages):
        raise RuntimeError("composition contract package set is not exact")
    for distribution, package in packages.items():
        record = records[distribution]
        if type(record) is not dict or set(record) != {
            "version",
            "wheel_sha256",
            "wheel_content_root_sha256",
        }:
            raise RuntimeError(f"composition contract package record is not exact: {distribution}")
        if record["version"] != package["version"]:
            raise RuntimeError(f"composition contract version differs: {distribution}")
        require_exact_sha256(record["wheel_sha256"], f"{distribution} wheel")
        require_exact_sha256(record["wheel_content_root_sha256"], f"{distribution} content root")
    protocol = contract["protocol"]
    if type(protocol) is not dict or set(protocol) != {
        "version",
        "schema_root_sha256",
        "selected_surface_root_sha256",
    }:
        raise RuntimeError("composition contract protocol record is not exact")
    if type(protocol["version"]) is not str or not protocol["version"]:
        raise RuntimeError("composition contract protocol version is invalid")
    require_exact_sha256(protocol["schema_root_sha256"], "protocol schema root")
    require_exact_sha256(protocol["selected_surface_root_sha256"], "protocol surface root")


def validate_fixture_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported_package_modules: set[str] = set()
    package_aliases: dict[str, str] = {}
    for node in ast.walk(tree):
        module: str | None = None
        if isinstance(node, ast.Import):
            for alias in node.names:
                candidate = alias.name
                root = candidate.partition(".")[0]
                if root in {name.partition(".")[0] for name in PACKAGE_MODULES}:
                    if candidate not in PACKAGE_MODULES:
                        raise RuntimeError(
                            f"composition fixture imports a private module: {candidate}"
                        )
                    imported_package_modules.add(candidate)
                    package_aliases[alias.asname or candidate.partition(".")[0]] = candidate
                elif root not in __import__("sys").stdlib_module_names:
                    raise RuntimeError(
                        f"composition fixture imports an external module: {candidate}"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise RuntimeError("composition fixture uses a relative import")
            module = node.module
            if module is None:
                raise RuntimeError("composition fixture has an unbound import")
            root = module.partition(".")[0]
            if root in {name.partition(".")[0] for name in PACKAGE_MODULES}:
                raise RuntimeError(
                    "composition fixture must import public package modules, not attributes: "
                    f"{module}"
                )
            elif root not in __import__("sys").stdlib_module_names:
                raise RuntimeError(f"composition fixture imports an external module: {module}")
    if imported_package_modules != PACKAGE_MODULES:
        raise RuntimeError(
            "composition fixture does not reach the exact installed public module set: "
            f"{sorted(imported_package_modules)}"
        )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            continue
        module = package_aliases.get(node.value.id)
        if module is None:
            continue
        if node.attr not in PUBLIC_MODULE_ATTRIBUTES[module]:
            raise RuntimeError(
                f"composition fixture reaches a non-public package attribute: {module}.{node.attr}"
            )


def verify_artifact(
    distribution: str,
    *,
    wheel_sha256: str,
    content_root_sha256: str,
    expected: dict[str, object],
) -> None:
    if wheel_sha256 != expected["wheel_sha256"]:
        raise RuntimeError(f"combined wheel bytes differ from Block 12: {distribution}")
    if content_root_sha256 != expected["wheel_content_root_sha256"]:
        raise RuntimeError(f"combined wheel content root differs from Block 12: {distribution}")


def validate_result(
    result: object,
    contract: dict[str, object],
) -> None:
    if type(result) is not dict or set(result) != RESULT_KEYS:
        raise RuntimeError("neutral composition result has an unexpected shape")
    records = contract["packages"]
    assert isinstance(records, dict)
    if result["schema_version"] != 1:
        raise RuntimeError("neutral composition result schema version differs")
    if result["packages"] != {name: record["version"] for name, record in records.items()}:
        raise RuntimeError("neutral composition result package versions differ")
    if result["protocol"] != contract["protocol"]:
        raise RuntimeError("neutral composition result protocol roots differ")
    if result["public_modules"] != sorted(PACKAGE_MODULES):
        raise RuntimeError("neutral composition did not reach the exact public module set")
    if result["manifest_compatible"] is not True:
        raise RuntimeError("neutral composition manifest did not compare compatible")
    require_exact_sha256(result["manifest_sha256"], "composition manifest")
    if set(result["incompatible_root_kinds"]) != {"dependency-root", "protocol-schema"}:
        raise RuntimeError("neutral composition root diagnostics differ")
    if result["client"] != {
        "channel_close_count": 1,
        "generation": 1,
        "listed_threads": 0,
        "transport": "injected-byte-channel",
    }:
        raise RuntimeError("neutral app-server client result differs")
    if result["lifecycle"] != {
        "embedded": {"events": 6, "scenarios": 3, "shape": "embedded"},
        "process_owner_count": 1,
        "service": {"events": 6, "scenarios": 3, "shape": "service"},
    }:
        raise RuntimeError("neutral lifecycle composition result differs")


def build_wheels(
    *,
    temporary_root: Path,
    packages: dict[str, dict[str, object]],
    package_roots: dict[str, Path],
    contract: dict[str, object],
    python_spec: str,
    uv: str,
) -> tuple[list[Path], dict[str, dict[str, object]]]:
    contract_packages = contract["packages"]
    assert isinstance(contract_packages, dict)
    wheels: list[Path] = []
    records: dict[str, dict[str, object]] = {}
    for distribution in sorted(packages):
        build_root = temporary_root / "build" / distribution
        dist_dir = temporary_root / "dist" / distribution
        check_package.copy_package_snapshot(package_roots[distribution], build_root)
        snapshot = check_package.package_snapshot_record(build_root)
        check_package.run(
            [
                uv,
                "build",
                "--wheel",
                "--out-dir",
                str(dist_dir),
                "--no-create-gitignore",
                "--python",
                python_spec,
                str(build_root),
            ],
            cwd=temporary_root,
        )
        check_package.verify_snapshot_unchanged(build_root, snapshot, label=distribution)
        built = sorted(dist_dir.glob("*.whl"))
        if len(built) != 1:
            raise RuntimeError(f"combined build expected one wheel: {distribution}")
        wheel = built[0]
        wheel_sha256 = hashlib.sha256(wheel.read_bytes()).hexdigest()
        with zipfile.ZipFile(wheel) as archive:
            members = check_package.validated_wheel_member_names(archive)
            name, version, python_requires, requirements = check_package.wheel_metadata(archive)
            package = packages[distribution]
            if (
                name != distribution
                or version != package["version"]
                or python_requires != ">=3.11"
                or requirements != package["runtime_dependencies"]
            ):
                raise RuntimeError(f"combined wheel metadata differs: {distribution}")
            check_package.audit_wheel_layout(
                members,
                distribution=distribution,
                import_root=str(package["import"]),
                version=version,
            )
            content_root, member_count, uncompressed_bytes = check_package.wheel_content_record(
                archive
            )
        expected = contract_packages[distribution]
        assert isinstance(expected, dict)
        verify_artifact(
            distribution,
            wheel_sha256=wheel_sha256,
            content_root_sha256=content_root,
            expected=expected,
        )
        wheels.append(wheel)
        records[distribution] = {
            "content_root_sha256": content_root,
            "members": member_count,
            "uncompressed_bytes": uncompressed_bytes,
            "version": version,
            "wheel": wheel.name,
            "wheel_sha256": wheel_sha256,
        }
    return wheels, records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python", default="3.11", dest="python_spec")
    args = parser.parse_args()
    uv = check_package.require_uv()
    matrix = check_package.load_matrix()
    packages = check_package.package_records(matrix)
    package_roots = check_package.validate_package_paths(packages)
    check_package.audit_dependency_graph(packages, package_roots)
    contract = load_contract(packages)
    validate_fixture_imports(FIXTURE_PATH)

    with tempfile.TemporaryDirectory(prefix="utils-neutral-composition-") as temporary:
        temporary_root = Path(temporary)
        wheels, wheel_records = build_wheels(
            temporary_root=temporary_root,
            packages=packages,
            package_roots=package_roots,
            contract=contract,
            python_spec=args.python_spec,
            uv=uv,
        )
        environment = temporary_root / "venv"
        check_package.run(
            [uv, "venv", "--no-project", "--python", args.python_spec, str(environment)],
            cwd=temporary_root,
        )
        interpreter = check_package.environment_python(environment)
        check_package.run(
            [
                uv,
                "pip",
                "install",
                "--python",
                str(interpreter),
                "--no-deps",
                "--offline",
                *(str(wheel) for wheel in wheels),
            ],
            cwd=temporary_root,
        )
        fixture_input = temporary_root / "composition-input.json"
        package_contract = contract["packages"]
        assert isinstance(package_contract, dict)
        fixture_input.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "packages": {
                        name: {
                            "version": record["version"],
                            "wheel_content_root_sha256": record["wheel_content_root_sha256"],
                        }
                        for name, record in package_contract.items()
                    },
                    "protocol": contract["protocol"],
                },
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        completed = check_package.run(
            [str(interpreter), "-I", str(FIXTURE_PATH), str(fixture_input)],
            cwd=temporary_root,
        )
        result = json.loads(completed.stdout)
        validate_result(result, contract)
    print(
        json.dumps(
            {
                "composition": result,
                "python": args.python_spec,
                "wheels": wheel_records,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
