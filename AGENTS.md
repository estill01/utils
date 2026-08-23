# Repository instructions

This repository owns only narrow domain-neutral enabling packages.

- Keep every distribution independently named, versioned, tested, and
  documented. Do not expose a top-level grab-bag `utils` import.
- A package is admitted only when it has two concrete consumers, or one
  existing consumer plus an imminent active second implementation.
- Utilities import none of Software Factory, libRSI, Patent Studio, or their
  domain authorities. Dependency direction is products → utilities.
- Do not move product policy, mission state, QA/supervision/acceptance,
  semantic evidence/improvement records, patent content, product persistence,
  tenancy, billing, or release authority into this repository.
- Shared records are non-authoritative transport/runtime metadata only.
- Use `docs/tracker.md` as the canonical program owner. Authoring a tracker
  does not implement its Blocks.
- Preserve exact protocol/schema compatibility and provide deterministic fake
  servers and consumer conformance tests.
- Do not add a license, publish packages, create a release, or claim open-source
  reuse rights without an explicit license decision and release authority.
