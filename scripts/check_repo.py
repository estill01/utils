#!/usr/bin/env python3
"""Validate repository and package-boundary invariants using the standard library."""

from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MATRIX = json.loads((REPOSITORY_ROOT / "tools" / "package_matrix.json").read_text())
FORBIDDEN_IMPORTS = {
    "librsi",
    "patent_studio",
    "software_factory",
    "utils",
}


def imported_roots(source: Path) -> set[str]:
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.partition(".")[0])
    return roots


def main() -> int:
    root_config = tomllib.loads((REPOSITORY_ROOT / "pyproject.toml").read_text())
    if "project" in root_config:
        raise RuntimeError("repository root must not define a distribution")
    if (REPOSITORY_ROOT / "src" / "utils").exists():
        raise RuntimeError("top-level utils namespace is prohibited")

    packages = MATRIX["packages"]
    import_roots = {details["import"] for details in packages.values()}
    for distribution, details in packages.items():
        package_root = REPOSITORY_ROOT / details["path"]
        metadata = tomllib.loads((package_root / "pyproject.toml").read_text())
        project = metadata["project"]
        if project["name"] != distribution:
            raise RuntimeError(f"distribution name mismatch for {distribution}")
        if project["version"] != details["version"]:
            raise RuntimeError(f"version mismatch for {distribution}")
        if project["requires-python"] != MATRIX["python_requires"]:
            raise RuntimeError(f"Python baseline mismatch for {distribution}")
        if project.get("dependencies", []) != []:
            raise RuntimeError(f"skeleton has runtime dependencies: {distribution}")
        if not (package_root / "README.md").is_file():
            raise RuntimeError(f"missing package documentation: {distribution}")
        source_root = package_root / "src" / details["import"]
        if not (source_root / "__init__.py").is_file():
            raise RuntimeError(f"missing import skeleton: {distribution}")
        sibling_imports = import_roots - {details["import"]}
        for source in source_root.rglob("*.py"):
            roots = imported_roots(source)
            prohibited = roots & (FORBIDDEN_IMPORTS | sibling_imports)
            if prohibited:
                raise RuntimeError(f"prohibited import in {source}: {sorted(prohibited)}")

    print(
        json.dumps(
            {
                "distributions": sorted(packages),
                "root_distribution": False,
                "runtime_dependencies": "none",
                "top_level_utils": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
