# Package admission record

This is the bounded admission record permitted by `AGENTS.md` and
`docs/tracker.md`. Consumer names establish concrete need only. They are not
runtime dependencies, fixtures, test subjects, acceptance authorities, or
implementation scope.

## Evidence identity

- Repository instructions SHA-256:
  `c27e6934692df8bb600dfa522b1ec4e9be431dfaaf1088a02fce780374dfa7d2`.
- Repository README SHA-256:
  `44639727f096187ae483ec34a08b6b4a49e93ba74bcfcd3575cb194e40cf598d`.
- Tracker source SHA-256:
  `37f68c490bff37451f023c8fc1adedf360a902532e47009b052f109779199d84`.
- Direct full-tracker implementation request SHA-256:
  `28ab86781f82ccfc39d0c5a71a642151d86353ac011bd7852e0a93165998c190`.
- Cross-project coordination source: direct-user instruction transported from
  task `01a02cf9-50b4-7f03-9dd7-8b443b42cb0e`, which identifies Software
  Factory, libRSI, and Patent Studio as external consumers and identifies the
  app-client, embedded/service contract, and runtime-manifest handoff needs.

No consumer repository was cloned, opened, imported, executed, changed, or
tested to produce this record. The direct user evidence is sufficient for the
admission decision and keeps implementation inward-facing.

## Admission decisions

| Distribution | Concrete consumers established by direct coordination | Domain-neutral owner | Six-condition result | Decision |
|---|---|---|---|---|
| `codex-app-server-client` | Software Factory and Patent Studio; libRSI is an additional eligible external consumer | exact Codex app-server compatibility, RPC, local transport, typed session, async, and restart mechanics | neutral; multiple consumers; no product authority; consumer-to-utility dependency; independent API/tests/versioning; removes duplicated protocol mechanics | admitted |
| `embedded-service-contract` | Software Factory and Patent Studio; libRSI is an additional eligible external consumer | structural lifecycle protocols and conformance assertions only | neutral; multiple consumers; no host policy/state; consumer-to-utility dependency; independent API/tests/versioning; removes duplicated host-shape checks | admitted |
| `runtime-manifest` | Software Factory, libRSI, and Patent Studio | caller-supplied descriptive version, root, feature, and dependency compatibility metadata | neutral; multiple consumers; authority-bearing fields excluded; consumer-to-utility dependency; independent API/tests/versioning; removes incompatible manifest encodings | admitted |

No additional distribution or exported primitive is admitted. In particular,
there is no top-level `utils` package, shared daemon, product model, product
registry, scheduler, persistence owner, acceptance record, release authority,
or consumer adapter.

## Condition-by-condition result

Each admitted distribution satisfies all six repository conditions:

1. Its behavior is domain-neutral.
2. Direct coordination establishes at least two concrete external consumers.
3. Product policy, authority, product records, and product persistence are
   outside the representable or executable surface.
4. Dependency direction is external product to independently installed utility.
5. Each distribution has its own API, tests, version, documentation, build,
   and compatibility policy.
6. The narrow owner replaces repeated mechanics without adding cross-product
   coordination or a shared runtime.

## Rejected and deferred candidates

| Candidate | Disposition | Reason |
|---|---|---|
| top-level `utils` import | rejected | violates independent distribution ownership and creates a grab bag |
| common product/runtime service | rejected | would centralize state and operating authority that remain external |
| consumer adapters or pins | rejected | downstream implementation belongs to each consumer program |
| additional future-use helpers | deferred | no independently evidenced admission case |
| license, publication, or release machinery | deferred | requires separate explicit legal and release authority |

There is no unresolved admission question delegated to a later Block.

## Product-capability review

- Trigger: Block 0 has consequential posture.
- Frame identity: `docs/tracker.md`, Block 0, target-product capability frame
  SHA-256
  `b30790e21ab26a17240ee434cf7a356530e8fde0b87e461c5a5db4a7cbbb3952`.
- Capability added or preserved: evidence-based package admission with one
  narrow owner per public contract and no downstream implementation authority.
- Paths compared:
  - smallest local: one repository-wide helper or `utils` namespace; rejected
    because it loses independent packaging and compatibility ownership;
  - bounded-general: a shared runtime/service for the three consumers;
    rejected because the evidence supports contracts, not a runtime authority;
  - architectural owner: the repository's three independent distributions;
    selected because it supplies the complete evidenced capability at the
    lowest eligible complexity.
- Protected-capability result: independent distributions, downstream
  replaceability, one process owner, exact compatibility, and zero consumer
  coupling are preserved by the recorded architecture.
- Tradeoffs and uncertainty: three distributions add build metadata and CI
  jobs; future adoption, license selection, and publication remain external or
  separately authorized facts and do not alter this admission.
- Frozen-candidate proof: to be bound to the accepted Block 0 commit after the
  architecture record and exact-revision audit are complete.
