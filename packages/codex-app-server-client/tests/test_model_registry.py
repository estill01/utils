"""Offline contracts for independently bound retained model graphs."""

from __future__ import annotations

import importlib
import inspect
import json
import pickle
import unittest
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError

import codex_app_server_client as legacy_api
from codex_app_server_client import models as legacy
from codex_app_server_client.compatibility import _packaged_protocol_root
from test_session import minimum_value


class ProfileModelRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.original_identity = legacy.ClientIdentity
        cls.original_turn = legacy.TurnStartParams
        cls.modern = importlib.import_module("codex_app_server_client.v0_162_1.models")

    def test_legacy_identity_module_paths_signatures_and_pickle_stay_stable(self) -> None:
        self.assertIs(legacy.ClientIdentity, self.original_identity)
        self.assertIs(legacy_api.ClientIdentity, self.original_identity)
        self.assertIs(legacy.TurnStartParams, self.original_turn)
        self.assertEqual(
            str(inspect.signature(legacy.ClientIdentity)),
            "(name: 'str', version: 'str', title: 'str | None' = None) -> None",
        )
        for module in (legacy, self.modern):
            for name in ("ClientIdentity", *module._PUBLIC_MODEL_NAMES):
                self.assertEqual(getattr(module, name).__module__, module.__name__)
            self.assertEqual(module.FrozenJsonObject.__module__, module.__name__)
            identity = module.ClientIdentity("fixture", "1.0")
            self.assertEqual(pickle.loads(pickle.dumps(identity)), identity)
        self.assertIsNot(legacy.ClientIdentity, self.modern.ClientIdentity)
        self.assertIsNot(legacy.ImageDetail, self.modern.ImageDetail)
        self.assertIsNot(legacy._SchemaModel, self.modern._SchemaModel)

    def test_registry_and_nested_schema_bindings_are_immutable(self) -> None:
        registry = self.modern._REGISTRY
        with self.assertRaises(FrozenInstanceError):
            registry.module_name = "switched"
        with self.assertRaises(TypeError):
            registry.namespace["ThreadStartParams"] = legacy.ThreadStartParams
        with self.assertRaises(TypeError):
            self.modern._RUNTIME_TYPES["ThreadStartParams"] = legacy.ThreadStartParams
        spec = self.modern._SPECS["ImageUserInput"]
        with self.assertRaises(FrozenInstanceError):
            spec.schema = {}
        with self.assertRaises(TypeError):
            spec.schema["properties"]["type"]["enum"][0] = "switched"
        self.assertIsInstance(spec.sources, frozenset)

    def test_both_selected_top_level_graphs_round_trip_independently(self) -> None:
        for module, root in (
            (legacy, _packaged_protocol_root().joinpath("upstream", "0.147.0")),
            (
                self.modern,
                _packaged_protocol_root().joinpath("profiles", "0.162.1", "upstream", "0.162.1"),
            ),
        ):
            for source in module._PUBLIC_SCHEMA_FILES:
                document = json.loads(root.joinpath(source).read_text(encoding="utf-8"))
                value = minimum_value(document, document)
                with self.subTest(profile=module.__name__, source=source):
                    model = module._REGISTRY.decode_document(source, value)
                    self.assertIsInstance(model, getattr(module, document["title"]))
                    self.assertEqual(model.to_dict(), value)

    def test_new_profile_fields_do_not_expand_legacy_models(self) -> None:
        value = {"threadId": "thread", "input": [{"type": "image", "fileId": "file-a"}]}
        modern = self.modern.TurnStartParams.from_dict(value)
        self.assertEqual(modern.to_dict(), value)
        with self.assertRaises(legacy._ModelValidationError):
            legacy.TurnStartParams.from_dict(value)
        self.assertNotIn("fileId", legacy.ImageUserInput.__dataclass_fields__)
        self.assertIn("fileId", self.modern.ImageUserInput.__dataclass_fields__)

    def test_cross_profile_nested_models_do_not_leak_through_constructors_or_decoders(self) -> None:
        for source, target in ((legacy, self.modern), (self.modern, legacy)):
            foreign = source.TextUserInput(type="text", text="fixture")
            with self.subTest(source=source.__name__, target=target.__name__):
                with self.assertRaises(target._ModelValidationError):
                    target.TurnStartParams(threadId="thread", input=(foreign,))
                with self.assertRaises(target._ModelValidationError):
                    target.TextUserInput.from_dict(foreign)
                with self.assertRaises(target._ModelValidationError):
                    target._REGISTRY.to_json(foreign)

    def test_parallel_profiles_keep_their_own_classes_and_closure_policy(self) -> None:
        def round_trip(index: int) -> None:
            module = legacy if index % 2 else self.modern
            image = {"type": "image", "url": "https://example.test/image.png"}
            if module is self.modern:
                image["fileId"] = "file-a"
            value = {"threadId": "thread", "input": [image]}
            params = module.TurnStartParams.from_dict(value)
            self.assertIsInstance(params.input[0], module.ImageUserInput)
            self.assertEqual(params.to_dict(), value)
            with self.assertRaises(module._ModelValidationError):
                module.ThreadReadParams.from_dict({"threadId": "thread", "unknown": True})
            warning = module.WarningNotification.from_dict(
                {"message": "fixture", "futureInbound": {"nested": [index]}}
            )
            self.assertEqual(warning.to_dict()["futureInbound"], {"nested": [index]})

        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(round_trip, range(40)))


class CompositeImageModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.models = importlib.import_module("codex_app_server_client.v0_162_1.models")

    def test_valid_image_alternatives_keep_parent_and_all_present_child_fields(self) -> None:
        images = (
            {"type": "image", "url": "https://example.test/image.png"},
            {"type": "image", "fileId": "file-a"},
            {"type": "image", "url": "https://example.test/image.png", "detail": "high"},
            {"type": "image", "fileId": "file-a", "detail": "low"},
            {"type": "image", "url": "url-a", "fileId": "file-a"},
            {"type": "image", "url": "url-a", "fileId": "file-a", "detail": "original"},
        )
        for image in images:
            with self.subTest(image=image):
                direct = self.models.ImageUserInput.from_dict(image)
                self.assertEqual(direct.to_dict(), image)
                self.assertEqual(self.models.ImageUserInput(**image).to_dict(), image)
                value = {"threadId": "thread", "input": [image]}
                params = self.models.TurnStartParams.from_dict(value)
                self.assertIsInstance(params.input[0], self.models.ImageUserInput)
                self.assertEqual(params.to_dict(), value)
                self.assertEqual(params.input[0].type, "image")

    def test_invalid_parent_children_or_unselected_fields_fail_closed(self) -> None:
        invalid = (
            {"url": "url-a"},
            {"fileId": "file-a"},
            {"type": "wrong", "url": "url-a"},
            {"type": 123, "fileId": "file-a"},
            {"type": "image"},
            {"type": "image", "url": 123},
            {"type": "image", "fileId": 123},
            {"type": "image", "url": "url-a", "fileId": 123},
            {"type": "image", "url": 123, "fileId": "file-a"},
            {"type": "image", "url": "url-a", "detail": "wrong"},
            {"type": "image", "url": "url-a", "detail": 123},
            {"type": "image", "url": "url-a", "unselected": True},
            {"type": "image", "fileId": "file-a", "unselected": True},
        )
        for image in invalid:
            with self.subTest(image=image):
                with self.assertRaises(self.models._ModelValidationError):
                    self.models.ImageUserInput.from_dict(image)
                with self.assertRaises(self.models._ModelValidationError):
                    self.models.TurnStartParams.from_dict({"threadId": "t", "input": [image]})

    def test_direct_constructor_enforces_the_child_requirement(self) -> None:
        with self.assertRaises(self.models._ModelValidationError):
            self.models.ImageUserInput(type="image")
        with self.assertRaises(self.models._ModelValidationError):
            self.models.ImageUserInput(type="wrong", url="url-a")
        with self.assertRaises(self.models._ModelValidationError):
            self.models.ImageUserInput(type="image", fileId=123)

    def test_composite_inbound_extras_are_preserved_but_not_serializable_outbound(self) -> None:
        image = {"type": "image", "fileId": "file-a", "detail": "high", "future": [1]}
        decoded = self.models._decode_named(
            "ImageUserInput", image, "image", allow_omitted_additional=True
        )
        self.assertEqual(
            self.models._REGISTRY.to_json(decoded, allow_omitted_additional=True), image
        )
        outbound = self.models.TurnStartParams(threadId="t", input=(decoded,))
        with self.assertRaises(self.models._ModelValidationError):
            outbound.to_dict()

    def test_generic_object_combinators_conjoin_parent_constraints(self) -> None:
        parent = {
            "type": "object",
            "properties": {"kind": {"type": "string", "enum": ["fixture"]}},
            "required": ["kind"],
        }
        branches = [
            {"type": "object", "properties": {name: {"type": "string"}}, "required": [name]}
            for name in ("left", "right")
        ]
        for keyword in ("anyOf", "oneOf", "allOf"):
            schema = {**parent, keyword: branches}
            valid = {"kind": "fixture", "left": "a"}
            if keyword == "allOf":
                valid["right"] = "b"
            with self.subTest(keyword=keyword):
                self.assertEqual(
                    self.models._REGISTRY.to_json(
                        self.models._decode(schema, {}, valid, "fixture")
                    ),
                    valid,
                )
                with self.assertRaises(self.models._ModelValidationError):
                    self.models._decode(schema, {}, {"left": "a", "right": "b"}, "fixture")
                with self.assertRaises(self.models._ModelValidationError):
                    self.models._decode(schema, {}, {**valid, "kind": "wrong"}, "fixture")
                if keyword == "oneOf":
                    with self.assertRaises(self.models._ModelValidationError):
                        self.models._decode(schema, {}, {**valid, "right": "b"}, "fixture")
