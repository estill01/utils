# Shared Domain-Neutral Utilities Implementation Tracker

- Tracker status: `implementation`
- Tracker sequence: Blocks 0–16
- Repository: `https://github.com/estill01/utils`
- Governing objective: provide narrow, independently versioned enabling
  packages with neutral internal contracts and conformance proof, without
  implementing, operating, testing, or tracking any downstream consumer.

## 1. Purpose and intended outcome

Create an organizational monorepo of individually named Python distributions:

- `codex-app-server-client` — typed process, transport, and protocol support;
- `embedded-service-contract` — structural lifecycle protocols and conformance
  fixtures for embedded and service hosts; and
- `runtime-manifest` — non-authoritative exact component, protocol, schema,
  capability, and dependency metadata.

Completion means:

- every admitted distribution builds, installs, versions, tests, and documents
  independently;
- the app-server client conforms to one exact official protocol/schema target
  through deterministic in-repository fakes and bounded live-protocol smoke;
- embedded and service reference hosts prove the same neutral lifecycle
  contract without sharing product state or authority;
- runtime manifests bind exact descriptive compatibility metadata without
  representing authorization, acceptance, or product truth;
- isolated and combined package conformance passes entirely inside this
  repository; and
- the repository records a truthful no-license/no-publication posture unless a
  later explicit license and release authority creates a separate successor.

Downstream adoption is not part of this implementation program. No package
source, test, fixture, schema, example, CLI, CI job, or runtime path may import,
invoke, shell into, mutate, pin, launch, or otherwise depend on a downstream
consumer repository. Read-only downstream need may support package admission,
but it cannot become implementation scope or acceptance evidence.

### Mission frame

- Primary outcome: deliver narrow domain-neutral package implementations and
  internal conformance proof with no downstream coupling.
- Observable completion: Blocks 0–16 are accepted at exact current pushed
  revisions; every distribution builds and installs independently; the internal
  compatibility/conformance matrix passes; and the no-downstream-interaction
  audit is clean.
- Ordinary effect classes needed: files, tests, schemas, neutral fixtures,
  package metadata, CI, builds, documentation, commits, and non-force pushes
  inside this repository only.
- Hard direct authority or safety boundaries: utilities cannot own downstream
  adapters, product semantics, missions, QA/supervision/acceptance, semantic
  evidence, patent content, product persistence, credentials, tenancy, billing,
  release authority, or any downstream repository effect; no license,
  publication, or release without separate direct authority.
- Material goal alteration or reversal: adding downstream integration work,
  turning the repository into a common product platform or runtime service,
  introducing a universal model/ledger, or exposing one grab-bag `utils` API.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this tracker creates public package and compatibility
  boundaries even though it does not implement a downstream product feature.
- Direct product sources: repository `AGENTS.md`, repository `README.md`, the
  official Codex app-server protocol/schema selected in Block 2, and the direct
  user instructions that implementation remain inwardly focused and Blocks
  remain independently auditable rather than bloated.
- Product thesis and intended effect: implement proven cross-cutting mechanics
  once behind small transport/runtime contracts while leaving all consumer
  behavior and authority outside the repository.
- Protected capabilities: independent distributions, one process owner per
  composition, exact protocol/schema compatibility, deterministic offline
  conformance, downstream replaceability, and zero consumer coupling.
- Architecture strategy: an organizational monorepo of separately distributed
  packages with one-way internal dependencies and no service of its own.
- Requested capability: typed app-server support, structural embedded/service
  equivalence, and exact non-authoritative runtime metadata.
- Proportionality: implement only admitted package surfaces and neutral proof;
  split only where an outcome has its own mutation, acceptance, or review
  boundary; do not create adapters, product fixtures, orchestration, or
  future-use helpers.
- Tradeoffs: additional Blocks add checkpoints but isolate failures and reviews;
  separate distributions add packaging overhead but keep dependency and
  compatibility boundaries explicit.
- Uncertainty: future downstream adoption, license selection, and publication
  are separate programs and do not block internal technical completion.

## 2. Target architecture and authority boundaries

```text
packages/
  codex-app-server-client/
    compatibility → rpc → transports → session → async → restart safety
  embedded-service-contract/  neutral lifecycle protocols/test fixtures
  runtime-manifest/            descriptive version/compatibility metadata

neutral in-repository fakes and reference hosts
                  │
                  └── prove package isolation and composition

downstream applications import packages under their own programs
utils imports, operates, and tests against no downstream application
```

The app-server client is one distribution with distinct internal owners for
schema compatibility, bounded JSON-RPC state, local transports, typed session
operations, asynchronous coordination, and generation-safe restart. These are
Blocks rather than separate distributions because they compose one client API,
but each has its own acceptance and Stop boundary.

The embedded/service package owns structural conformance protocols and fixtures
only. It does not own a runtime, service runner, product lifecycle, outcome, or
state. The runtime-manifest package owns deterministic descriptive metadata
only. Authorization and acceptance are deliberately absent from its schema.

### External consumer boundary

- Downstream systems may justify admission through read-only evidence.
- Consumer-specific identifiers may appear only in governing repository
  instructions/documentation and a bounded admission record when necessary to
  establish scope or prove the admission rule; they do not appear in package
  source, exported APIs, schemas, fixtures, examples, test data, artifacts, or
  package records.
- This program creates no downstream branch, adapter, pin, migration, test run,
  handoff requirement, cutover, deletion, or acceptance claim.
- An accepted package Block emits an inert, repository-owned package record
  containing the exact pushed source revision, distribution/version,
  artifact/root, public API root, compatibility inputs, currentness proof, and
  qualification posture. Producing that record is internal package evidence;
  it does not operate a consumer, select a consumer pin, or authorize adoption.
- Downstream repositories own every later adoption and all resulting behavior,
  authority, persistence, and release effects.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Codex app-server protocol | exact official CLI/source/schema selected in Block 2 | reference and pin; do not fork protocol semantics |
| App-server schema compatibility | `codex-app-server-client` compatibility layer | own version/schema proof only |
| JSON-RPC request state | `codex-app-server-client` RPC layer | own framing, correlation, bounds, and errors |
| Process and socket transport | `codex-app-server-client` transport layer | own bytes and explicit connection/process lifecycle |
| Typed app-server behavior | `codex-app-server-client` session/async/restart layers | own generic protocol lifecycle, not product policy |
| Embedded/service structural contract | `embedded-service-contract` | own protocols and conformance fixtures, not host state |
| Runtime compatibility metadata | `runtime-manifest` | own descriptive projections, not authority |
| Package builds and quality | repository package metadata and CI | implement per distribution and in isolated environments |
| Downstream behavior and adoption | each external consumer's own repository | out of scope; never imported, operated, or modified here |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Repository instructions | repository commit `5eeb539` | preserve | 0–16 | execute the atomic inward-only program below |
| Inward-only predecessor tracker | SHA-256 `e5756c006bd66c6f72049d53c7ba09590e1aa0d0b70f24db75a360ac67d2f352` | split and renumber prospectively | 0–16 | preserve the map in Section 7 |
| Official Codex app-server protocol | resolve exact CLI/source revision and generated schema root in Block 2 | reference/pin | 2–9 | freeze supported surface and compatibility policy |
| Existing generic client implementations | resolve any inspected source revisions in Block 2 | adapt selectively as read-only evidence | 2–9 | reimplement only neutral behavior; import or runtime dependency prohibited |
| Downstream adoption needs | record only bounded admission evidence in Block 0 | admission evidence only | 0 | no implementation, test, handoff, or acceptance work here |

## 5. Scope, non-goals, and admission rule

### In scope

- The three named distributions, package-isolated tests/builds, official
  protocol compatibility, deterministic neutral fakes, neutral reference hosts,
  internal composition conformance, documentation, and truthful release posture.

### Out of scope

- Downstream adapters, imports, repository operations, pins, migrations,
  cutovers, deletions, tests, deployment, acceptance, or release work.
- A shared daemon/service, common product model, mission runtime, scheduler,
  QA/supervision system, semantic-evidence model, product database, patent
  schema/content, tenancy/billing, credential manager, logging platform, or
  universal event ledger.

### Admission rule

A new distribution or exported primitive requires all of:

1. domain-neutral behavior;
2. two concrete external consumers, or one current consumer plus an imminent
   active second implementation, proven by read-only admission evidence;
3. no product authority, policy, product record, or product database schema;
4. dependency direction from downstream applications to the utility only;
5. an independent API, tests, versioning, and named compatibility policy; and
6. net reduction in implementation and coordination complexity.

Admission evidence proves need only. It never authorizes consumer-specific
implementation. If a named distribution fails admission, Block 0 records the
finding and the tracker is amended before Block 1; no speculative skeleton or
later Block is credited as complete.

## 6. Block execution contract

1. Execute Blocks 0–16 through the dependency graph below; tracker authoring
   starts no Block.
2. Perform implementation-producing work only in this repository. Official
   upstream protocol generation/smoke is allowed; downstream repository reads
   are bounded to admission/source classification and cannot become validation.
3. Do not clone, import, execute commands in, mutate, pin, or test a downstream
   repository as part of any Block.
4. Mark a Block `in-progress` at its first implementation-producing effect.
5. Before each first candidate, exercise the most discriminating supported
   negative cases. Freeze one candidate, run focused proof, then the mapped
   internal matrix, and obtain one distinct exact-revision audit.
6. On rejection, correct only supported findings and rerun affected proof; a
   second material rejection triggers bounded causal design review.
7. Reuse exact accepted schemas, wheels, fixture roots, and test results after a
   cheap currentness check. Run the complete internal matrix once at the frozen
   terminal candidate.
8. A later Block may extend a deterministic fixture only for its newly owned
   behavior; it must reuse earlier accepted fixture paths and may not rewrite an
   earlier Block's accepted contract silently.
9. Push accepted coherent checkpoints without force. A package build, commit,
   review, or push is nonterminal.
10. Do not add a license, publish to a package index, create a GitHub Release,
    announce availability, or claim reuse rights under this program.

### Decision and continuation contract

- Ordinary package/API choices supported by the frozen contract proceed without
  a user gate.
- Blocks 10 and 11 may proceed independently after Block 1 while the app-server
  chain advances through Blocks 2–9.
- The current release posture is `no-license-selected/unpublished`. Recording
  that truthful posture requires no additional decision and does not grant
  reuse rights.
- A later request to add a license, publish, release, or implement downstream
  adoption is a separate successor with its own authority and scope.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- Package capability ID: `<stable identifier or not-applicable>`
- Distribution/version: `<distribution==version or not-applicable>`
- Artifact/root: `<filename, sha256, content root or not-applicable>`
- Public API root: `<import/API surface root or not-applicable>`
- Compatibility inputs: `<protocol/schema/contract/dependency roots or not-applicable>`
- Package currentness proof: `<remote/ref check and result or not-applicable>`
- Package qualification posture: `<package-accepted/program-qualification-pending, program-qualified, or not-applicable>`
- Official upstream revision/schema root: `<exact version/hash or not-applicable>`
- Inputs: `<internal paths/schemas/hashes>`
- Outputs: `<packages/artifacts/hashes>`
- Focused validation: `<commands/results>`
- Mapped internal validation: `<commands/results>`
- Candidate freeze: `<commit/content root/currentness>`
- Remediation closure: `<finding/change/proof or not-applicable>`
- Independent review: `<distinct reviewer/root>`
- Retained open work: `<items or none>`
- Downstream-interaction audit: `<clean/result>`
- License/release posture: `<no-license-selected/unpublished>`
- Post-block audit: `<accepted/reopened/blocked>`
- Git durability: `<commit/push posture>`
```

## 7. Status and required order

### 2026-08-23 atomicity amendment and numbering map

No predecessor Block had started or accumulated implementation evidence.

| Inward-only predecessor Block | Current disposition |
|---:|---|
| 0 | Split into current Blocks 0–1 |
| 1 | Current Block 2 |
| 2 | Split into current Blocks 3–5 |
| 3 | Split into current Blocks 6–9 |
| 4 | Current Block 10 |
| 5 | Current Block 11 |
| 6 | Split into current Blocks 12–13 |
| 7 | Split into current Blocks 14–15 |
| 8 | Current Block 16 |

For references to the initial 0–9 tracker: initial Blocks 0–1 map to current
Blocks 0–2; initial Block 2 maps to current Blocks 3–9; initial Blocks 3–5 map
to current Blocks 10–13; initial Blocks 6–8 remain removed downstream work; and
initial Block 9 maps to current Blocks 14–16.

Stable package capability labels preserve the former nine-Block coordination
points without re-bloating their implementation:

| Legacy coordination label | Atomic implementation | Accepted package-record milestone |
|---|---|---|
| Former B3 — typed app-server client lifecycle package | Current Blocks 3–9 | Current Block 9 |
| Former B4 — embedded/service structural package | Current Block 10 | Current Block 10 |
| Former B5 — runtime-manifest package | Current Block 11 | Current Block 11 |
| Former B6 — combined-package compatibility | Current Blocks 12–13 | Current Block 13 |
| Former B7 — frozen qualified package set | Current Block 14 | Current Block 14 |
| Former B8 — no-license/unpublished closure | Current Block 16 | Current Block 16 |

The legacy labels are references only. Current Block numbers and dependencies
govern execution.

| Block | Functionality targeted | Depends on | Status |
|---:|---|---:|---|
| 0 | Decide package admission, architecture, ownership, and the no-downstream boundary | — | `accepted` |
| 1 | Create independent package skeletons, version policy, shared development tooling, and CI baseline | 0 | `not-started` |
| 2 | Freeze the exact official Codex app-server protocol surface and public client contract | 1 | `not-started` |
| 3 | Implement exact binary/version resolution and schema compatibility | 2 | `not-started` |
| 4 | Implement bounded JSON-RPC framing, correlation, pending-call state, and protocol errors | 3 | `not-started` |
| 5 | Implement owned stdio, Unix-socket, and injected transport composition | 4 | `not-started` |
| 6 | Implement initialization, feature negotiation, and the narrowed typed operation surface | 5 | `not-started` |
| 7 | Implement notifications, server callbacks, cancellation, timeouts, and disconnect coordination | 6 | `not-started` |
| 8 | Implement generation-bound restart safety and single-process-owner recovery | 7 | `not-started` |
| 9 | Complete and freeze the app-server client distribution and deterministic conformance matrix | 8 | `not-started` |
| 10 | Implement neutral embedded-versus-service lifecycle protocols and fixtures | 1 | `not-started` |
| 11 | Implement deterministic non-authoritative runtime/version manifests | 1 | `not-started` |
| 12 | Prove every distribution builds and installs independently with clean dependency direction | 9–11 | `not-started` |
| 13 | Prove all distributions compose through public APIs in one neutral internal scenario | 12 | `not-started` |
| 14 | Qualify the frozen package set, artifacts, documentation, and complete internal matrix | 13 | `not-started` |
| 15 | Audit the frozen package set for downstream coupling and product/release authority leakage | 14 | `not-started` |
| 16 | Record the no-license/unpublished posture and close without external effects | 15 | `not-started` |

Required order:

```text
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 ┐
    1 → 10                               ├→ 12 → 13 → 14 → 15 → 16
    1 → 11                               ┘
```

## Block 0 — Decide package admission and architecture boundaries

Status: `accepted`

### Objective

Decide which distributions are justified and freeze their ownership,
dependency direction, and no-downstream implementation boundary.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: evidence-based package admission and clear authority
  before repository scaffolding begins.
- Potential capability loss or regression: unsupported packages or vague owners
  could create a grab bag or consumer coupling.
- Protected-capability effect: independent downstream ownership and narrow
  utility scope remain intact.
- Architecture and operating-model effect: establishes the distribution graph
  and one owner for each proposed public contract.
- Tradeoff and source evidence: repository instructions and direct user scope;
  admission proof is required before implementation convenience.

### Inputs and dependencies

- Repository instructions, README, predecessor tracker, and bounded read-only
  admission evidence for each proposed distribution.

### Required work

- Classify each proposed distribution against all six admission conditions.
- Define package purposes, public-boundary owners, permitted internal
  dependencies, and prohibited downstream interactions.
- Record accepted, deferred, and rejected candidates without creating package
  directories or implementation credit.

### Scope and non-goals

- In scope: admission, architecture, ownership, and dependency decisions.
- Not in scope: build metadata, package skeletons, CI, or package behavior.

### Deliverables and recorded state

- Admission record, architecture/ownership contract, internal dependency graph,
  and external-consumer boundary.

### Resource and economy contract

Read and hash each admission source once; no package build, downstream command,
or broad source scan.

### QA and independent review

Review necessity, two-consumer proof, naming, dependency direction, authority
leakage, and whether any candidate is speculative.

### Acceptance

- Every retained distribution satisfies admission and has one narrow owner;
  every excluded candidate has an explicit disposition; no unresolved admission
  question is hidden in later Blocks.

### Negative tests

- Reject one-consumer speculation, product models, common authority, reverse
  imports, top-level `utils`, or a candidate whose independent benefit is not
  greater than its coordination cost.

### Completion evidence

- Repository commit: `58b6d70665c6d7148426c4ff212552f196e09b3e`.
- Package capability ID: not applicable; this Block admits packages but creates
  no package implementation.
- Distribution/version: not applicable.
- Artifact/root: `docs/admission.md` SHA-256
  `9081a492043cf5ab5fc20a660427be7ca5f99930b71c9a85a30f2dc7cc9363cb`;
  `docs/architecture.md` SHA-256
  `08463baa45aeff2badbc70491b8b5534c8599aacdcf964fd73b94fc2b7116b71`.
- Public API root: not applicable.
- Compatibility inputs: repository instructions SHA-256
  `c27e6934692df8bb600dfa522b1ec4e9be431dfaaf1088a02fce780374dfa7d2`
  and tracker frame SHA-256
  `b30790e21ab26a17240ee434cf7a356530e8fde0b87e461c5a5db4a7cbbb3952`.
- Package currentness proof: not applicable.
- Package qualification posture: not applicable.
- Official upstream revision/schema root: not applicable.
- Inputs: `AGENTS.md`, `README.md`, the direct full-tracker request, and bounded
  direct-user cross-project admission evidence; no consumer checkout.
- Outputs: `docs/admission.md` and `docs/architecture.md` at the roots above.
- Focused validation: absence checks for `packages/`, root build metadata, and
  `LICENSE`; exact admission-row and architecture-boundary checks passed.
- Mapped internal validation: full tracker verifier returned Blocks 0–16 with
  zero errors and zero warnings; `git diff --check` passed.
- Candidate freeze: commit
  `58b6d70665c6d7148426c4ff212552f196e09b3e`, tree
  `0be743f9f180f62ae1b7a19a48e3db0c1d6f62a5`; `origin/main` matched.
- Remediation closure: reviewer found one naming-location contradiction at
  `b6e0e0e`; commit `58b6d70` confines consumer identifiers to governing scope
  documentation and the bounded admission record while keeping all package
  implementation and artifacts consumer-neutral.
- Independent review: distinct read-only reviewer `/root/block0_reviewer`
  returned `ACCEPT` for exact commit `58b6d70665c6d7148426c4ff212552f196e09b3e`.
- Product-capability review:
  - Trigger: consequential Block 0 posture.
  - Frame identity: `docs/tracker.md`, Block 0, frame SHA-256
    `b30790e21ab26a17240ee434cf7a356530e8fde0b87e461c5a5db4a7cbbb3952`.
  - Capability added or preserved: evidence-based package admission and one
    narrow owner per public contract without downstream implementation scope.
  - Paths compared: local grab-bag; bounded-general shared runtime; existing
    three-distribution architectural owner.
  - Selected level and owner: the existing three-distribution architecture,
    the lowest-complexity path supplying all evidenced capability.
  - Protected-capability result: independent versioning, downstream
    replaceability, one process owner, exact compatibility, and zero runtime
    consumer coupling preserved.
  - Rejected alternatives: a grab-bag loses isolation; a shared runtime adds
    unsupported state and authority.
  - Tradeoffs and uncertainty: independent metadata/CI overhead accepted;
    downstream adoption, license, and publication remain outside this program.
  - Frozen-candidate proof: exact commit and tree above plus accepted review.
- Retained open work: none in Block 0.
- Downstream-interaction audit: clean; no consumer repository was opened,
  executed, imported, changed, or tested.
- License/release posture: `no-license-selected/unpublished`.
- Post-block audit: `accepted`.
- Git durability: candidate and remediation commits pushed to `origin/main`;
  accepted status is recorded by the next scoped tracker checkpoint.

### Stop

Stop before creating package skeletons, build metadata, or CI.

---

## Block 1 — Establish independent packaging and CI baseline

Status: `not-started`

### Objective

Create buildable independent distribution skeletons and repository quality
tooling without implementing package behavior.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: reproducible independent builds and scoped CI from
  the first implementation change.
- Potential capability loss or regression: shared tooling could accidentally
  become a shared runtime dependency or one combined distribution.
- Protected-capability effect: independent naming, versioning, installation,
  testing, and documentation remain.
- Architecture and operating-model effect: creates the monorepo packaging and
  development-only tooling baseline.
- Tradeoff and source evidence: accepted Block 0 architecture; shared developer
  configuration is allowed only where it does not couple runtime packages.

### Inputs and dependencies

- Accepted Block 0 distribution and dependency contract.

### Required work

- Create package directories, import namespaces, independent build metadata,
  version policy, supported Python baseline, and documentation entry points.
- Add repository development tooling, package-isolated CI jobs, build smoke,
  and changed-test mapping.
- Enforce the absence of a top-level `utils` import and runtime dependency on
  repository-wide development tooling.

### Scope and non-goals

- In scope: skeletons, builds, development tooling, and CI foundation.
- Not in scope: protocol schemas, runtime records, package behavior, or
  downstream fixtures.

### Deliverables and recorded state

- Independently buildable skeleton distributions, CI configuration, version and
  compatibility policy, changed-test map, and package documentation shells.

### Resource and economy contract

Run skeleton build/import smoke per distribution; no behavior suite, upstream
binary, network, or downstream checkout.

### QA and independent review

Review package independence, metadata, namespace isolation, CI selection, and
development-versus-runtime dependency direction.

### Acceptance

- Every admitted skeleton builds and imports independently; CI can select each
  package; shared tooling is development-only; no `utils` namespace exists.

### Negative tests

- Reject one combined wheel, shared runtime dependency without admission,
  cross-package undeclared import, top-level `utils`, or CI that requires a
  downstream repository.

### Completion evidence

Pending.

### Stop

Stop before generating protocol schemas or implementing package behavior.

---

## Block 2 — Freeze the official app-server protocol and client contract

Status: `not-started`

### Objective

Bind one exact official app-server protocol/schema target and define the
domain-neutral public client surface before implementation.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: protocol fidelity and a reviewable public API.
- Potential capability loss or regression: an overbroad API could expose raw
  methods or freeze unstable upstream behavior.
- Protected-capability effect: exact compatibility, explicit process ownership,
  and downstream adapter freedom remain.
- Architecture and operating-model effect: freezes the contracts implemented by
  Blocks 3–9.
- Tradeoff and source evidence: official generated schemas and current CLI
  behavior; a narrowed surface is preferred to a general raw RPC bridge.

### Inputs and dependencies

- Block 1 and an exact official Codex CLI/source revision.

### Required work

- Generate and hash the official schemas in a disposable directory.
- Select stable methods, notifications, callbacks, transports, errors, and
  capability probes required by the package objective.
- Define the public Python API, compatibility rule, and deterministic update
  procedure.
- Classify inspected prior implementations only as neutral behavior or excluded
  product behavior; copy no consumer API or type.

### Scope and non-goals

- In scope: official source/schema contract and public package design.
- Not in scope: package behavior, raw arbitrary methods, WebSocket baseline,
  remote public proxying, or consumer behavior.

### Deliverables and recorded state

- Upstream manifest, schema root, supported-feature matrix, public API contract,
  compatibility/update policy, and proof map for Blocks 3–9.

### Resource and economy contract

Generate official schemas once, reuse the root, and perform bounded static
classification before implementation review.

### QA and independent review

Review upstream fidelity, public-surface minimality, schema currentness,
transport selection, and absence of product semantics.

### Acceptance

- The exact upstream target and supported surface are reproducible; every
  exported capability is necessary; Blocks 3–9 have unambiguous ownership and
  Stop boundaries.

### Negative tests

- Reject unpinned schemas, arbitrary RPC escape hatch, unstable baseline
  feature, product type, hidden process owner, or undocumented compatibility
  change.

### Completion evidence

Pending.

### Stop

Stop before implementing compatibility or client code.

---

## Block 3 — Implement app-server version and schema compatibility

Status: `not-started`

### Objective

Implement the exact binary/version and generated-schema compatibility owner
without starting transport or request lifecycle work.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: fail-closed, reproducible compatibility checks.
- Potential capability loss or regression: schema drift or loose version rules
  could silently enable unsupported behavior.
- Protected-capability effect: official protocol fidelity and exact feature
  availability remain explicit.
- Architecture and operating-model effect: creates the compatibility layer used
  by every later client layer.
- Tradeoff and source evidence: Block 2 contract; schema work is accepted before
  transport so drift failures remain isolated.

### Inputs and dependencies

- Block 2 upstream manifest, schema root, and compatibility contract.

### Required work

- Implement exact binary resolution, version probing, schema generation/loading,
  semantic-root calculation, schema selection, and compatibility validation.
- Expose typed compatibility results and errors without starting a child or
  opening a socket.
- Add deterministic accepted, stale, missing, malformed, and incompatible
  schema fixtures.

### Scope and non-goals

- In scope: binary identity, schema artifacts, validation, and compatibility
  reporting.
- Not in scope: JSON-RPC framing, request IDs, transports, initialization, or
  typed operations.

### Deliverables and recorded state

- Compatibility module, schema artifacts/manifests, typed results/errors,
  deterministic fixtures, tests, and update documentation.

### Resource and economy contract

Use retained generated schemas in normal tests; generate from the official
binary only for a bounded currentness check and candidate freeze.

### QA and independent review

Review reproducibility, semantic-root stability, version rules, fail-closed
behavior, and no process/transport side effects.

### Acceptance

- Compatible exact inputs produce one stable feature/schema result; stale,
  missing, malformed, or incompatible inputs fail with discriminating errors
  before any transport starts.

### Negative tests

- Reject PATH ambiguity, unpinned version, changed schema root, missing selected
  schema, malformed schema, unknown required feature, or transport side effect.

### Completion evidence

Pending.

### Stop

Stop before implementing JSON-RPC state or any transport.

---

## Block 4 — Implement bounded JSON-RPC request state

Status: `not-started`

### Objective

Implement transport-independent JSON-RPC framing, correlation, bounds, and
pending-call lifecycle over an injected byte channel.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: one deterministic request/response owner shared by
  all local transports.
- Potential capability loss or regression: ID mismatch, duplicate response, or
  unbounded pending state could corrupt calls.
- Protected-capability effect: exact schema validation, bounded memory, and
  discriminating protocol errors remain.
- Architecture and operating-model effect: creates the RPC layer below concrete
  transports and typed sessions.
- Tradeoff and source evidence: Block 2 protocol contract and Block 3 schema
  owner; injected bytes make the core independently testable.

### Inputs and dependencies

- Block 3 compatibility results and selected message schemas.

### Required work

- Implement message framing, outbound/inbound schema validation, bounded integer
  request IDs, pending-call registration/resolution, message-size limits, and
  structured protocol/remote errors.
- Define the minimal injected byte-channel protocol used by Block 5.
- Provide deterministic peer fixtures for success, remote error, malformed
  input, mismatched/duplicate IDs, timeout handoff, and closure.

### Scope and non-goals

- In scope: transport-independent RPC state and byte-channel contract.
- Not in scope: subprocesses, sockets, initialization, notifications, server
  callbacks, retry, or restart.

### Deliverables and recorded state

- RPC engine, byte-channel protocol, typed errors, deterministic peer fixtures,
  focused tests, and internal API documentation.

### Resource and economy contract

Use in-memory deterministic peers; no process, socket, official binary,
network, or downstream checkout.

### QA and independent review

Review correlation, bounds, concurrency invariants, schema enforcement, pending
cleanup, error taxonomy, and transport independence.

### Acceptance

- Concurrent bounded calls resolve exactly once through the injected channel;
  malformed, duplicate, mismatched, oversized, or remote-error responses fail
  without leaking pending state.

### Negative tests

- Reject non-integer/duplicate IDs, unmatched response, double resolution,
  oversized line, malformed JSON/object, invalid schema, pending leak, or
  concrete transport assumption.

### Completion evidence

Pending.

### Stop

Stop before starting a subprocess or opening a Unix socket.

---

## Block 5 — Implement local transports and explicit process ownership

Status: `not-started`

### Objective

Implement the selected local byte transports and make connection/process
ownership explicit without adding app-server session behavior.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: reusable owned-process, socket, and injected
  composition over the same RPC core.
- Potential capability loss or regression: hidden ownership or broken cleanup
  could create two processes, leaked descriptors, or cross-connection writes.
- Protected-capability effect: one composition owner and transport
  replaceability remain.
- Architecture and operating-model effect: adds owned stdio and Unix-socket
  adapters behind Block 4's byte-channel protocol.
- Tradeoff and source evidence: Block 2 transport contract; remote WebSocket and
  service proxying remain excluded.

### Inputs and dependencies

- Block 4 RPC engine and injected byte-channel protocol.

### Required work

- Implement owned stdio subprocess transport, Unix-socket transport, injected
  transport composition, serialized writes, bounded reads, and deterministic
  close/terminate behavior.
- Resolve exact command arguments and ownership modes without ambient singleton
  process state.
- Add local fake process/socket fixtures for startup, partial write, EOF,
  explicit close, and failed cleanup.

### Scope and non-goals

- In scope: byte transport lifecycle and explicit process/connection ownership.
- Not in scope: app-server initialize, typed methods, callbacks, cancellation,
  automatic restart, public network transport, or service daemon.

### Deliverables and recorded state

- Transport adapters, ownership/configuration API, local fixtures, focused
  tests, and lifecycle documentation.

### Resource and economy contract

Use disposable local processes and sockets; no provider, public listener,
remote network, or downstream command.

### QA and independent review

Review ownership, argv resolution, cleanup, descriptor/process lifetime,
serialized writes, socket bounds, and no hidden singleton.

### Acceptance

- Each selected transport satisfies the same byte-channel contract; owned and
  injected modes are explicit; close/failure leaves no live child, socket,
  descriptor, or pending write.

### Negative tests

- Reject shell command strings, two owners, ambient singleton, unresolved
  executable, path-unsafe socket, partial-write corruption, post-close write,
  leaked child/descriptor, or public listener.

### Completion evidence

Pending.

### Stop

Stop before app-server initialization or typed operations.

---

## Block 6 — Implement typed app-server session and operations

Status: `not-started`

### Objective

Implement one initialized app-server session with feature negotiation and the
frozen narrowed typed operation surface.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: typed official operations without exposing raw RPC.
- Potential capability loss or regression: invalid handshake or broad methods
  could enable unsupported behavior or bypass adapters.
- Protected-capability effect: exact feature availability, narrowed methods,
  and explicit transport ownership remain.
- Architecture and operating-model effect: creates the synchronous typed session
  layer above Blocks 3–5.
- Tradeoff and source evidence: Block 2 API contract; asynchronous callbacks and
  restart remain separate review boundaries.

### Inputs and dependencies

- Block 5 transports, Block 4 RPC engine, and Block 3 compatibility result.

### Required work

- Implement initialize/initialized handshake, client identity, feature
  negotiation, session state, and the exact typed request methods selected in
  Block 2.
- Gate every method independently by compatible schema and negotiated feature.
- Keep raw method names/payload calls private and unexported.

### Scope and non-goals

- In scope: one connected initialized session and typed request surface.
- Not in scope: notification stream, server callbacks, cancellation, restart,
  product records, prompts, missions, or adapter policy.

### Deliverables and recorded state

- Typed session API, request/response models, feature gates, handshake fixtures,
  focused tests, and public API documentation.

### Resource and economy contract

Use deterministic fake transports for normal tests and one bounded official
initialize/read smoke at candidate freeze.

### QA and independent review

Review handshake order, feature gating, typed narrowing, schema coverage, raw
RPC encapsulation, and absence of product semantics.

### Acceptance

- A compatible session initializes once, exposes only negotiated typed methods,
  returns validated typed results, and refuses unsupported or raw operations.

### Negative tests

- Reject use before initialization, duplicate/changed initialization, invalid
  initialize result, unavailable method, raw RPC escape, incompatible schema,
  or product-specific request/result type.

### Completion evidence

Pending.

### Stop

Stop before notifications, server callbacks, cancellation, or restart behavior.

---

## Block 7 — Implement asynchronous events, callbacks, and call termination

Status: `not-started`

### Objective

Implement bounded asynchronous coordination for notifications, server-initiated
callbacks, cancellation, timeouts, and disconnects within one connection.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: complete bidirectional protocol behavior without
  product approval or retry policy.
- Potential capability loss or regression: races could drop, duplicate, or
  misattribute events, callbacks, cancellations, or terminal errors.
- Protected-capability effect: exact attribution, bounded queues, and explicit
  caller-owned decisions remain.
- Architecture and operating-model effect: adds one async coordinator to the
  initialized typed session.
- Tradeoff and source evidence: Block 2 callback/event contract; restart and
  cross-generation safety remain isolated in Block 8.

### Inputs and dependencies

- Block 6 initialized session and typed method surface.

### Required work

- Implement the read/event pump, notification projection, bounded event queues,
  server-request registration/response, callback attribution, cancellation,
  timeouts, disconnect termination, and final cleanup.
- Expose policy-neutral callback envelopes; callers supply decisions without the
  package choosing approval or product action.
- Extend deterministic fixtures for interleaving, capacity, cancellation,
  timeout, disconnect, and duplicate callback resolution.

### Scope and non-goals

- In scope: single-connection asynchronous protocol coordination.
- Not in scope: automatic restart/backoff, product approval policy, workflow
  outcome, persistence, provider budgets, or downstream adapter.

### Deliverables and recorded state

- Async coordinator, event/callback models, cancellation/timeout behavior,
  bounded fixtures, focused concurrency tests, and API documentation.

### Resource and economy contract

Use deterministic forced interleavings and bounded queues; reuse earlier fake
transports and avoid repeated official-binary smoke.

### QA and independent review

Review attribution, exactly-once resolution, bounds, disconnect cleanup,
timeout/cancellation races, callback neutrality, and content-free diagnostics.

### Acceptance

- Notifications and callbacks remain attributable and bounded; every pending
  call terminates exactly once by response, cancellation, timeout, callback
  result, or disconnect; caller policy remains external.

### Negative tests

- Reject dropped/duplicate event, stale callback answer, callback-capacity leak,
  cancellation after replacement result, timeout double-resolution, secret or
  content log, or package-selected approval.

### Completion evidence

Pending.

### Stop

Stop before automatic restart, backoff, or cross-generation state replacement.

---

## Block 8 — Implement generation-bound restart safety

Status: `not-started`

### Objective

Make reconnect/restart replace one failed connection without allowing old
requests, events, callbacks, or transport effects to affect the replacement.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: recoverable local client state with exact
  generation isolation.
- Potential capability loss or regression: old concurrent work could publish,
  terminate, or corrupt state owned by a new connection.
- Protected-capability effect: one process owner, exactly-once termination, and
  current connection truth remain.
- Architecture and operating-model effect: adds generation-bound recovery hooks
  above the accepted session/async layers.
- Tradeoff and source evidence: Block 2 lifecycle contract; retry timing remains
  caller-configurable rather than product policy.

### Inputs and dependencies

- Block 7 asynchronous coordination and Block 5 transport ownership.

### Required work

- Assign immutable connection generations to transports, calls, events,
  callbacks, writes, cancellations, and completion effects.
- Implement restart/replace, bounded backoff hooks, old-generation failure,
  current-generation publication gates, and deterministic cleanup.
- Add forced race fixtures covering pre-write, post-write, response,
  notification, callback, cancellation, timeout, and close interleavings.

### Scope and non-goals

- In scope: connection replacement, generation isolation, and policy hooks.
- Not in scope: product retry budgets, provider selection, durable event ledger,
  multi-process pool, remote failover, or supervision policy.

### Deliverables and recorded state

- Generation/restart state, recovery hooks, forced-race fixtures, focused
  tests, lifecycle documentation, and retained failure diagnostics.

### Resource and economy contract

Use deterministic barriers rather than probabilistic stress loops; run only
affected race schedules after a correction.

### QA and independent review

Review every side-effect linearization point, process ownership, currentness,
cleanup, retry-policy separation, and exact forced schedules.

### Acceptance

- A failed connection is replaced once; all old-generation work terminates or
  is ignored at its side-effect boundary; only the current generation can
  publish, resolve, cancel, or close current state.

### Negative tests

- Reject old-generation write/response/event/callback publication, old timeout
  terminating new state, concurrent restart creating two owners, unbounded
  backoff, or diagnostic test cited without exact forced schedule.

### Completion evidence

Pending.

### Stop

Stop before full-distribution qualification or cross-package work.

---

## Block 9 — Freeze app-server client distribution conformance

Status: `not-started`

### Objective

Package and prove the complete app-server client contract across compatibility,
RPC, transports, session, async coordination, and restart safety.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block integrates and freezes
  already owned client behavior; it adds no new protocol capability.

### Inputs and dependencies

- Accepted Blocks 3–8 and the exact Block 2 contract.

### Required work

- Complete the deterministic fake server and end-to-end conformance matrix.
- Build/install the wheel, freeze exported API and compatibility fixtures, and
  validate docs/examples through public imports.
- Run focused checks first, then one complete client matrix and one bounded
  official-binary smoke at the frozen candidate.

### Scope and non-goals

- In scope: app-server distribution integration, packaging, and acceptance.
- Not in scope: new methods/transports, consumer adapter, cross-package
  composition, publication, or downstream testing.

### Deliverables and recorded state

- Final client wheel, complete fake server, conformance matrix, public API
  fixture, compatibility root, documentation/examples, and exact review.
- Package record for capability `codex-app-server-client-package`: exact pushed
  repository commit; `codex-app-server-client==<version>`; wheel filename,
  SHA-256, and content root; public import/API root; official protocol revision,
  schema root, and compatibility-fixture root; remote-currentness proof; and
  posture `package-accepted/program-qualification-pending` plus
  `no-license-selected/unpublished`.

### Resource and economy contract

Reuse all accepted focused proof after cheap currentness checks; run the full
client matrix and official smoke once after candidate freeze.

### QA and independent review

Review complete API proportionality, protocol coverage, fixture realism,
currentness, package isolation, and absence of product behavior.

### Acceptance

- The wheel-installed client passes the frozen protocol/lifecycle matrix,
  public docs execute, the official smoke matches the compatibility root, and
  no open finding changes client behavior.
- The package record resolves every required field to immutable values, its
  source commit is confirmed on the configured remote, and it makes no
  downstream pin, adoption, availability, or reuse-rights claim.

### Negative tests

- Reject private-only test path, stale compatibility fixture, missing lifecycle
  family, changed candidate after proof, raw RPC export, downstream type, or
  package artifact containing product policy.

### Completion evidence

Pending.

### Stop

Stop before implementing other package behavior or cross-package composition.

---

## Block 10 — Implement the embedded/service structural contract

Status: `not-started`

### Objective

Provide the smallest neutral protocols and fixtures needed to prove equivalent
lifecycle behavior from embedded and service-shaped hosts.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: a reusable structural conformance kit without a
  shared runtime or product lifecycle owner.
- Potential capability loss or regression: the contract could grow into a
  service framework or impose product outcome semantics.
- Protected-capability effect: each downstream host retains its engine, state,
  authority, and transport choices.
- Architecture and operating-model effect: creates the protocol/test-only
  `embedded-service-contract` distribution.
- Tradeoff and source evidence: Block 0 admission proof; structural equivalence
  is shared while all semantic operations remain external.

### Inputs and dependencies

- Block 1 packaging baseline and Block 0 admission contract.

### Required work

- Define minimal start/status/event/cancel/outcome/error structural protocols.
- Provide conformance assertions, explicit single-process-owner composition,
  two neutral in-repository reference hosts, and deterministic failure fixtures.

### Scope and non-goals

- In scope: structural protocols and test helpers.
- Not in scope: web framework, server, service runner, auth, scheduler,
  persistence, product lifecycle, canonical outcome, or downstream fixture.

### Deliverables and recorded state

- Independent distribution, protocols, conformance helpers, neutral reference
  hosts, failure fixtures, documentation, tests, and wheel.
- Package record for capability `embedded-service-contract-package`: exact
  pushed repository commit; `embedded-service-contract==<version>`; wheel
  filename, SHA-256, and content root; public import/API root; structural
  contract, conformance-fixture, and supported-Python roots; remote-currentness
  proof; and posture `package-accepted/program-qualification-pending` plus
  `no-license-selected/unpublished`.

### Resource and economy contract

Use pure deterministic tests and neutral in-memory reference hosts; no network,
provider, downstream checkout, or consumer suite.

### QA and independent review

Review minimality, structural neutrality, implementability, process ownership,
and absence of runtime or product authority.

### Acceptance

- Two structurally different neutral reference hosts pass the same conformance
  contract without sharing state, product types, or an implementation runtime.
- The package record resolves every required field to immutable values, its
  source commit is confirmed on the configured remote, and it contains no
  consumer identifier, pin, adoption claim, or reuse-rights claim.

### Negative tests

- Reject framework dependencies, canonical persistence, semantic outcome
  authority, product fields, session-only results, two process owners, or a
  fixture that requires a downstream package.

### Completion evidence

Pending.

### Stop

Stop before cross-package composition or any service implementation.

---

## Block 11 — Implement the non-authoritative runtime-manifest package

Status: `not-started`

### Objective

Represent exact descriptive component, protocol, schema, capability, and
dependency compatibility without representing product authority or acceptance.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: deterministic compatibility/currentness metadata
  for local composition.
- Potential capability loss or regression: a manifest could become a universal
  registry or be mistaken for authorization.
- Protected-capability effect: availability, authorization, acceptance, and
  application decisions remain entirely outside this package.
- Architecture and operating-model effect: creates an independent
  `runtime-manifest` distribution with canonical descriptive serialization.
- Tradeoff and source evidence: Block 0 admission proof; exact metadata is
  shared while authority-bearing state is deliberately unrepresentable.

### Inputs and dependencies

- Block 1 packaging baseline and Block 0 admission contract.

### Required work

- Define immutable component/version/content-root, protocol/schema feature,
  dependency, compatibility assertion, and unavailable-reason projections.
- Implement deterministic canonical serialization, comparison, validation, and
  schema-version handling.
- Exclude authorization, acceptance, product identity, discovery, and ambient
  installed-state inference from the schema and API.

### Scope and non-goals

- In scope: caller-supplied descriptive runtime metadata and deterministic
  compatibility helpers.
- Not in scope: product registry, discovery service, authority grant,
  acceptance state, persistence platform, universal identity, or consumer
  inventory.

### Deliverables and recorded state

- Independent distribution, schemas, canonical serializer, compatibility
  helpers, neutral fixtures, documentation, tests, and wheel.
- Package record for capability `runtime-manifest-package`: exact pushed
  repository commit; `runtime-manifest==<version>`; wheel filename, SHA-256,
  and content root; public import/API root; manifest-schema,
  compatibility-fixture, and supported-Python roots; remote-currentness proof;
  and posture `package-accepted/program-qualification-pending` plus
  `no-license-selected/unpublished`.

### Resource and economy contract

Use pure deterministic tests over bounded neutral manifests; no environment
scan, consumer checkout, network, or provider.

### QA and independent review

Review canonicality, versioning, compatibility semantics, extensibility bounds,
absence of authority states, and absence of consumer identifiers.

### Acceptance

- Neutral fixture compositions bind exact versions and roots, compatibility is
  deterministic, incompatible/unknown schemas fail clearly, and no manifest can
  express or imply authorization or acceptance.
- The package record resolves every required field to immutable values, its
  source commit is confirmed on the configured remote, and it contains no
  consumer identifier, pin, adoption claim, or reuse-rights claim.

### Negative tests

- Reject mutable roots, product IDs/content, authorization/acceptance fields,
  unknown schemas silently accepted, ambient discovery, filesystem scanning, or
  a manifest that changes runtime authority.

### Completion evidence

Pending.

### Stop

Stop before cross-package composition or downstream manifest adoption.

---

## Block 12 — Prove independent distribution isolation

Status: `not-started`

### Objective

Prove that each admitted distribution builds, installs, imports, and tests alone
with only its declared dependencies.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block validates distribution
  isolation and introduces no package behavior or product semantics.

### Inputs and dependencies

- Frozen distributions from Blocks 9–11.

### Required work

- Build each wheel independently, install it into a clean environment, run its
  public import and test contract, and audit declared versus observed imports.
- Add package-specific CI jobs and clear diagnostics for missing, undeclared,
  circular, or reverse dependencies.

### Scope and non-goals

- In scope: isolated build/install/import/test and dependency direction.
- Not in scope: combined composition, consumer skeleton, whole-product test,
  deployment, or new runtime API.

### Deliverables and recorded state

- Isolated-wheel matrix, clean-environment test jobs, import/dependency audit,
  CI integration, and failure diagnostics.

### Resource and economy contract

Build each wheel once per candidate and run package tests in parallel; use no
downstream content, checkout, command, provider, or network.

### QA and independent review

Review wheel contents, declared metadata, import direction, test reachability,
CI isolation, and absence of repository-layout assumptions.

### Acceptance

- Every distribution installs and passes through public imports in a clean
  environment; observed imports match metadata; no wheel requires another
  package unless explicitly declared and admitted.

### Negative tests

- Reject undeclared/circular/reverse dependency, monorepo-only import, missing
  package data, editable-install dependence, downstream path, or CI that passes
  only because all packages are installed.

### Completion evidence

Pending.

### Stop

Stop before installing all distributions together or testing composition.

---

## Block 13 — Prove neutral cross-package composition

Status: `not-started`

### Objective

Prove that the independently accepted distributions compose through public APIs
in one neutral internal scenario without creating a new production abstraction.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block verifies composition of
  accepted package behavior and adds no new public capability.

### Inputs and dependencies

- Block 12 isolated wheels and accepted neutral fixtures from Blocks 9–11.

### Required work

- Install all distributions together and run one neutral composition in which
  runtime manifests describe exact package/protocol roots, the app-server client
  uses deterministic transport, and embedded/service reference hosts satisfy
  the same structural lifecycle contract.
- Prove every exercised path is reachable through installed public APIs and the
  composition fixture is test-only.

### Scope and non-goals

- In scope: neutral internal integration and incompatible-root diagnostics.
- Not in scope: consumer skeleton, new facade/framework, production service,
  downstream adapter, or whole-product behavior.

### Deliverables and recorded state

- Combined-install job, neutral composition fixture, exact root/result matrix,
  public-API reachability proof, and failure diagnostics.

### Resource and economy contract

Reuse isolated wheels and accepted fixtures; run one affected scenario during
development and the complete neutral composition once after candidate freeze.

### QA and independent review

Review fixture neutrality, public-API use, exact roots, error discrimination,
absence of test-only architecture, and no new package coupling.

### Acceptance

- All distributions coexist and complete the neutral scenario through public
  APIs; incompatible roots fail clearly; the fixture creates no production API
  or downstream dependency.

### Negative tests

- Reject private import, mutable/mixed roots, hidden product field, fixture-only
  alternate runtime, implicit authority, incompatible versions accepted, or
  downstream invocation.

### Completion evidence

Pending.

### Stop

Stop before terminal qualification, authority audit, or release posture.

---

## Block 14 — Qualify the frozen technical package set

Status: `not-started`

### Objective

Freeze one exact package set and prove complete build, API, compatibility,
documentation, and internal conformance quality.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block qualifies frozen technical
  behavior and adds no feature, authority, or external effect.

### Inputs and dependencies

- Block 13 combined composition and one frozen repository candidate.

### Required work

- Build every wheel, verify checksums and metadata, run affected checks then the
  full internal matrix once, and validate public API docs/examples.
- Freeze compatibility roots, dependency inventory, artifact manifest, and
  exact candidate revision.
- Reconcile the three accepted package records against the frozen candidate;
  preserve their package-source revisions and artifact roots, add the exact
  pushed qualification revision/currentness proof, and change posture to
  `program-qualified` only after the complete internal matrix passes.
- Obtain distinct exact-revision technical review.

### Scope and non-goals

- In scope: technical qualification of repository-owned artifacts.
- Not in scope: downstream/authority audit, license selection, publication,
  release, announcement, or consumer testing.

### Deliverables and recorded state

- Wheels/checksums, artifact/dependency inventory, API/compatibility matrix,
  documentation proof, complete internal conformance evidence, and technical
  exact-revision review.

### Resource and economy contract

Reuse accepted focused proof after cheap currentness checks; execute the full
frozen matrix once after likely-mutating review and rerun only invalidated proof.

### QA and independent review

Review build reproducibility, API proportionality, protocol coverage,
documentation truth, dependency metadata, and exact candidate currentness.

### Acceptance

- Every distribution builds and installs at one exact revision; all internal
  matrices and docs pass; artifacts and compatibility roots are frozen; no
  technical finding remains open.
- Each package record names its immutable package source/artifact and the exact
  pushed Block 14 qualification revision, with posture `program-qualified` and
  `no-license-selected/unpublished`; no record claims downstream acceptance.

### Negative tests

- Reject mixed roots, changed candidate after proof, missing wheel data,
  undeclared dependency, invalid example, incomplete matrix, or pre-correction
  evidence cited as current.

### Completion evidence

Pending.

### Stop

Stop before authority/downstream audit, license action, publication, or release.

---

## Block 15 — Audit authority and downstream non-interaction

Status: `not-started`

### Objective

Prove that the frozen technical package set contains no downstream integration,
product authority, or release authority leakage.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block audits the frozen
  candidate against repository boundaries and introduces no package behavior.

### Inputs and dependencies

- Accepted Block 14 exact candidate and Block 0 authority/dependency contract.

### Required work

- Audit package source, schemas, tests, fixtures, examples, commands, artifacts,
  and CI runtime paths for downstream imports, paths, identifiers, operations,
  pins, handoffs, or acceptance claims.
- Audit exported records/APIs for product policy, semantic authority,
  persistence, credential, tenancy, billing, QA/supervision, or release state.
- Obtain distinct semantic authority-boundary review of the exact candidate.

### Scope and non-goals

- In scope: downstream non-interaction and authority-boundary proof.
- Not in scope: technical feature requalification unless a finding changes code,
  license decision, publication, release, or downstream adoption.

### Deliverables and recorded state

- Downstream-interaction audit, authority/import matrix, finding-closure map,
  exact semantic review, and retained limitations.

### Resource and economy contract

Inspect the frozen candidate once; reuse Block 14 technical proof. A correction
reruns only affected technical proof before a fresh authority review.

### QA and independent review

The semantic reviewer independently inspects exact artifacts and public APIs;
passing tests or populated manifests cannot substitute for this judgment.

### Acceptance

- No distribution artifact or runtime test interacts with a downstream
  consumer; no exported API/record owns product or release authority; every
  finding is closed on the exact reviewed revision.

### Negative tests

- Reject consumer import/path/identifier in artifact/runtime fixture, product
  acceptance or authorization state, consumer handoff/pin, domain content,
  credential/persistence owner, open-source claim, or technical proof used as
  semantic authority proof.

### Completion evidence

Pending.

### Stop

Stop before license grant, publication, release, announcement, or downstream
adoption.

---

## Block 16 — Record no-license/unpublished posture and close the program

Status: `not-started`

### Objective

Record the truthful internal-completion and release posture without granting a
license, publishing packages, or implying downstream adoption.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block records terminal evidence
  and performs no package behavior or external effect.

### Inputs and dependencies

- Accepted Block 15 exact revision and repository license/release instructions.

### Required work

- Confirm artifacts and metadata make no unsupported license, publication,
  release, support, or downstream-adoption claim.
- Record the exact `no-license-selected/unpublished` posture, prohibited effects,
  and activation conditions for any separately authorized successor.
- Freeze the final package, conformance, documentation, authority, and
  Git-currentness evidence set.

### Scope and non-goals

- In scope: truthful terminal posture and internal program closure.
- Not in scope: adding `LICENSE`, choosing legal terms, publishing to an index,
  GitHub Release, announcement, consumer handoff, downstream integration, or
  unrelated package admission.

### Deliverables and recorded state

- Final internal completion manifest, package/artifact roots, release-posture
  record, retained limitations, and successor-activation boundary.
- Final package records retain their technical qualification facts while
  truthfully recording `no-license-selected/unpublished`; this posture neither
  publishes the artifacts nor grants or withdraws any downstream authority.

### Resource and economy contract

Reuse Blocks 14–15 artifacts and hashes; perform metadata/currentness checks
only and do not rerun the full matrix unless exact bytes changed.

### QA and independent review

Review that technical and authority completion are proven, release/legal claims
remain truthful, no external effect occurred, and the Stop is explicit.

### Acceptance

- The exact internal package set is accepted, the repository remains
  `no-license-selected/unpublished`, no release or downstream-adoption claim is
  made, and future external work is clearly outside this program.
- No final package record describes a publicly installable or reusable
  dependency, redistribution permission, consumer pin, or consumer acceptance.

### Negative tests

- Reject added license/classifier, publication configuration or effect, GitHub
  Release, open-source/reuse claim, consumer acceptance statement, downstream
  pin/handoff, or package admission hidden in terminal cleanup.

### Completion evidence

Pending.

### Stop

Stop before any license grant, publication, release, announcement, downstream
adapter or cutover, consumer test, or unrelated utility admission.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Package admission and authority architecture | 0 | 1–13 | 15–16 |
| Independent packaging and CI | 1 | 9–14 | 14 |
| Official app-server protocol contract | 2 | 3–9 | 14 |
| Version/schema compatibility | 3 | 4–9 | 14 |
| Bounded transport-independent JSON-RPC | 4 | 5–9 | 14 |
| Local transport and process ownership | 5 | 6–9 | 14–15 |
| Typed session and narrowed operations | 6 | 7–9 | 14 |
| Events, callbacks, and call termination | 7 | 8–9 | 14 |
| Restart generation safety | 8 | 9 | 14 |
| App-server client distribution | 9 | 12–14 | 14–15 |
| Embedded/service structural equivalence | 10 | 12–14 | 14–15 |
| Non-authoritative runtime manifests | 11 | 12–14 | 14–15 |
| Isolated distribution installation | 12 | 13–14 | 14 |
| Neutral cross-package composition | 13 | 14 | 14 |
| Technical package qualification | 14 | — | 14 |
| No downstream implementation or authority | 15 | — | 15–16 |
| No-license/unpublished release posture | 16 | — | 16 |

## 9. Final completion definition

The tracker is complete only when Blocks 0–16 are accepted at exact current
pushed revisions; every admitted distribution builds, installs, versions,
tests, and documents independently; the exact official protocol and internal
conformance matrices pass; exported APIs and artifacts contain no downstream
consumer dependency or product/release authority; no downstream repository was
operated or modified as implementation work; and the repository truthfully
records its `no-license-selected/unpublished` posture without crossing Block
16's Stop.

Completion does not mean that any downstream application has adopted, tested,
accepted, released, or even referenced these packages.
