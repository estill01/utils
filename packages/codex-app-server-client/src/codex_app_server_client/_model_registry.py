"""Private profile-bound model and decoder factory.

Each registry captures one retained schema graph. Building another registry never
changes the classes or decoding rules already used by an existing client.
"""

from __future__ import annotations

import json
import operator
import re
from collections.abc import Iterator, Mapping
from contextvars import ContextVar
from dataclasses import dataclass, field, fields, make_dataclass, replace
from enum import StrEnum
from importlib.resources.abc import Traversable
from types import MappingProxyType
from typing import Any, Literal, Self

from .compatibility import _load_json


def _freeze_schema(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _freeze_schema(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_schema(item) for item in value)
    return value


@dataclass(frozen=True, slots=True, init=False)
class ModelRegistry:
    """Immutable bindings for an independently generated model namespace."""

    namespace: Mapping[str, object]
    module_name: str

    def __init__(self, schema_root: Traversable, module_name: str) -> None:
        object.__setattr__(self, "module_name", module_name)
        object.__setattr__(self, "namespace", _build_model_namespace(schema_root, module_name))

    def decode_document(self, source: str, value: object) -> object:
        return self.namespace["_decode_document"](source, value)

    def decode_named(self, name: str, value: object, path: str, **kwargs: Any) -> object:
        return self.namespace["_decode_named"](name, value, path, **kwargs)

    def to_json(self, value: object, **kwargs: Any) -> object:
        return self.namespace["_to_json"](value, **kwargs)


def _build_model_namespace(schema_root: Traversable, module_name: str) -> Mapping[str, object]:
    namespace: dict[str, object] = {}
    _OPERATION_SCHEMA_FILES = (
        "v2/ThreadStartParams.json",
        "v2/ThreadStartResponse.json",
        "v2/ThreadResumeParams.json",
        "v2/ThreadResumeResponse.json",
        "v2/ThreadReadParams.json",
        "v2/ThreadReadResponse.json",
        "v2/ThreadListParams.json",
        "v2/ThreadListResponse.json",
        "v2/TurnStartParams.json",
        "v2/TurnStartResponse.json",
        "v2/TurnSteerParams.json",
        "v2/TurnSteerResponse.json",
        "v2/TurnInterruptParams.json",
        "v2/TurnInterruptResponse.json",
        "v2/ReviewStartParams.json",
        "v2/ReviewStartResponse.json",
    )
    _NOTIFICATION_SCHEMA_FILES = (
        "v2/ErrorNotification.json",
        "v2/WarningNotification.json",
        "v2/DeprecationNoticeNotification.json",
        "v2/ThreadStartedNotification.json",
        "v2/ThreadStatusChangedNotification.json",
        "v2/ThreadClosedNotification.json",
        "v2/TurnStartedNotification.json",
        "v2/TurnCompletedNotification.json",
        "v2/TurnDiffUpdatedNotification.json",
        "v2/TurnPlanUpdatedNotification.json",
        "v2/ItemStartedNotification.json",
        "v2/ItemCompletedNotification.json",
        "v2/AgentMessageDeltaNotification.json",
        "v2/PlanDeltaNotification.json",
        "v2/ReasoningSummaryTextDeltaNotification.json",
    )
    _CALLBACK_SCHEMA_FILES = (
        "CommandExecutionRequestApprovalParams.json",
        "CommandExecutionRequestApprovalResponse.json",
        "FileChangeRequestApprovalParams.json",
        "FileChangeRequestApprovalResponse.json",
        "ToolRequestUserInputParams.json",
        "ToolRequestUserInputResponse.json",
    )
    _PUBLIC_SCHEMA_FILES = (
        *_OPERATION_SCHEMA_FILES,
        *_NOTIFICATION_SCHEMA_FILES,
        *_CALLBACK_SCHEMA_FILES,
    )
    _INTERNAL_SCHEMA_FILES = ("v1/InitializeParams.json", "v1/InitializeResponse.json")
    _INBOUND_SCHEMA_FILES = (
        *(path for path in _OPERATION_SCHEMA_FILES if path.endswith("Response.json")),
        *_NOTIFICATION_SCHEMA_FILES,
        *(path for path in _CALLBACK_SCHEMA_FILES if path.endswith("Params.json")),
        "v1/InitializeResponse.json",
    )
    _PUBLIC_MODEL_NAMES = tuple(
        path.removeprefix("v2/").removesuffix(".json") for path in _PUBLIC_SCHEMA_FILES
    )
    _INTEGER_FORMAT_BOUNDS = MappingProxyType(
        {
            "int32": (-(2**31), 2**31 - 1),
            "int64": (-(2**63), 2**63 - 1),
            "uint": (0, 2**64 - 1),
            "uint16": (0, 2**16 - 1),
            "uint32": (0, 2**32 - 1),
            "uint64": (0, 2**64 - 1),
        }
    )
    _ALLOW_OMITTED_ADDITIONAL = ContextVar("allow_omitted_additional", default=False)

    class _ModelValidationError(ValueError):
        """Content-free selected-schema model validation failure."""

    def _freeze_json(value: object, path: str) -> object:
        if value is None or isinstance(value, (bool, int, float, str, StrEnum)):
            return value
        if isinstance(value, _SchemaModel):
            return value
        if isinstance(value, Mapping):
            return FrozenJsonObject(value, _path=path)
        if isinstance(value, (list, tuple)):
            return tuple(_freeze_json(item, f"{path}[]") for item in value)
        raise _ModelValidationError(f"{path} contains a non-JSON value")

    class FrozenJsonObject(Mapping[str, object]):
        """Deeply immutable JSON object used only where the schema permits openness."""

        __slots__ = ("_items", "_lookup")

        def __init__(
            self, value: Mapping[str, object] | None = None, *, _path: str = "object"
        ) -> None:
            source = value or {}
            if not all(isinstance(key, str) for key in source):
                raise _ModelValidationError(f"{_path} contains a non-string key")
            items = tuple(
                (key, _freeze_json(item, f"{_path}.{key}")) for key, item in source.items()
            )
            self._items = items
            self._lookup = dict(items)

        def __getitem__(self, key: str) -> object:
            return self._lookup[key]

        def __iter__(self) -> Iterator[str]:
            return iter(self._lookup)

        def __len__(self) -> int:
            return len(self._lookup)

        def __repr__(self) -> str:
            return f"FrozenJsonObject(keys={tuple(self._lookup)})"

    JsonValue = None | bool | int | float | str | tuple["JsonValue", ...] | FrozenJsonObject

    class _SchemaModel:
        __slots__ = ()

        _schema_name: str

        @classmethod
        def from_dict(cls, value: Mapping[str, object]) -> Self:
            spec = _SPECS[cls._schema_name]
            decoded = _decode_named(
                cls._schema_name,
                value,
                cls._schema_name,
                allow_omitted_additional=_is_exclusively_inbound(spec),
            )
            if not isinstance(decoded, cls):
                raise _ModelValidationError(f"{cls.__name__} did not decode to its frozen class")
            return decoded

        def to_dict(self) -> dict[str, object]:
            spec = _SPECS[self._schema_name]
            return _model_to_dict(
                self,
                allow_omitted_additional=_is_exclusively_inbound(spec),
            )

    @dataclass(frozen=True, slots=True)
    class _ModelSpec:
        name: str
        schema: Mapping[str, object]
        root: Mapping[str, object]
        source: str
        sources: frozenset[str]
        canonical: str

    def _allows_additional_properties(spec: _ModelSpec) -> bool:
        if "additionalProperties" in spec.schema:
            return spec.schema["additionalProperties"] is not False
        return not spec.sources.isdisjoint(_INBOUND_SCHEMA_FILES)

    def _is_exclusively_inbound(spec: _ModelSpec) -> bool:
        return bool(spec.sources) and spec.sources.issubset(_INBOUND_SCHEMA_FILES)

    def _collect_model_specs(
        documents: Mapping[str, Mapping[str, object]],
    ) -> dict[str, _ModelSpec]:
        specs: dict[str, _ModelSpec] = {}
        visited_refs: set[tuple[str, str]] = set()

        def register(
            name: str,
            schema: Mapping[str, object],
            root: Mapping[str, object],
            source: str,
        ) -> None:
            if not name.isidentifier():
                raise _ModelValidationError(f"selected schema has an invalid model name: {name!r}")
            candidate = _ModelSpec(
                name,
                schema,
                root,
                source,
                frozenset({source}),
                json.dumps(schema, sort_keys=True, separators=(",", ":")),
            )
            prior = specs.get(name)
            if prior is not None:
                if prior.canonical != candidate.canonical:
                    raise _ModelValidationError(
                        f"selected schemas define unequal models with the same name: {name}"
                    )
                specs[name] = replace(prior, sources=prior.sources | {source})
                return
            specs[name] = candidate

        def visit(node: object, root: Mapping[str, object], source: str) -> None:
            if isinstance(node, (list, tuple)):
                for item in node:
                    visit(item, root, source)
                return
            if not isinstance(node, Mapping):
                return
            title = node.get("title")
            if isinstance(title, str) and (
                node.get("enum") is not None or node.get("type") == "object" or "properties" in node
            ):
                register(title, node, root, source)
            reference = node.get("$ref")
            if isinstance(reference, str) and reference.startswith("#/definitions/"):
                name = reference.removeprefix("#/definitions/")
                marker = (source, name)
                if marker not in visited_refs:
                    visited_refs.add(marker)
                    definitions = root.get("definitions")
                    if not isinstance(definitions, Mapping) or not isinstance(
                        definitions.get(name), Mapping
                    ):
                        raise _ModelValidationError(
                            f"selected schema references missing model: {name}"
                        )
                    definition = definitions[name]
                    register(name, definition, root, source)
                    visit(definition, root, source)
            for key, child in node.items():
                if key not in {"$ref", "definitions"}:
                    visit(child, root, source)

        for source, root in documents.items():
            title = root.get("title")
            if not isinstance(title, str):
                raise _ModelValidationError(f"selected schema document has no title: {source}")
            top = {key: value for key, value in root.items() if key != "definitions"}
            register(title, top, root, source)
            visit(top, root, source)

        initialize = documents["v1/InitializeParams.json"]
        definitions = initialize.get("definitions")
        client_info = definitions.get("ClientInfo") if isinstance(definitions, Mapping) else None
        if not isinstance(client_info, Mapping):
            raise _ModelValidationError("initialize schema has no ClientInfo definition")
        register("ClientIdentity", client_info, initialize, "v1/InitializeParams.json")
        return specs

    def _load_documents() -> dict[str, Mapping[str, object]]:
        root = schema_root
        return {
            path: _load_json(root.joinpath(path), f"selected model schema {path}")
            for path in (*_PUBLIC_SCHEMA_FILES, *_INTERNAL_SCHEMA_FILES)
        }

    _DOCUMENTS = _load_documents()
    _SPECS = _collect_model_specs(_DOCUMENTS)
    _RUNTIME_TYPES: dict[str, object] = {}

    def _is_object_schema(schema: Mapping[str, object]) -> bool:
        return schema.get("type") == "object" or "properties" in schema

    def _object_constraints(
        schema: Mapping[str, object], root: Mapping[str, object]
    ) -> tuple[dict[str, object], tuple[str, ...]]:
        """Collect fields without treating an alternative as a replacement parent.

        Omitted additionalProperties is deliberately closed for outbound models.
        Recognized fields from sibling alternatives still belong to that closed
        field set, so an anyOf may retain more than one valid alternative.
        """
        properties = schema.get("properties", {})
        required = schema.get("required", ())
        if not isinstance(properties, Mapping) or not isinstance(required, (list, tuple)):
            raise _ModelValidationError("selected schema has malformed object constraints")
        combined = dict(properties)
        mandatory = list(required)
        for keyword in ("allOf", "anyOf", "oneOf"):
            variants = schema.get(keyword, ())
            if not isinstance(variants, (list, tuple)):
                raise _ModelValidationError("selected schema has malformed composition constraints")
            for variant in variants:
                if not isinstance(variant, Mapping):
                    continue
                reference = variant.get("$ref")
                if isinstance(reference, str) and reference.startswith("#/definitions/"):
                    definitions = root.get("definitions", {})
                    variant = definitions.get(reference.removeprefix("#/definitions/"), {})
                if not isinstance(variant, Mapping) or not _is_object_schema(variant):
                    continue
                child_properties, child_required = _object_constraints(variant, root)
                for name, child in child_properties.items():
                    if name in combined and combined[name] != child:
                        combined[name] = {"allOf": (combined[name], child)}
                    else:
                        combined[name] = child
                if keyword == "allOf":
                    mandatory.extend(child_required)
        return combined, tuple(dict.fromkeys(mandatory))

    def _validate_object_composition(
        schema: Mapping[str, object],
        root: Mapping[str, object],
        value: Mapping[str, object],
        path: str,
        *,
        allow_omitted_additional: bool,
    ) -> None:
        for keyword in ("allOf", "anyOf", "oneOf"):
            variants = schema.get(keyword)
            if not isinstance(variants, (list, tuple)):
                continue
            if not variants:
                raise _ModelValidationError(f"{path} has an empty {keyword}")
            if schema.get("additionalProperties") is False and set(value).difference(
                schema.get("properties", {})
            ):
                raise _ModelValidationError(f"{path} contains unselected parent fields")
            matches = 0
            for variant in variants:
                candidate = value
                resolved = variant
                if isinstance(variant, Mapping):
                    reference = variant.get("$ref")
                    if isinstance(reference, str) and reference.startswith("#/definitions/"):
                        resolved = root.get("definitions", {}).get(
                            reference.removeprefix("#/definitions/"), variant
                        )
                if (
                    isinstance(resolved, Mapping)
                    and _is_object_schema(resolved)
                    and "additionalProperties" not in resolved
                ):
                    # Parent/sibling fields are checked once by the enclosing
                    # composite object; each branch checks its own constraints.
                    child_properties, _ = _object_constraints(resolved, root)
                    candidate = {
                        key: item for key, item in value.items() if key in child_properties
                    }
                try:
                    _decode(
                        variant,
                        root,
                        candidate,
                        path,
                        allow_omitted_additional=allow_omitted_additional,
                    )
                except _ModelValidationError:
                    continue
                matches += 1
            if (
                (keyword == "allOf" and matches != len(variants))
                or (keyword == "anyOf" and matches == 0)
                or (keyword == "oneOf" and matches != 1)
            ):
                raise _ModelValidationError(f"{path} does not satisfy its retained {keyword}")

    def _enum_members(values: list[object]) -> dict[str, str]:
        if not all(isinstance(value, str) for value in values):
            raise _ModelValidationError("selected string enum contains a non-string value")
        members: dict[str, str] = {}
        for value in values:
            base = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").upper() or "VALUE"
            if base[0].isdigit():
                base = f"VALUE_{base}"
            name = base
            suffix = 2
            while name in members and members[name] != value:
                name = f"{base}_{suffix}"
                suffix += 1
            members[name] = value
        return members

    def _annotation(schema: object, root: Mapping[str, object]) -> str:
        if schema is True:
            return "JsonValue"
        if schema is False or not isinstance(schema, Mapping):
            return "object"
        if not schema:
            return "JsonValue"
        reference = schema.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/definitions/"):
            return reference.removeprefix("#/definitions/")
        title = schema.get("title")
        if isinstance(title, str) and title in _SPECS:
            return title
        variants = schema.get("oneOf", schema.get("anyOf"))
        if isinstance(variants, (list, tuple)):
            return " | ".join(dict.fromkeys(_annotation(item, root) for item in variants))
        all_of = schema.get("allOf")
        if isinstance(all_of, (list, tuple)) and all_of:
            return _annotation(all_of[0], root)
        enum = schema.get("enum")
        if isinstance(enum, (list, tuple)):
            return "Literal[" + ", ".join(repr(value) for value in enum) + "]"
        expected = schema.get("type")
        if isinstance(expected, (list, tuple)):
            return " | ".join(dict.fromkeys(_annotation({"type": item}, root) for item in expected))
        if expected == "null":
            return "None"
        if expected == "boolean":
            return "bool"
        if expected == "integer":
            return "int"
        if expected == "number":
            return "int | float"
        if expected == "string":
            return "str"
        if expected == "array":
            return f"tuple[{_annotation(schema.get('items', True), root)}, ...]"
        if expected == "object" or "properties" in schema:
            return "FrozenJsonObject"
        return "object"

    def _model_post_init(self: _SchemaModel) -> None:
        spec = _SPECS[self._schema_name]
        properties, required = _object_constraints(spec.schema, spec.root)
        if not isinstance(properties, Mapping) or not isinstance(required, (list, tuple)):
            raise _ModelValidationError(f"{self._schema_name} has malformed object constraints")
        for name, child_schema in properties.items():
            value = getattr(self, name)
            if name not in required and value is None:
                continue
            normalized = _decode(
                child_schema,
                spec.root,
                value,
                f"{self._schema_name}.{name}",
                allow_omitted_additional=_ALLOW_OMITTED_ADDITIONAL.get(),
            )
            object.__setattr__(self, name, normalized)
        if hasattr(self, "additional_properties"):
            extras = self.additional_properties
            if not isinstance(extras, Mapping):
                raise _ModelValidationError(
                    f"{self._schema_name}.additional_properties must be a mapping"
                )
            overlap = set(extras).intersection(properties)
            if overlap:
                raise _ModelValidationError(
                    f"{self._schema_name}.additional_properties repeats declared fields"
                )
            additional_schema = spec.schema.get("additionalProperties", True)
            normalized = {
                key: _decode(
                    additional_schema if isinstance(additional_schema, Mapping) else True,
                    spec.root,
                    value,
                    f"{self._schema_name}.{key}",
                )
                for key, value in extras.items()
            }
            object.__setattr__(self, "additional_properties", FrozenJsonObject(normalized))
        if any(key in spec.schema for key in ("allOf", "anyOf", "oneOf")):
            value = {
                name: getattr(self, name)
                for name in properties
                if name in required or getattr(self, name) is not None
            }
            if hasattr(self, "additional_properties"):
                value.update(self.additional_properties)
            _validate_object_composition(
                spec.schema,
                spec.root,
                value,
                self._schema_name,
                allow_omitted_additional=_ALLOW_OMITTED_ADDITIONAL.get(),
            )

    def _make_models() -> None:
        for name, spec in _SPECS.items():
            enum = spec.schema.get("enum")
            if isinstance(enum, (list, tuple)):
                enum_type = StrEnum(name, _enum_members(enum), module=module_name)
                namespace[name] = enum_type
                _RUNTIME_TYPES[name] = enum_type

        for name, spec in _SPECS.items():
            if name in _RUNTIME_TYPES or not _is_object_schema(spec.schema):
                continue
            properties, required = _object_constraints(spec.schema, spec.root)
            if not isinstance(properties, Mapping) or not isinstance(required, (list, tuple)):
                raise _ModelValidationError(f"{name} has malformed object constraints")
            model_fields: list[tuple[Any, ...]] = []
            property_order = (
                ("name", "version", "title") if name == "ClientIdentity" else tuple(properties)
            )
            for property_name in property_order:
                child_schema = properties[property_name]
                annotation = _annotation(child_schema, spec.root)
                if property_name in required:
                    model_fields.append((property_name, annotation))
                else:
                    if "None" not in annotation.split(" | "):
                        annotation = f"{annotation} | None"
                    model_fields.append((property_name, annotation, field(default=None)))
            if _allows_additional_properties(spec):
                if "additional_properties" in properties:
                    raise _ModelValidationError(f"{name} conflicts with the open-object field name")
                model_fields.append(
                    (
                        "additional_properties",
                        "FrozenJsonObject",
                        field(default_factory=FrozenJsonObject, repr=False),
                    )
                )
            model = make_dataclass(
                name,
                model_fields,
                bases=(_SchemaModel,),
                namespace={
                    "__module__": module_name,
                    "__doc__": f"Frozen model for the retained {name} schema.",
                    "_schema_name": name,
                    "__post_init__": _model_post_init,
                },
                frozen=True,
                slots=True,
                kw_only=name != "ClientIdentity",
            )
            # Python 3.12+ infers its caller module after applying namespace.
            # Set this explicitly afterward while retaining Python 3.11 support.
            model.__module__ = module_name
            namespace[name] = model
            _RUNTIME_TYPES[name] = model

        for name in _SPECS:
            if name not in _RUNTIME_TYPES:
                alias = _runtime_type(_SPECS[name].schema, _SPECS[name].root, resolving={name})
                namespace[name] = alias
                _RUNTIME_TYPES[name] = alias

    def _union_type(types: list[object]) -> object:
        unique: list[object] = []
        for item in types:
            if item not in unique:
                unique.append(item)
        if not unique:
            return object
        result = unique[0]
        for item in unique[1:]:
            result = operator.or_(result, item)
        return result

    def _runtime_type(
        schema: object,
        root: Mapping[str, object],
        *,
        resolving: set[str] | None = None,
    ) -> object:
        resolving = set() if resolving is None else resolving
        if schema is True:
            return JsonValue
        if schema is False or not isinstance(schema, Mapping):
            return object
        if not schema:
            return JsonValue
        reference = schema.get("$ref")
        if isinstance(reference, str) and reference.startswith("#/definitions/"):
            name = reference.removeprefix("#/definitions/")
            if name in _RUNTIME_TYPES:
                return _RUNTIME_TYPES[name]
            if name in resolving:
                return object
            spec = _SPECS[name]
            return _runtime_type(spec.schema, spec.root, resolving=resolving | {name})
        title = schema.get("title")
        if isinstance(title, str) and title in _RUNTIME_TYPES:
            return _RUNTIME_TYPES[title]
        variants = schema.get("oneOf", schema.get("anyOf"))
        if isinstance(variants, (list, tuple)):
            return _union_type(
                [_runtime_type(item, root, resolving=resolving) for item in variants]
            )
        all_of = schema.get("allOf")
        if isinstance(all_of, (list, tuple)) and all_of:
            return _runtime_type(all_of[0], root, resolving=resolving)
        enum = schema.get("enum")
        if isinstance(enum, (list, tuple)):
            return Literal[tuple(enum)]
        expected = schema.get("type")
        if isinstance(expected, (list, tuple)):
            return _union_type(
                [_runtime_type({"type": item}, root, resolving=resolving) for item in expected]
            )
        if expected == "null":
            return type(None)
        if expected == "boolean":
            return bool
        if expected == "integer":
            return int
        if expected == "number":
            return int | float
        if expected == "string":
            return str
        if expected == "array":
            return tuple[_runtime_type(schema.get("items", True), root, resolving=resolving), ...]
        if expected == "object" or "properties" in schema:
            return FrozenJsonObject
        return object

    def _decode_named(
        name: str,
        value: object,
        path: str,
        *,
        allow_omitted_additional: bool = False,
    ) -> object:
        runtime_type = _RUNTIME_TYPES.get(name)
        if isinstance(runtime_type, type) and isinstance(value, runtime_type):
            return value
        spec = _SPECS.get(name)
        if spec is None:
            raise _ModelValidationError(f"{path} references an unavailable frozen model")
        return _decode(
            spec.schema,
            spec.root,
            value,
            path,
            expected_name=name,
            allow_omitted_additional=allow_omitted_additional,
        )

    def _decode(
        schema: object,
        root: Mapping[str, object],
        value: object,
        path: str,
        *,
        expected_name: str | None = None,
        allow_omitted_additional: bool = False,
    ) -> object:
        if schema is True:
            return _freeze_json(value, path)
        if schema is False or not isinstance(schema, Mapping):
            raise _ModelValidationError(f"{path} is forbidden by the retained schema")
        if not schema:
            return _freeze_json(value, path)
        reference = schema.get("$ref")
        if isinstance(reference, str):
            if not reference.startswith("#/definitions/"):
                raise _ModelValidationError(f"{path} uses an unsupported schema reference")
            return _decode_named(
                reference.removeprefix("#/definitions/"),
                value,
                path,
                allow_omitted_additional=allow_omitted_additional,
            )
        title = schema.get("title")
        if expected_name is None and isinstance(title, str) and title in _SPECS:
            return _decode_named(
                title,
                value,
                path,
                allow_omitted_additional=allow_omitted_additional,
            )
        if _is_object_schema(schema):
            return _decode_object(
                schema,
                root,
                value,
                path,
                expected_name=expected_name,
                allow_omitted_additional=allow_omitted_additional,
            )
        all_of = schema.get("allOf")
        if isinstance(all_of, (list, tuple)):
            if not all_of:
                raise _ModelValidationError(f"{path} has an empty allOf")
            decoded = _decode(
                all_of[0],
                root,
                value,
                path,
                allow_omitted_additional=allow_omitted_additional,
            )
            for item in all_of[1:]:
                _decode(
                    item,
                    root,
                    value,
                    path,
                    allow_omitted_additional=allow_omitted_additional,
                )
            return decoded
        variants = schema.get("oneOf")
        if isinstance(variants, (list, tuple)):
            matches: list[object] = []
            for item in variants:
                try:
                    matches.append(
                        _decode(
                            item,
                            root,
                            value,
                            path,
                            allow_omitted_additional=allow_omitted_additional,
                        )
                    )
                except _ModelValidationError:
                    continue
            if len(matches) != 1:
                raise _ModelValidationError(f"{path} does not match exactly one closed variant")
            return matches[0]
        variants = schema.get("anyOf")
        if isinstance(variants, (list, tuple)):
            for item in variants:
                try:
                    return _decode(
                        item,
                        root,
                        value,
                        path,
                        allow_omitted_additional=allow_omitted_additional,
                    )
                except _ModelValidationError:
                    pass
            raise _ModelValidationError(f"{path} does not match a closed variant")
        enum = schema.get("enum")
        if isinstance(enum, (list, tuple)):
            if value not in enum:
                raise _ModelValidationError(f"{path} is not a selected enum value")
            if expected_name is not None:
                enum_type = _RUNTIME_TYPES.get(expected_name)
                if isinstance(enum_type, type) and issubclass(enum_type, StrEnum):
                    return enum_type(value)
            return value
        expected = schema.get("type")
        if isinstance(expected, (list, tuple)):
            for item in expected:
                try:
                    return _decode(
                        {**schema, "type": item},
                        root,
                        value,
                        path,
                        allow_omitted_additional=allow_omitted_additional,
                    )
                except _ModelValidationError:
                    pass
            raise _ModelValidationError(f"{path} has the wrong closed JSON type")
        if expected == "null":
            if value is not None:
                raise _ModelValidationError(f"{path} must be null")
            return None
        if expected == "boolean":
            if not isinstance(value, bool):
                raise _ModelValidationError(f"{path} must be boolean")
            return value
        if expected == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise _ModelValidationError(f"{path} must be integer")
            _validate_number_constraints(schema, value, path)
            return value
        if expected == "number":
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise _ModelValidationError(f"{path} must be number")
            _validate_number_constraints(schema, value, path)
            return value
        if expected == "string":
            if not isinstance(value, str):
                raise _ModelValidationError(f"{path} must be string")
            minimum = schema.get("minLength")
            if isinstance(minimum, int) and len(value) < minimum:
                raise _ModelValidationError(f"{path} is shorter than the retained minimum")
            pattern = schema.get("pattern")
            if isinstance(pattern, str) and re.search(pattern, value) is None:
                raise _ModelValidationError(f"{path} does not match the retained pattern")
            return value
        if expected == "array":
            if not isinstance(value, (list, tuple)):
                raise _ModelValidationError(f"{path} must be array")
            return tuple(
                _decode(
                    schema.get("items", True),
                    root,
                    item,
                    f"{path}[]",
                    allow_omitted_additional=allow_omitted_additional,
                )
                for item in value
            )
        if expected == "object" or "properties" in schema:
            return _decode_object(
                schema,
                root,
                value,
                path,
                expected_name=expected_name,
                allow_omitted_additional=allow_omitted_additional,
            )
        raise _ModelValidationError(f"{path} has an unsupported retained schema shape")

    def _validate_number_constraints(
        schema: Mapping[str, object], value: int | float, path: str
    ) -> None:
        integer_format = schema.get("format")
        if integer_format in _INTEGER_FORMAT_BOUNDS:
            lower, upper = _INTEGER_FORMAT_BOUNDS[integer_format]
            if value < lower or value > upper:
                raise _ModelValidationError(
                    f"{path} is outside the retained {integer_format} range"
                )
        minimum = schema.get("minimum")
        if isinstance(minimum, (int, float)) and value < minimum:
            raise _ModelValidationError(f"{path} is below the retained minimum")
        maximum = schema.get("maximum")
        if isinstance(maximum, (int, float)) and value > maximum:
            raise _ModelValidationError(f"{path} is above the retained maximum")

    def _decode_object(
        schema: Mapping[str, object],
        root: Mapping[str, object],
        value: object,
        path: str,
        *,
        expected_name: str | None,
        allow_omitted_additional: bool,
    ) -> object:
        if not isinstance(value, Mapping) or not all(isinstance(key, str) for key in value):
            raise _ModelValidationError(f"{path} must be an object with string keys")
        properties, required = _object_constraints(schema, root)
        missing = [name for name in required if name not in value]
        if missing:
            raise _ModelValidationError(f"{path} is missing required fields")
        unknown = set(value).difference(properties)
        additional = schema.get("additionalProperties", False)
        if "additionalProperties" not in schema and allow_omitted_additional:
            additional = True
        if unknown and additional is False:
            raise _ModelValidationError(f"{path} contains unselected fields")
        _validate_object_composition(
            schema,
            root,
            value,
            path,
            allow_omitted_additional=allow_omitted_additional,
        )
        decoded = {
            name: _decode(
                child_schema,
                root,
                value[name],
                f"{path}.{name}",
                allow_omitted_additional=allow_omitted_additional,
            )
            for name, child_schema in properties.items()
            if name in value
        }
        extras = {
            name: _decode(
                additional if isinstance(additional, Mapping) else True,
                root,
                value[name],
                f"{path}.{name}",
                allow_omitted_additional=allow_omitted_additional,
            )
            for name in unknown
        }
        if expected_name is not None:
            runtime_type = _RUNTIME_TYPES.get(expected_name)
            if isinstance(runtime_type, type) and issubclass(runtime_type, _SchemaModel):
                if additional is not False:
                    decoded["additional_properties"] = FrozenJsonObject(extras)
                token = _ALLOW_OMITTED_ADDITIONAL.set(allow_omitted_additional)
                try:
                    return runtime_type(**decoded)
                finally:
                    _ALLOW_OMITTED_ADDITIONAL.reset(token)
        return FrozenJsonObject({**decoded, **extras}, _path=path)

    def _model_to_dict(
        model: _SchemaModel,
        *,
        allow_omitted_additional: bool = False,
    ) -> dict[str, object]:
        spec = _SPECS[model._schema_name]
        properties, required = _object_constraints(spec.schema, spec.root)
        result: dict[str, object] = {}
        for item in fields(model):
            if item.name == "additional_properties":
                continue
            value = getattr(model, item.name)
            if item.name not in required and value is None:
                continue
            result[item.name] = _to_json(
                value,
                allow_omitted_additional=allow_omitted_additional,
            )
        if hasattr(model, "additional_properties"):
            additional = spec.schema.get("additionalProperties", False)
            if "additionalProperties" not in spec.schema and allow_omitted_additional:
                additional = True
            if model.additional_properties and additional is False:
                raise _ModelValidationError(
                    f"{model._schema_name} contains outbound-unselected fields"
                )
            for key, value in model.additional_properties.items():
                if key in properties:
                    raise _ModelValidationError(
                        f"{model._schema_name} has an extra-field collision"
                    )
                result[key] = _to_json(
                    value,
                    allow_omitted_additional=allow_omitted_additional,
                )
        return result

    def _to_json(value: object, *, allow_omitted_additional: bool = False) -> object:
        if isinstance(value, _SchemaModel):
            return _model_to_dict(
                value,
                allow_omitted_additional=allow_omitted_additional,
            )
        if isinstance(value, StrEnum):
            return value.value
        if isinstance(value, FrozenJsonObject):
            return {
                key: _to_json(
                    item,
                    allow_omitted_additional=allow_omitted_additional,
                )
                for key, item in value.items()
            }
        if isinstance(value, tuple):
            return [
                _to_json(item, allow_omitted_additional=allow_omitted_additional) for item in value
            ]
        if value is None or isinstance(value, (bool, int, float, str)):
            return value
        raise _ModelValidationError("model contains a non-JSON value")

    def _decode_document(source: str, value: object) -> _SchemaModel:
        root = _DOCUMENTS[source]
        title = root.get("title")
        if not isinstance(title, str):
            raise _ModelValidationError("selected document has no model title")
        decoded = _decode_named(
            title,
            value,
            title,
            allow_omitted_additional=source in _INBOUND_SCHEMA_FILES,
        )
        if not isinstance(decoded, _SchemaModel):
            raise _ModelValidationError(f"{title} did not decode to an immutable model")
        return decoded

    _make_models()

    # Everything used by a decoder remains bound to this schema graph. Exposed
    # maps and schema trees are read-only, including their nested containers.
    _DOCUMENTS = _freeze_schema(_DOCUMENTS)
    _SPECS = MappingProxyType(
        {
            name: _ModelSpec(
                spec.name,
                _freeze_schema(spec.schema),
                _DOCUMENTS[spec.source],
                spec.source,
                spec.sources,
                spec.canonical,
            )
            for name, spec in _SPECS.items()
        }
    )
    _RUNTIME_TYPES = MappingProxyType(_RUNTIME_TYPES)
    for helper in (_ModelValidationError, FrozenJsonObject, _SchemaModel):
        helper.__module__ = module_name
        helper.__qualname__ = helper.__name__
    namespace.update({name: value for name, value in locals().items() if name.startswith("_")})
    namespace.update(FrozenJsonObject=FrozenJsonObject, JsonValue=JsonValue, Literal=Literal)
    namespace["__all__"] = list(("ClientIdentity", *_PUBLIC_MODEL_NAMES))
    return MappingProxyType(namespace)
