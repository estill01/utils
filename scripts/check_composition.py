#!/usr/bin/env python3
"""Build the frozen wheels together and run the neutral installed composition."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import subprocess
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
PACKAGE_IMPORT_ALIASES = {
    "codex_app_server_client": "client_api",
    "embedded_service_contract": "lifecycle_api",
    "embedded_service_contract.testing": "lifecycle_testing",
    "runtime_manifest": "manifest_api",
}
EXPECTED_IMPORT_STATEMENTS = (
    "from __future__ import annotations",
    "import asyncio",
    "import hashlib",
    "import json",
    "import sys",
    "from pathlib import Path",
    "import codex_app_server_client as client_api",
    "import embedded_service_contract as lifecycle_api",
    "import embedded_service_contract.testing as lifecycle_testing",
    "import runtime_manifest as manifest_api",
)
FORBIDDEN_DYNAMIC_IMPORT_ROOTS = {"importlib", "pkgutil"}
FORBIDDEN_REFLECTION_CALLS = {
    "compile",
    "delattr",
    "dir",
    "eval",
    "exec",
    "getattr",
    "hasattr",
    "setattr",
    "vars",
}
ALLOWED_STDLIB_MODULES = {"__future__", "asyncio", "hashlib", "json", "pathlib", "sys"}
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
    "incompatible_root_diagnostics",
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


def canonical_manifest_document(contract: dict[str, object]) -> str:
    records = contract["packages"]
    protocol = contract["protocol"]
    assert isinstance(records, dict)
    assert isinstance(protocol, dict)

    def component(name: str) -> dict[str, str]:
        record = records[name]
        assert isinstance(record, dict)
        return {
            "content_root": f"sha256:{record['wheel_content_root_sha256']}",
            "name": name,
            "version": str(record["version"]),
        }

    document = {
        "capabilities": [
            {"name": "embedded-lifecycle", "version": "1"},
            {"name": "injected-byte-channel", "version": "1"},
            {"name": "service-lifecycle", "version": "1"},
        ],
        "component": component("codex-app-server-client"),
        "dependencies": [
            component("embedded-service-contract"),
            component("runtime-manifest"),
        ],
        "protocols": [
            {
                "features": [],
                "name": "codex-app-server-schema",
                "schema_root": f"sha256:{protocol['schema_root_sha256']}",
                "version": str(protocol["version"]),
            },
            {
                "features": ["typed-session"],
                "name": "codex-app-server-surface",
                "schema_root": f"sha256:{protocol['selected_surface_root_sha256']}",
                "version": str(protocol["version"]),
            },
        ],
        "schema_version": 1,
    }
    return (
        json.dumps(
            document,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    )


def canonical_manifest_sha256(contract: dict[str, object]) -> str:
    return hashlib.sha256(canonical_manifest_document(contract).encode()).hexdigest()


def validate_contract(
    contract: object,
    packages: dict[str, dict[str, object]],
) -> None:
    if type(contract) is not dict or set(contract) != {
        "schema_version",
        "fixture_sha256",
        "manifest_sha256",
        "packages",
        "protocol",
    }:
        raise RuntimeError("composition contract has an unexpected top-level shape")
    if type(contract["schema_version"]) is not int or contract["schema_version"] != 1:
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
    require_exact_sha256(contract["fixture_sha256"], "neutral composition fixture")
    fixture_sha256 = hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
    if contract["fixture_sha256"] != fixture_sha256:
        raise RuntimeError("neutral composition fixture source differs")
    require_exact_sha256(contract["manifest_sha256"], "canonical manifest")
    if contract["manifest_sha256"] != canonical_manifest_sha256(contract):
        raise RuntimeError("composition contract canonical manifest shape differs")


def validate_fixture_imports(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
    import_nodes = [
        node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    if any(not isinstance(parents.get(node), ast.Module) for node in import_nodes):
        raise RuntimeError("composition fixture contains a non-top-level import")
    observed_imports = tuple(
        ast.unparse(node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
    )
    if observed_imports != EXPECTED_IMPORT_STATEMENTS or len(import_nodes) != len(
        EXPECTED_IMPORT_STATEMENTS
    ):
        raise RuntimeError("composition fixture import statements or aliases differ")
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
                elif root in FORBIDDEN_DYNAMIC_IMPORT_ROOTS:
                    raise RuntimeError(
                        f"composition fixture imports a dynamic import facility: {candidate}"
                    )
                elif root not in ALLOWED_STDLIB_MODULES:
                    raise RuntimeError(
                        f"composition fixture imports a non-admitted module: {candidate}"
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
            elif root not in ALLOWED_STDLIB_MODULES:
                raise RuntimeError(f"composition fixture imports a non-admitted module: {module}")
    if imported_package_modules != PACKAGE_MODULES:
        raise RuntimeError(
            "composition fixture does not reach the exact installed public module set: "
            f"{sorted(imported_package_modules)}"
        )
    if package_aliases != {alias: module for module, alias in PACKAGE_IMPORT_ALIASES.items()}:
        raise RuntimeError("composition fixture package import aliases differ")
    observed_attributes: dict[str, set[str]] = {module: set() for module in PACKAGE_MODULES}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            continue
        module = package_aliases.get(node.value.id)
        if module is None:
            continue
        parent = parents.get(node)
        if isinstance(parent, ast.Attribute) and parent.value is node:
            raise RuntimeError("composition fixture nests access from a package module")
        if node.attr not in PUBLIC_MODULE_ATTRIBUTES[module]:
            raise RuntimeError(
                f"composition fixture reaches a non-public package attribute: {module}.{node.attr}"
            )
        observed_attributes[module].add(node.attr)
    if observed_attributes != PUBLIC_MODULE_ATTRIBUTES:
        raise RuntimeError("composition fixture does not reach the exact public attribute set")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Name) or node.id not in package_aliases:
            continue
        parent = parents.get(node)
        if not (
            isinstance(parent, ast.Attribute)
            and parent.value is node
            and parent.attr in PUBLIC_MODULE_ATTRIBUTES[package_aliases[node.id]]
        ):
            raise RuntimeError("composition fixture lets a package module object escape")
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "__import__":
            raise RuntimeError("composition fixture uses dynamic package import")
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_REFLECTION_CALLS:
            raise RuntimeError("composition fixture uses dynamic evaluation or reflection")
        if isinstance(node.func, ast.Name) and node.func.id in {"globals", "locals"}:
            raise RuntimeError("composition fixture uses dynamic namespace access")
        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "importlib"
        ):
            raise RuntimeError("composition fixture uses dynamic package import")
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "sys"
            and node.attr == "modules"
        ):
            raise RuntimeError("composition fixture uses dynamic module registry access")


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


def require_fixture_rejection(command: list[str], *, cwd: Path, diagnostic: str) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if completed.returncode == 0 or diagnostic not in completed.stdout:
        raise RuntimeError(
            "neutral composition fixture negative did not fail with the expected diagnostic"
        )


def validate_result(
    result: object,
    contract: dict[str, object],
) -> None:
    if type(result) is not dict or set(result) != RESULT_KEYS:
        raise RuntimeError("neutral composition result has an unexpected shape")
    records = contract["packages"]
    assert isinstance(records, dict)
    if type(result["schema_version"]) is not int or result["schema_version"] != 1:
        raise RuntimeError("neutral composition result schema version differs")
    if result["packages"] != {name: record["version"] for name, record in records.items()}:
        raise RuntimeError("neutral composition result package versions differ")
    if result["protocol"] != contract["protocol"]:
        raise RuntimeError("neutral composition result protocol roots differ")
    if result["public_modules"] != sorted(PACKAGE_MODULES):
        raise RuntimeError("neutral composition did not reach the exact public module set")
    if result["manifest_compatible"] is not True:
        raise RuntimeError("neutral composition manifest did not compare compatible")
    if result["manifest_sha256"] != contract["manifest_sha256"]:
        raise RuntimeError("neutral composition canonical manifest shape differs")
    embedded = records["embedded-service-contract"]
    assert isinstance(embedded, dict)
    protocol = contract["protocol"]
    assert isinstance(protocol, dict)
    if result["incompatible_root_diagnostics"] != [
        {
            "expected": f"sha256:{embedded['wheel_content_root_sha256']}",
            "kind": "dependency-root",
            "observed": f"sha256:{'0' * 64}",
            "subject": "embedded-service-contract",
        },
        {
            "expected": f"sha256:{protocol['selected_surface_root_sha256']}",
            "kind": "protocol-schema",
            "observed": f"sha256:{'0' * 64}",
            "subject": "codex-app-server-surface",
        },
    ]:
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
                    "manifest_sha256": contract["manifest_sha256"],
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
        invalid_input = temporary_root / "invalid-composition-input.json"
        invalid_document = json.loads(fixture_input.read_text(encoding="utf-8"))
        invalid_document["schema_version"] = True
        invalid_input.write_text(
            json.dumps(invalid_document, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        require_fixture_rejection(
            [str(interpreter), "-I", str(FIXTURE_PATH), str(invalid_input)],
            cwd=temporary_root,
            diagnostic="unsupported schema version",
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
                "fixture_input_negatives": 1,
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
