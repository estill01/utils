#!/usr/bin/env python3
"""Validate the frozen, repository-owned technical qualification record."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
QUALIFICATION_PATH = REPOSITORY_ROOT / "tools" / "qualification_matrix.json"
PACKAGE_MATRIX_PATH = REPOSITORY_ROOT / "tools" / "package_matrix.json"
COMPOSITION_MATRIX_PATH = REPOSITORY_ROOT / "tools" / "composition_matrix.json"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
EXECUTABLE_EXAMPLE_PATTERN = re.compile(r"```python executable\n(.*?)```", re.DOTALL)
FROZEN_TOOLING = (
    ".github/workflows/ci.yml",
    "README.md",
    "docs/admission.md",
    "docs/architecture.md",
    "docs/composition.md",
    "docs/development.md",
    "docs/qualification.md",
    "pyproject.toml",
    "scripts/check_app_server_currentness.py",
    "scripts/check_composition.py",
    "scripts/check_package.py",
    "scripts/check_protocol_contract.py",
    "scripts/check_qualification.py",
    "scripts/check_repo.py",
    "scripts/check_quality.py",
    "scripts/schema_tree.py",
    "scripts/smoke_app_server_client.py",
    "scripts/test_check_composition.py",
    "scripts/test_check_package.py",
    "scripts/test_check_qualification.py",
    "scripts/test_protocol_contract.py",
    "tests/neutral_composition.py",
    "tools/changed_tests.json",
    "tools/composition_matrix.json",
    "tools/package_matrix.json",
    "tools/toolchain.json",
)


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def require_exact_sha256(value: object, label: str) -> str:
    if type(value) is not str or SHA256_PATTERN.fullmatch(value) is None:
        raise RuntimeError(f"{label} must be an exact lowercase SHA-256 value")
    return value


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frozen_source_record(repository_root: Path) -> tuple[str, int]:
    package_root = repository_root / "packages"
    ignored_parts = {"__pycache__", ".pytest_cache", ".ruff_cache", "build", "dist"}
    paths = sorted(
        {
            *(repository_root / relative for relative in FROZEN_TOOLING),
            *(
                path
                for path in package_root.rglob("*")
                if path.is_file()
                and not ignored_parts.intersection(path.relative_to(package_root).parts)
                and path.suffix != ".pyc"
            ),
        },
        key=lambda path: path.relative_to(repository_root).as_posix(),
    )
    missing = [path for path in paths if not path.is_file()]
    if missing:
        rendered = ", ".join(str(path.relative_to(repository_root)) for path in missing)
        raise RuntimeError(f"frozen technical source is missing file(s): {rendered}")
    rows = [
        {
            "path": path.relative_to(repository_root).as_posix(),
            "sha256": file_sha256(path),
            "size": path.stat().st_size,
        }
        for path in paths
    ]
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    return hashlib.sha256(payload).hexdigest(), len(rows)


def validate_exact_shape(value: object, fields: set[str], label: str) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise RuntimeError(f"{label} has an unexpected shape")
    return value


def repository_file(repository_root: Path, relative: object, label: str) -> Path:
    if type(relative) is not str:
        raise RuntimeError(f"{label} path must be text")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise RuntimeError(f"{label} path escapes the repository")
    candidate = repository_root / path
    if candidate.is_symlink() or not candidate.is_file():
        raise RuntimeError(f"{label} file is missing or not regular: {relative}")
    return candidate


def validate_documentation(record: dict[str, object], repository_root: Path) -> None:
    documentation = validate_exact_shape(
        record["documentation"], {"files", "executable_examples"}, "documentation record"
    )
    files = documentation["files"]
    if type(files) is not dict or not files:
        raise RuntimeError("documentation file inventory is empty")
    for relative, expected_sha256 in files.items():
        require_exact_sha256(expected_sha256, f"documentation file {relative}")
        path = repository_file(repository_root, relative, "documentation")
        if file_sha256(path) != expected_sha256:
            raise RuntimeError(f"documentation file differs: {relative}")

    examples = documentation["executable_examples"]
    if type(examples) is not dict or set(examples) != set(record["packages"]):
        raise RuntimeError("executable documentation example matrix is incomplete")
    for distribution, details in examples.items():
        example = validate_exact_shape(details, {"path", "sha256"}, f"{distribution} example")
        relative = example["path"]
        path = repository_file(repository_root, relative, f"{distribution} example")
        require_exact_sha256(example["sha256"], f"{distribution} example")
        if not path.is_file() or file_sha256(path) != example["sha256"]:
            raise RuntimeError(f"executable documentation differs: {distribution}")
        matches = EXECUTABLE_EXAMPLE_PATTERN.findall(path.read_text(encoding="utf-8"))
        if len(matches) != 1:
            raise RuntimeError(f"{distribution} must have exactly one executable example")
        ast.parse(matches[0], filename=relative)


def validate_contract(
    record: object,
    package_matrix: object,
    composition_matrix: object,
) -> dict[str, object]:
    qualification = validate_exact_shape(
        record,
        {
            "schema_version",
            "qualification_posture",
            "release_posture",
            "python_matrix",
            "commands",
            "packages",
            "protocol",
            "composition",
            "documentation",
            "technical_source",
        },
        "qualification record",
    )
    if type(qualification["schema_version"]) is not int or qualification["schema_version"] != 1:
        raise RuntimeError("qualification schema version differs")
    if qualification["qualification_posture"] != "program-qualified":
        raise RuntimeError("technical package set is not program-qualified")
    if qualification["release_posture"] != "no-license-selected/unpublished":
        raise RuntimeError("qualification record changes the release posture")
    if qualification["python_matrix"] != ["3.11", "3.14"]:
        raise RuntimeError("qualification Python matrix is incomplete")
    expected_commands = [
        "python3 scripts/check_quality.py",
        "python3 scripts/check_package.py --all --python 3.11 --tests",
        "python3 scripts/check_package.py --all --python 3.14 --tests",
        "python3 scripts/check_composition.py --python 3.11",
        "python3 scripts/check_composition.py --python 3.14",
    ]
    if qualification["commands"] != expected_commands:
        raise RuntimeError("complete internal matrix command inventory differs")

    packages_input = validate_exact_shape(
        package_matrix, {"schema_version", "python_requires", "packages"}, "package matrix"
    )
    composition_input = validate_exact_shape(
        composition_matrix,
        {"schema_version", "fixture_sha256", "manifest_sha256", "packages", "protocol"},
        "composition matrix",
    )
    packages = qualification["packages"]
    package_inputs = packages_input["packages"]
    composition_packages = composition_input["packages"]
    if (
        type(packages) is not dict
        or type(package_inputs) is not dict
        or type(composition_packages) is not dict
        or not packages
        or set(packages) != set(package_inputs)
        or set(packages) != set(composition_packages)
    ):
        raise RuntimeError("qualified package inventory differs from the accepted matrices")
    for distribution, details in packages.items():
        package = validate_exact_shape(
            details,
            {
                "accepted_source_commit",
                "path",
                "import",
                "version",
                "runtime_dependencies",
                "wheel",
                "wheel_sha256",
                "wheel_content_root_sha256",
                "public_contracts",
            },
            f"qualified package {distribution}",
        )
        if type(package["accepted_source_commit"]) is not str or not re.fullmatch(
            r"[0-9a-f]{40}", package["accepted_source_commit"]
        ):
            raise RuntimeError(f"{distribution} accepted source commit is invalid")
        source = package_inputs[distribution]
        artifact = composition_packages[distribution]
        assert isinstance(source, dict) and isinstance(artifact, dict)
        for field in ("path", "import", "version", "runtime_dependencies"):
            if package[field] != source[field]:
                raise RuntimeError(f"{distribution} qualified {field} differs")
        for field in ("version", "wheel_sha256", "wheel_content_root_sha256"):
            if package[field] != artifact[field]:
                raise RuntimeError(f"{distribution} qualified artifact differs: {field}")
        expected_wheel = f"{str(package['import'])}-{package['version']}-py3-none-any.whl"
        if package["wheel"] != expected_wheel:
            raise RuntimeError(f"{distribution} wheel filename differs")
        require_exact_sha256(package["wheel_sha256"], f"{distribution} wheel")
        require_exact_sha256(package["wheel_content_root_sha256"], f"{distribution} content")
        contracts = package["public_contracts"]
        if type(contracts) is not dict or not contracts:
            raise RuntimeError(f"{distribution} public contract inventory is empty")
        for path, digest in contracts.items():
            if type(path) is not str:
                raise RuntimeError(f"{distribution} public contract path must be text")
            package_path = Path(str(package["path"]))
            contract_path = Path(path)
            if (
                contract_path.is_absolute()
                or ".." in contract_path.parts
                or not contract_path.is_relative_to(package_path)
            ):
                raise RuntimeError(f"{distribution} public contract path escapes the package")
            require_exact_sha256(digest, f"{distribution} public contract {path}")

    if qualification["protocol"] != composition_input["protocol"]:
        raise RuntimeError("qualified protocol roots differ")
    if qualification["composition"] != {
        "fixture_sha256": composition_input["fixture_sha256"],
        "manifest_sha256": composition_input["manifest_sha256"],
    }:
        raise RuntimeError("qualified composition roots differ")
    return qualification


def validate_files(record: dict[str, object], repository_root: Path) -> None:
    for distribution, details in record["packages"].items():
        assert isinstance(details, dict)
        for relative, expected_sha256 in details["public_contracts"].items():
            path = repository_file(repository_root, relative, f"{distribution} public contract")
            if file_sha256(path) != expected_sha256:
                raise RuntimeError(f"{distribution} public contract differs: {relative}")
    validate_documentation(record, repository_root)
    source = validate_exact_shape(
        record["technical_source"], {"root_sha256", "files"}, "technical source record"
    )
    expected_root = require_exact_sha256(source["root_sha256"], "technical source root")
    observed_root, observed_files = frozen_source_record(repository_root)
    if (
        type(source["files"]) is not int
        or source["files"] != observed_files
        or expected_root != observed_root
    ):
        raise RuntimeError("frozen technical source differs from qualification evidence")


def validate_git_ancestry(record: dict[str, object], repository_root: Path) -> None:
    for distribution, details in record["packages"].items():
        assert isinstance(details, dict)
        commit = str(details["accepted_source_commit"])
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", commit, "HEAD"],
            cwd=repository_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"{distribution} accepted source is not an ancestor of HEAD")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-git", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    record = validate_contract(
        load_json(QUALIFICATION_PATH),
        load_json(PACKAGE_MATRIX_PATH),
        load_json(COMPOSITION_MATRIX_PATH),
    )
    validate_files(record, REPOSITORY_ROOT)
    if not args.skip_git:
        validate_git_ancestry(record, REPOSITORY_ROOT)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
