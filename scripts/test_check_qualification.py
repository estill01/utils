#!/usr/bin/env python3
"""Focused negative tests for the technical qualification verifier."""

from __future__ import annotations

import copy
import importlib.util
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_qualification", REPOSITORY_ROOT / "scripts" / "check_qualification.py"
)
assert SPEC is not None and SPEC.loader is not None
check_qualification = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = check_qualification
SPEC.loader.exec_module(check_qualification)


class QualificationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.record = check_qualification.load_json(check_qualification.QUALIFICATION_PATH)
        self.packages = check_qualification.load_json(check_qualification.PACKAGE_MATRIX_PATH)
        self.composition = check_qualification.load_json(
            check_qualification.COMPOSITION_MATRIX_PATH
        )

    def validate(self, record: object | None = None) -> dict[str, object]:
        return check_qualification.validate_contract(
            self.record if record is None else record, self.packages, self.composition
        )

    def test_current_contract_and_files_validate(self) -> None:
        record = self.validate()
        check_qualification.validate_files(record, REPOSITORY_ROOT)

    def test_rejects_unknown_field(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["consumer_acceptance"] = True
        with self.assertRaisesRegex(RuntimeError, "unexpected shape"):
            self.validate(changed)

    def test_rejects_incomplete_matrix(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["python_matrix"] = ["3.11"]
        with self.assertRaisesRegex(RuntimeError, "Python matrix is incomplete"):
            self.validate(changed)

    def test_rejects_release_posture_change(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["release_posture"] = "published"
        with self.assertRaisesRegex(RuntimeError, "changes the release posture"):
            self.validate(changed)

    def test_rejects_undeclared_dependency(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["packages"]["runtime-manifest"]["runtime_dependencies"] = ["consumer"]
        with self.assertRaisesRegex(RuntimeError, "runtime_dependencies differs"):
            self.validate(changed)

    def test_rejects_mixed_artifact_root(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["packages"]["runtime-manifest"]["wheel_sha256"] = "0" * 64
        with self.assertRaisesRegex(RuntimeError, "qualified artifact differs"):
            self.validate(changed)

    def test_rejects_missing_wheel_data(self) -> None:
        changed = copy.deepcopy(self.record)
        del changed["packages"]["runtime-manifest"]["wheel_sha256"]
        with self.assertRaisesRegex(RuntimeError, "unexpected shape"):
            self.validate(changed)

    def test_rejects_pre_correction_source_commit(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["packages"]["runtime-manifest"]["accepted_source_commit"] = (
            "5e0a84137875740cb3c1ebf73a5f5cbf0525d9d9"
        )
        with self.assertRaisesRegex(RuntimeError, "accepted source commit differs"):
            self.validate(changed)

    def test_rejects_incomplete_public_contract_inventory(self) -> None:
        changed = copy.deepcopy(self.record)
        del changed["packages"]["codex-app-server-client"]["public_contracts"][
            "packages/codex-app-server-client/protocol/compatibility.json"
        ]
        with self.assertRaisesRegex(RuntimeError, "public contract inventory differs"):
            self.validate(changed)

    def test_rejects_changed_package_tree(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["packages"]["runtime-manifest"]["package_tree_object"] = "0" * 40
        with self.assertRaisesRegex(RuntimeError, "accepted package tree differs"):
            self.validate(changed)

    def test_rejects_swapped_executable_example_ownership(self) -> None:
        record = copy.deepcopy(self.validate())
        runtime = record["documentation"]["executable_examples"]["runtime-manifest"]
        record["documentation"]["executable_examples"]["codex-app-server-client"] = runtime
        with self.assertRaisesRegex(RuntimeError, "example ownership differs"):
            check_qualification.validate_documentation(record, REPOSITORY_ROOT)

    def test_rejects_wrong_expected_head(self) -> None:
        record = self.validate()
        with self.assertRaisesRegex(RuntimeError, "qualification HEAD differs"):
            check_qualification.validate_current_candidate(record, REPOSITORY_ROOT, "0" * 40)

    def test_rejects_contract_path_escape(self) -> None:
        changed = copy.deepcopy(self.record)
        changed["packages"]["runtime-manifest"]["public_contracts"] = {"../outside.json": "0" * 64}
        with self.assertRaisesRegex(RuntimeError, "public contract inventory differs"):
            self.validate(changed)

    def test_rejects_changed_documentation(self) -> None:
        record = self.validate()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in record["documentation"]["files"]:
                source = REPOSITORY_ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            source = REPOSITORY_ROOT / "packages" / "runtime-manifest" / "README.md"
            target = root / "packages" / "runtime-manifest" / "README.md"
            target.write_text(source.read_text(encoding="utf-8") + "changed\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "documentation file differs"):
                check_qualification.validate_documentation(record, root)

    def test_rejects_invalid_executable_example(self) -> None:
        record = copy.deepcopy(self.validate())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in record["documentation"]["files"]:
                source = REPOSITORY_ROOT / relative
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            relative = "packages/runtime-manifest/README.md"
            path = root / relative
            path.write_text("```python executable\nif\n```\n", encoding="utf-8")
            digest = check_qualification.file_sha256(path)
            record["documentation"]["files"][relative] = digest
            record["documentation"]["executable_examples"]["runtime-manifest"] = {
                "path": relative,
                "sha256": digest,
            }
            with self.assertRaises(SyntaxError):
                check_qualification.validate_documentation(record, root)


if __name__ == "__main__":
    unittest.main()
