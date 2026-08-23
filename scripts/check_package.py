#!/usr/bin/env python3
"""Build, install, import, test, and audit utility wheels in isolation."""

from __future__ import annotations

import argparse
import ast
import collections
import concurrent.futures
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from email.parser import BytesParser
from pathlib import Path, PurePosixPath

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = REPOSITORY_ROOT / "tools" / "package_matrix.json"
TOOLCHAIN_PATH = REPOSITORY_ROOT / "tools" / "toolchain.json"
NAME_PATTERN = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")
MAX_COMMAND_DIAGNOSTIC_CHARACTERS = 8_000


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as exc:
        output = exc.stdout if isinstance(exc.stdout, str) else ""
        truncated = len(output) > MAX_COMMAND_DIAGNOSTIC_CHARACTERS
        detail = output[-MAX_COMMAND_DIAGNOSTIC_CHARACTERS:].rstrip()
        prefix = "[earlier output truncated]\n" if truncated else ""
        rendered = f"\n{prefix}{detail}" if detail else ""
        raise RuntimeError(
            f"command failed with exit {exc.returncode}: {shlex.join(command)}{rendered}"
        ) from exc


def load_matrix() -> dict[str, object]:
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def normalize_distribution(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def requirement_distribution(value: str) -> str:
    match = NAME_PATTERN.match(value)
    if match is None:
        raise RuntimeError(f"invalid runtime requirement: {value!r}")
    return normalize_distribution(match.group(1))


def package_records(matrix: dict[str, object]) -> dict[str, dict[str, object]]:
    raw = matrix.get("packages")
    if not isinstance(raw, dict):
        raise RuntimeError("package matrix is missing packages")
    records: dict[str, dict[str, object]] = {}
    for distribution, details in raw.items():
        if not isinstance(distribution, str) or not isinstance(details, dict):
            raise RuntimeError("package matrix contains a malformed record")
        if not all(isinstance(details.get(field), str) for field in ("path", "import", "version")):
            raise RuntimeError(f"package matrix record is incomplete: {distribution}")
        runtime_dependencies = details.get("runtime_dependencies")
        if not isinstance(runtime_dependencies, list) or not all(
            isinstance(item, str) for item in runtime_dependencies
        ):
            raise RuntimeError(
                f"package matrix runtime dependency contract is malformed: {distribution}"
            )
        normalized = normalize_distribution(distribution)
        if normalized in records:
            raise RuntimeError(f"duplicate normalized distribution: {normalized}")
        records[normalized] = {
            "path": details["path"],
            "import": details["import"],
            "version": details["version"],
            "runtime_dependencies": tuple(runtime_dependencies),
        }
    return records


def validate_package_paths(
    packages: dict[str, dict[str, object]],
    *,
    repository_root: Path = REPOSITORY_ROOT,
) -> dict[str, Path]:
    packages_root = repository_root / "packages"
    if packages_root.is_symlink() or not packages_root.is_dir():
        raise RuntimeError("repository packages root must be a real directory")
    resolved_packages_root = packages_root.resolve()
    roots: dict[str, Path] = {}
    for distribution, package in packages.items():
        relative = Path(str(package["path"]))
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"package path escapes packages/: {distribution}: {relative}")
        candidate = repository_root / relative
        if candidate.is_symlink() or not candidate.is_dir():
            raise RuntimeError(f"package root must be a real directory: {distribution}: {relative}")
        resolved = candidate.resolve()
        if resolved.parent != resolved_packages_root:
            raise RuntimeError(f"package path escapes packages/: {distribution}: {relative}")
        nested_symlinks = sorted(path for path in candidate.rglob("*") if path.is_symlink())
        if nested_symlinks:
            rendered = ", ".join(str(path.relative_to(candidate)) for path in nested_symlinks)
            raise RuntimeError(f"package tree contains symlink(s): {distribution}: {rendered}")
        roots[distribution] = resolved
    return roots


def declared_runtime_requirements(package_root: Path) -> tuple[str, ...]:
    document = tomllib.loads((package_root / "pyproject.toml").read_text(encoding="utf-8"))
    project = document.get("project")
    if not isinstance(project, dict):
        raise RuntimeError(f"package project metadata is missing: {package_root}")
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list) or not all(
        isinstance(item, str) for item in dependencies
    ):
        raise RuntimeError(f"runtime dependencies are malformed: {package_root}")
    return tuple(dependencies)


def audit_requirement_contract(
    distribution: str,
    *,
    expected: tuple[str, ...],
    observed: tuple[str, ...],
    source: str,
) -> None:
    if observed != expected:
        raise RuntimeError(
            f"{source} runtime dependency contract differs for {distribution}: "
            f"expected={expected}, observed={observed}"
        )


def audit_dependency_edges(
    distribution: str,
    dependencies: tuple[str, ...],
    admitted: set[str],
) -> None:
    unadmitted = sorted(set(dependencies) - admitted)
    if unadmitted:
        raise RuntimeError(
            f"unadmitted runtime dependency in {distribution}: {', '.join(unadmitted)}"
        )


def validate_acyclic_graph(graph: dict[str, tuple[str, ...]]) -> None:
    visited: set[str] = set()
    active: list[str] = []

    def visit(distribution: str) -> None:
        if distribution in active:
            start = active.index(distribution)
            cycle = [*active[start:], distribution]
            raise RuntimeError(f"circular package dependency: {' -> '.join(cycle)}")
        if distribution in visited:
            return
        active.append(distribution)
        for dependency in graph[distribution]:
            visit(dependency)
        active.pop()
        visited.add(distribution)

    for distribution in sorted(graph):
        visit(distribution)


def audit_dependency_graph(
    packages: dict[str, dict[str, object]],
    package_roots: dict[str, Path],
) -> dict[str, tuple[str, ...]]:
    admitted = set(packages)
    graph: dict[str, tuple[str, ...]] = {}
    for distribution, package in packages.items():
        allowed_requirements = package["runtime_dependencies"]
        assert isinstance(allowed_requirements, tuple)
        source_requirements = declared_runtime_requirements(package_roots[distribution])
        audit_requirement_contract(
            distribution,
            expected=allowed_requirements,
            observed=source_requirements,
            source="source",
        )
        dependencies = tuple(
            requirement_distribution(requirement) for requirement in allowed_requirements
        )
        audit_dependency_edges(distribution, dependencies, admitted)
        graph[distribution] = dependencies
    validate_acyclic_graph(graph)
    return graph


def require_uv() -> str:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for the maintained package smoke envelope")
    toolchain = json.loads(TOOLCHAIN_PATH.read_text(encoding="utf-8"))
    actual = run([uv, "--version"], cwd=REPOSITORY_ROOT).stdout.strip()
    fields = actual.split(maxsplit=2)
    expected = str(toolchain["uv"])
    if len(fields) < 2 or fields[0] != "uv" or fields[1] != expected:
        raise RuntimeError(
            f"uv version mismatch: expected semantic version {expected!r}, got {actual!r}"
        )
    return uv


def environment_python(environment: Path) -> Path:
    posix = environment / "bin" / "python"
    return posix if posix.exists() else environment / "Scripts" / "python.exe"


def copy_package_snapshot(package_root: Path, destination: Path) -> None:
    symlinks = sorted(path for path in package_root.rglob("*") if path.is_symlink())
    if symlinks:
        relative = ", ".join(str(path.relative_to(package_root)) for path in symlinks)
        raise RuntimeError(f"package snapshot contains symlink(s): {relative}")
    shutil.copytree(
        package_root,
        destination,
        ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".pytest_cache", ".ruff_cache", "build", "dist"
        ),
    )


def wheel_metadata(archive: zipfile.ZipFile) -> tuple[str, str, str, tuple[str, ...]]:
    names = [
        name
        for name in archive.namelist()
        if name.endswith(".dist-info/METADATA") and not name.endswith("/")
    ]
    if len(names) != 1:
        raise RuntimeError(f"wheel must contain exactly one METADATA file, found {len(names)}")
    message = BytesParser().parsebytes(archive.read(names[0]))

    def singleton(field: str) -> str:
        values = message.get_all(field, [])
        if len(values) != 1 or not isinstance(values[0], str) or not values[0]:
            raise RuntimeError(f"wheel METADATA must contain exactly one {field} header")
        return values[0]

    name = singleton("Name")
    version = singleton("Version")
    requires_python = singleton("Requires-Python")
    requirements = tuple(message.get_all("Requires-Dist", []))
    return normalize_distribution(name), version, requires_python, requirements


def validated_wheel_member_names(archive: zipfile.ZipFile) -> tuple[str, ...]:
    names = tuple(info.filename for info in archive.infolist() if not info.is_dir())
    duplicates = sorted(name for name, count in collections.Counter(names).items() if count > 1)
    if duplicates:
        raise RuntimeError(f"wheel contains duplicate member name(s): {duplicates}")
    invalid: list[str] = []
    for name in names:
        path = PurePosixPath(name)
        if (
            path.is_absolute()
            or not path.parts
            or ".." in path.parts
            or "\\" in name
            or path.as_posix() != name
        ):
            invalid.append(name)
    if invalid:
        raise RuntimeError(f"wheel contains unsafe member path(s): {sorted(invalid)}")
    return names


def wheel_distribution_component(distribution: str) -> str:
    return re.sub(r"[-_.]+", "_", distribution)


def wheel_version_component(version: str) -> str:
    return re.sub(r"[^A-Za-z0-9.]+", "_", version)


def audit_wheel_layout(
    member_names: tuple[str, ...],
    *,
    distribution: str,
    import_root: str,
    version: str,
) -> None:
    dist_info = (
        f"{wheel_distribution_component(distribution)}-{wheel_version_component(version)}.dist-info"
    )
    import_prefix = f"{import_root}/"
    metadata_prefix = f"{dist_info}/"
    unexpected = sorted(
        name
        for name in member_names
        if not name.startswith(import_prefix) and not name.startswith(metadata_prefix)
    )
    if unexpected:
        raise RuntimeError(f"wheel contains unexpected top-level member(s): {unexpected}")
    required = {
        f"{import_root}/__init__.py",
        f"{dist_info}/METADATA",
        f"{dist_info}/RECORD",
        f"{dist_info}/WHEEL",
    }
    missing = sorted(required - set(member_names))
    if missing:
        raise RuntimeError(f"wheel layout is missing required member(s): {missing}")


def imported_roots_from_wheel(archive: zipfile.ZipFile) -> set[str]:
    roots: set[str] = set()
    for info in sorted(archive.infolist(), key=lambda item: item.filename):
        if info.is_dir() or not info.filename.endswith(".py"):
            continue
        source = archive.read(info).decode("utf-8")
        tree = ast.parse(source, filename=info.filename)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(alias.name.partition(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                roots.add(node.module.partition(".")[0])
    return roots


def audit_wheel_imports(
    distribution: str,
    observed: set[str],
    *,
    import_root: str,
    declared_import_roots: set[str],
) -> tuple[str, ...]:
    external = observed - set(sys.stdlib_module_names) - {import_root}
    undeclared = sorted(external - declared_import_roots)
    if undeclared:
        raise RuntimeError(f"undeclared import in {distribution}: {', '.join(undeclared)}")
    unobserved = sorted(declared_import_roots - external)
    if unobserved:
        raise RuntimeError(
            f"declared dependency import not observed in {distribution}: {', '.join(unobserved)}"
        )
    return tuple(sorted(external))


def wheel_content_record(archive: zipfile.ZipFile) -> tuple[str, int, int]:
    rows: list[dict[str, str | int]] = []
    total = 0
    for info in sorted(
        (item for item in archive.infolist() if not item.is_dir()),
        key=lambda item: item.filename,
    ):
        data = archive.read(info)
        total += len(data)
        rows.append(
            {
                "path": info.filename,
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            }
        )
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    return hashlib.sha256(payload).hexdigest(), len(rows), total


def audit_forced_package_data(
    package_root: Path,
    archive: zipfile.ZipFile,
    *,
    import_root: str,
) -> tuple[str, int]:
    document = tomllib.loads((package_root / "pyproject.toml").read_text(encoding="utf-8"))
    try:
        force_include = document["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"wheel has no declared retained package data: {package_root}") from exc
    if not isinstance(force_include, dict) or not force_include:
        raise RuntimeError(f"wheel has no declared retained package data: {package_root}")

    archive_members = {name for name in archive.namelist() if name and not name.endswith("/")}
    retained_rows: list[dict[str, str | int]] = []
    retained_destinations: set[str] = set()
    resolved_root = package_root.resolve()
    for source_value, destination_value in sorted(force_include.items()):
        if not isinstance(source_value, str) or not isinstance(destination_value, str):
            raise RuntimeError("wheel force-include mapping must contain text paths")
        source_relative = Path(source_value)
        if source_relative.is_absolute():
            raise RuntimeError(f"wheel package-data source must be relative: {source_value}")
        source = (package_root / source_relative).resolve()
        if not source.is_relative_to(resolved_root):
            raise RuntimeError(f"wheel package-data source escapes package root: {source_value}")
        destination_path = PurePosixPath(destination_value)
        if (
            destination_path.is_absolute()
            or ".." in destination_path.parts
            or not destination_path.parts
            or destination_path.parts[0] != import_root
            or "\\" in destination_value
        ):
            raise RuntimeError(
                f"wheel package-data destination escapes import root: {destination_value}"
            )
        destination = destination_path.as_posix().rstrip("/")
        if source.is_file():
            expected = {destination: source}
            actual = {destination} if destination in archive_members else set()
        elif source.is_dir():
            expected = {
                f"{destination}/{path.relative_to(source).as_posix()}": path
                for path in sorted(item for item in source.rglob("*") if item.is_file())
            }
            prefix = f"{destination}/"
            actual = {name for name in archive_members if name.startswith(prefix)}
        else:
            raise RuntimeError(f"wheel package-data source is missing: {source_value}")
        if not expected:
            raise RuntimeError(f"wheel package-data source is empty: {source_value}")
        if set(expected) != actual:
            missing = sorted(set(expected) - actual)
            extra = sorted(actual - set(expected))
            raise RuntimeError(
                f"wheel package-data members differ for {source_value}: "
                f"missing={missing}, extra={extra}"
            )
        overlap = retained_destinations & set(expected)
        if overlap:
            raise RuntimeError(f"wheel package-data destinations overlap: {sorted(overlap)}")
        retained_destinations.update(expected)
        for member, source_path in sorted(expected.items()):
            source_data = source_path.read_bytes()
            wheel_data = archive.read(member)
            if source_data != wheel_data:
                raise RuntimeError(f"wheel package-data bytes differ: {member}")
            retained_rows.append(
                {
                    "path": member,
                    "sha256": hashlib.sha256(wheel_data).hexdigest(),
                    "size": len(wheel_data),
                }
            )
    payload = json.dumps(retained_rows, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    return hashlib.sha256(payload).hexdigest(), len(retained_rows)


def require_test_contract(tests_root: Path) -> list[Path]:
    if not tests_root.is_dir():
        raise RuntimeError(f"package-local test contract is missing: {tests_root}")
    test_files = sorted(tests_root.rglob("test_*.py"))
    if not test_files:
        raise RuntimeError(f"package-local test contract is empty: {tests_root}")
    return test_files


def executed_test_count(output: str) -> int:
    matches = re.findall(r"^Ran ([0-9]+) tests? in ", output, flags=re.MULTILINE)
    if len(matches) != 1 or int(matches[0]) < 1:
        raise RuntimeError("package-local test contract executed zero or an unknown test count")
    return int(matches[0])


def check_package(
    distribution: str,
    package: dict[str, object],
    *,
    package_root: Path,
    packages: dict[str, dict[str, object]],
    dependency_graph: dict[str, tuple[str, ...]],
    python_requires: str,
    python_spec: str,
    uv: str,
    tests: bool,
) -> dict[str, object]:
    import_root = package["import"]
    version_contract = package["version"]
    expected_requirements = package["runtime_dependencies"]
    assert isinstance(import_root, str)
    assert isinstance(version_contract, str)
    assert isinstance(expected_requirements, tuple)
    with tempfile.TemporaryDirectory(prefix=f"utils-{distribution}-") as temporary:
        temporary_root = Path(temporary)
        snapshot = temporary_root / "package"
        dist_dir = temporary_root / "dist"
        environment = temporary_root / "venv"
        copy_package_snapshot(package_root, snapshot)
        run(
            [
                uv,
                "build",
                "--wheel",
                "--out-dir",
                str(dist_dir),
                "--no-create-gitignore",
                "--python",
                python_spec,
                str(snapshot),
            ],
            cwd=temporary_root,
        )
        wheels = sorted(dist_dir.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one wheel for {distribution}, found {len(wheels)}")
        wheel = wheels[0]
        with zipfile.ZipFile(wheel) as archive:
            members = validated_wheel_member_names(archive)
            import_prefix = f"{import_root}/"
            if not any(member.startswith(import_prefix) for member in members):
                raise RuntimeError(f"wheel is missing import root {import_prefix}")
            if any(member.startswith("utils/") for member in members):
                raise RuntimeError("wheel exposes prohibited top-level utils import")
            name, version, requires_python, metadata_requirements = wheel_metadata(archive)
            if name != distribution:
                raise RuntimeError(
                    f"wheel distribution mismatch: expected {distribution}, observed {name}"
                )
            if version != version_contract:
                raise RuntimeError(
                    f"wheel version mismatch for {distribution}: expected {version_contract}, "
                    f"observed {version}"
                )
            if requires_python != python_requires:
                raise RuntimeError(
                    f"wheel Python baseline mismatch for {distribution}: "
                    f"expected {python_requires}, observed {requires_python}"
                )
            audit_wheel_layout(
                members,
                distribution=distribution,
                import_root=import_root,
                version=version,
            )
            audit_requirement_contract(
                distribution,
                expected=expected_requirements,
                observed=metadata_requirements,
                source="wheel",
            )
            dependency_names = dependency_graph[distribution]
            declared_import_roots = {
                str(packages[dependency]["import"]) for dependency in dependency_names
            }
            external_imports = audit_wheel_imports(
                distribution,
                imported_roots_from_wheel(archive),
                import_root=import_root,
                declared_import_roots=declared_import_roots,
            )
            retained_root, retained_count = audit_forced_package_data(
                snapshot,
                archive,
                import_root=import_root,
            )
            content_root, member_count, uncompressed_bytes = wheel_content_record(archive)

        run(
            [uv, "venv", "--no-project", "--python", python_spec, str(environment)],
            cwd=REPOSITORY_ROOT,
        )
        interpreter = environment_python(environment)
        run(
            [uv, "pip", "install", "--python", str(interpreter), "--no-deps", str(wheel)],
            cwd=REPOSITORY_ROOT,
        )
        probe = (
            f"import {import_root} as package; "
            f"assert package.__version__ == {version_contract!r}; "
            "print(package.__version__)"
        )
        result = run([str(interpreter), "-I", "-c", probe], cwd=temporary_root)
        record: dict[str, object] = {
            "distribution": distribution,
            "import": import_root,
            "version": result.stdout.strip(),
            "wheel": wheel.name,
            "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            "wheel_content_root_sha256": content_root,
            "wheel_members": member_count,
            "wheel_uncompressed_bytes": uncompressed_bytes,
            "python": python_spec,
            "declared_dependencies": list(metadata_requirements),
            "observed_external_imports": list(external_imports),
            "dependency_audit": "passed",
            "retained_package_data_files": retained_count,
            "retained_package_data_root_sha256": retained_root,
            "test_source": "isolated-package-snapshot",
        }
        tests_root = snapshot / "tests"
        if tests:
            require_test_contract(tests_root)
            test_result = run(
                [
                    str(interpreter),
                    "-I",
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    str(tests_root),
                    "-p",
                    "test_*.py",
                    "-v",
                ],
                cwd=temporary_root,
            )
            record["test_count"] = executed_test_count(test_result.stdout)
            record["tests"] = test_result.stdout.strip().splitlines()[-1]
        return record


def main() -> int:
    parser = argparse.ArgumentParser()
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--package")
    selection.add_argument("--all", action="store_true")
    parser.add_argument("--python", default=sys.executable, dest="python_spec")
    parser.add_argument("--tests", action="store_true")
    args = parser.parse_args()
    if not args.tests:
        parser.error("--tests is required for the isolated distribution acceptance check")

    uv = require_uv()
    matrix = load_matrix()
    packages = package_records(matrix)
    package_roots = validate_package_paths(packages)
    dependency_graph = audit_dependency_graph(packages, package_roots)
    selected = sorted(packages) if args.all else [args.package]
    unknown = [name for name in selected if name not in packages]
    if unknown:
        parser.error(f"unknown package: {', '.join(unknown)}")

    python_requires = matrix.get("python_requires")
    if not isinstance(python_requires, str):
        raise RuntimeError("package matrix is missing python_requires")
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(selected)) as executor:
        futures = {
            name: executor.submit(
                check_package,
                name,
                packages[name],
                package_root=package_roots[name],
                packages=packages,
                dependency_graph=dependency_graph,
                python_requires=python_requires,
                python_spec=args.python_spec,
                uv=uv,
                tests=args.tests,
            )
            for name in selected
        }
        results = [futures[name].result() for name in selected]
    print(json.dumps({"results": results}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
