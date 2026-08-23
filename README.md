# estill01 utilities

This repository contains narrow, domain-neutral enabling packages shared by
multiple estill01 products. It is an organizational monorepo, not one
grab-bag `utils` package.

Planned initial distributions:

- `codex-app-server-client`: typed Python process/transport/client support for
  Codex app-server;
- `embedded-service-contract`: small contracts and conformance fixtures for
  equivalent embedded and service hosts; and
- `runtime-manifest`: non-authoritative component, capability, schema, and
  dependency-version manifests.

Software Factory, libRSI, and Patent Studio remain separate products and
authorities. This repository must not contain their domain models, missions,
patent content, QA policy, improvement semantics, persistence schemas, or
product-specific adapters.

The canonical implementation program is [docs/tracker.md](docs/tracker.md).

## Current posture

The repository is public, but no open-source license has been selected yet.
Public visibility is not a grant of reuse rights. The tracker keeps license
selection as an explicit terminal release gate.
