"""Public app-server client error taxonomy."""


class AppServerClientError(Exception):
    """Base class for every public client failure."""


class CodexBinaryNotFoundError(AppServerClientError):
    """No executable resolved from the explicit path or PATH."""


class AmbiguousCodexBinaryError(AppServerClientError):
    """More than one distinct executable resolved from PATH."""


class CodexVersionError(AppServerClientError):
    """The executable version could not be probed or is incompatible."""


class SchemaMissingError(AppServerClientError):
    """A required schema root, file, or definition is missing."""


class SchemaMalformedError(AppServerClientError):
    """A schema file is not valid JSON or has an invalid structure."""


class SchemaRootMismatchError(AppServerClientError):
    """A byte, semantic, selected-surface, or API root is incompatible."""


class UnsupportedFeatureError(AppServerClientError):
    """A required selected feature is absent from the compatible schema."""


class JsonRpcFramingError(AppServerClientError):
    """A byte-channel record is not one complete JSON-RPC line."""


class JsonRpcValidationError(AppServerClientError):
    """A JSON-RPC envelope does not satisfy the retained official schema."""


class RequestLimitError(AppServerClientError):
    """The bounded pending-request capacity is exhausted."""


class MessageTooLargeError(AppServerClientError):
    """A JSON-RPC line exceeds the configured byte limit."""


class CorrelationError(AppServerClientError):
    """A response cannot be correlated exactly once to a pending request."""


class RemoteRpcError(AppServerClientError):
    """The remote peer returned a validated JSON-RPC error envelope."""

    def __init__(
        self,
        *,
        request_id: int,
        code: int,
        has_data: bool,
    ) -> None:
        super().__init__(f"remote RPC error {code} for request {request_id}")
        self.request_id = request_id
        self.code = code
        self.has_data = has_data


class TransportStartError(AppServerClientError):
    """A selected local transport could not create its one connection."""


class TransportClosedError(AppServerClientError):
    """A byte transport closed or failed while reading or writing."""


class TransportOwnershipError(AppServerClientError):
    """A transport instance was claimed by more than one connection owner."""


class TransportCleanupError(AppServerClientError):
    """A transport could not prove that its owned resources were closed."""
