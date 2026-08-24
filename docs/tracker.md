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

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Decide package admission, architecture, ownership, and the no-downstream boundary | — | `completed` |
| 1 | Create independent package skeletons, version policy, shared development tooling, and CI baseline | 0 | `completed` |
| 2 | Freeze the exact official Codex app-server protocol surface and public client contract | 1 | `completed` |
| 3 | Implement exact binary/version resolution and schema compatibility | 2 | `completed` |
| 4 | Implement bounded JSON-RPC framing, correlation, pending-call state, and protocol errors | 3 | `completed` |
| 5 | Implement owned stdio, Unix-socket, and injected transport composition | 4 | `completed` |
| 6 | Implement initialization, feature negotiation, and the narrowed typed operation surface | 5 | `completed` |
| 7 | Implement notifications, server callbacks, cancellation, timeouts, and disconnect coordination | 6 | `completed` |
| 8 | Implement generation-bound restart safety and single-process-owner recovery | 7 | `completed` |
| 9 | Complete and freeze the app-server client distribution and deterministic conformance matrix | 8 | `completed` |
| 10 | Implement neutral embedded-versus-service lifecycle protocols and fixtures | 1 | `completed` |
| 11 | Implement deterministic non-authoritative runtime/version manifests | 1 | `completed` |
| 12 | Prove every distribution builds and installs independently with clean dependency direction | 9–11 | `completed` |
| 13 | Prove all distributions compose through public APIs in one neutral internal scenario | 12 | `completed` |
| 14 | Qualify the frozen package set, artifacts, documentation, and complete internal matrix | 13 | `completed` |
| 15 | Audit the frozen package set for downstream coupling and product/release authority leakage | 14 | `completed` |
| 16 | Record the no-license/unpublished posture and close without external effects | 15 | `completed` |

Required order:

```text
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 ┐
    1 → 10                               ├→ 12 → 13 → 14 → 15 → 16
    1 → 11                               ┘
```

## Block 0 — Decide package admission and architecture boundaries

Status: `completed`

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
  implementation and artifacts consumer-neutral. A later provenance check
  found that the request hash omitted its canonical terminating newline; the
  first correction attempt also suffered shell expansion of the `$implement`
  token. The admission record now binds the canonical task, turn, item, exact
  194-byte length, terminating LF, and reviewer-confirmed SHA-256. Fresh
  exact-revision review accepted commit
  `601cd587d6c60bfa0c9724d75f72e39d1d555a5e`.
- Independent review: distinct read-only reviewer `/root/block0_reviewer`
  returned `ACCEPT` for exact commit
  `601cd587d6c60bfa0c9724d75f72e39d1d555a5e` after independently verifying the
  canonical 194 bytes, terminal LF, and SHA-256.
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
- Post-block audit: `accepted`; the source-provenance remediation is closed and
  substantive admission/architecture content is unchanged.
- Git durability: candidate and remediation commits pushed to `origin/main`;
  accepted status is recorded by the next scoped tracker checkpoint.

### Stop

Stop before creating package skeletons, build metadata, or CI.

---

## Block 1 — Establish independent packaging and CI baseline

Status: `completed`

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

- Exact accepted source: pushed commit
  `3c5510f81aa67f4c34c1510e27d30176fc5c2ab1`, tree
  `4e48d2075b926474e959264388bd1a7f8ec38012`; `origin/main` matched the
  candidate during review.
- Distribution/version roots: `codex-app-server-client==0.1.0` at
  `packages/codex-app-server-client`, `embedded-service-contract==0.1.0` at
  `packages/embedded-service-contract`, and `runtime-manifest==0.1.0` at
  `packages/runtime-manifest`. Each exposes only its own import namespace and
  package-local `__version__`; the repository root is not a distribution.
- Artifact proof: clean isolated builds, dependency-free installs, and imports
  passed on Python 3.11 and 3.14. Wheel SHA-256 values were respectively
  `37db7241ce052baf09d2cbccf92b44f2e127d839917a97dc5d8ca83ae83f5b2d`,
  `24c8035e44fd9a203bd3923e541db440f6c11a801a8a210ae0629415b8e9da9f`,
  and `0b1de132470200d0435bfc6579b8e5dd5655eb89d6cf403235a12e2b1b8e88d7`
  on both interpreters.
- Compatibility inputs: package matrix SHA-256
  `3436da75aa77685ffc87b99c4bb3d1795875596cb64549c70dc06e14ad9727c9`,
  changed-test map SHA-256
  `aaab545ad786df21e956320b7a2b775c64ab236767d9746a6a544e49ed9f3661`,
  and toolchain manifest SHA-256
  `09e59e2d487cba7b3eba6af044dc02dbd0c41325d3ca1889b218e4e01d408370`.
  The maintained runners enforce uv `0.11.9` and Ruff `0.15.12`; CI invokes
  those same repository-owned envelopes.
- Focused and negative validation: both `.github/...` and `./.github/...`
  changes select all three package jobs; package-local changes remain scoped;
  unknown package names fail closed; repository checks confirm no top-level
  `utils` import, root distribution, runtime dependency, cross-package import,
  license, or publication/release configuration.
- Independent review: distinct read-only reviewer `/root/block0_reviewer`
  returned `ACCEPT` for the exact pushed source above after rechecking the two
  remediated findings, all isolated builds/imports, deterministic artifact
  hashes, namespace and dependency boundaries, and absence of Block 2+
  behavior or downstream interaction.
- Product-capability review: the accepted three-distribution architecture was
  implemented at skeleton level with one pinned development/CI envelope; the
  rejected alternatives were a combined root distribution and unversioned
  ambient tooling. Independent versioning, downstream replaceability, and
  runtime isolation are preserved.
- Currentness and qualification posture: current for the accepted Block 1
  skeleton/tooling contract only; not a functional package handoff and not yet
  qualified for consumer adoption. No consumer repository was opened,
  executed, imported, changed, or tested.
- License/release posture: `no-license-selected/unpublished`.

### Stop

Stop before generating protocol schemas or implementing package behavior.

---

## Block 2 — Freeze the official app-server protocol and client contract

Status: `completed`

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

- Exact accepted source: pushed commit
  `b9d8a3e87bd1c45e60a8e27307e0f22e94a69cdb`, tree
  `2e2d993d7d6b4caee6e9156897ab5cdcd623f67b`; `origin/main` matched the
  independently reviewed candidate.
- Official upstream identity: `@openai/codex`/`codex-cli` `0.147.0`, official
  source tag `rust-v0.147.0`, tag object
  `3ed6f04f6bf8b7c46299d1cb1ff99c74ce21a51d`, and peeled source commit
  `be6e8eac029b183056b7e4402879f15d2c85f61b`. Exact remote tag currentness was
  reconfirmed at candidate freeze.
- Artifact/root: the one non-experimental disposable generation produced 285
  JSON files totaling 2,925,973 bytes. The retained tree root is
  `eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa`;
  manifest SHA-256 is
  `83ae559e659f2cfd6d7f66bd6c98208287e75200aa61d958e60f0b32baad6a3a`.
  Observed wrapper and `aarch64-apple-darwin` native executable SHA-256 values
  are pinned in that manifest and the maintained checker.
- Public contract: selected-surface root
  `9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`
  freezes eight typed request methods, fifteen typed notifications, three
  policy-neutral callbacks, and owned-stdio, Unix-socket, and injected-channel
  transports. Exact public API SHA-256
  `11e02c9c460821ebd5dd08f80b6544eb45b2217a53b90918ca472c26d14e1a21`
  freezes every root export, function/method signature, timeout/event/callback
  surface, schema-model reference, capability-enum value, ownership type,
  configuration model, generation rule, and concrete error subclass.
- Capability necessity: `supported-surface.json` records one neutral rationale
  for every selected request, notification, callback, and transport. The
  reviewer-requested `configWarning` export was removed because configuration
  is outside package ownership; raw RPC, experimental APIs, WebSocket, public
  listeners/proxies, account/auth, configuration/filesystem mutation,
  plugin/marketplace/MCP management, realtime media, remote control, deprecated
  callbacks, product types, and consumer behavior remain excluded.
- Compatibility/update proof: `scripts/schema_tree.py` defines the exact sorted
  tree-root algorithm and update record. CI replays it with the full frozen
  argument set. `scripts/check_protocol_contract.py` independently pins and
  cross-validates every provenance value, all schema/model references, the
  surface/API roots, capability enums, necessity maps, and exact exports.
- Focused and negative validation: repository quality and full tracker checks
  passed. Five mutations covering upstream version, experimental generation,
  surface widening, missing necessity evidence, and raw API widening failed
  closed. The unchanged skeleton wheel built/imported on Python 3.11 and 3.14
  with identical SHA-256
  `c927e81b942d6b854b862e3beda9c895cf70270f5a4f4a46f00d6cd4c38ca0d2`.
- Independent review: distinct read-only reviewer `/root/block0_reviewer`
  returned `ACCEPT` for the exact pushed source above after one remediation
  cycle and independently confirmed official currentness, complete provenance
  pinning, API unambiguity, per-member minimality, retained-tree
  proportionality, proof-map ownership, and every Stop/non-interaction
  boundary.
- Product-capability review:
  - Trigger: consequential Block 2 posture.
  - Paths compared: no reusable client; a raw/general bridge over the complete
    official protocol; the selected closed lifecycle surface; and a fully
    exported generated protocol client.
  - Selected level and owner: the closed lifecycle surface owned by Blocks
    3–9, the smallest option providing typed create/resume/read/list,
    turn/steer/interrupt/review, bounded events, neutral callbacks, and local
    transport replacement without raw access.
  - Protected-capability result: exact upstream fidelity, one explicit process
    owner, downstream adapter freedom, additive-upstream non-widening, and
    product-policy separation are preserved.
  - Rejected alternatives: no client loses admitted shared mechanics; a raw
    bridge or full generated export widens unstable/product-adjacent surface;
    `configWarning` was unnecessary under the no-configuration boundary.
  - Tradeoff and uncertainty: a complete 2.9 MB provenance snapshot is retained
    for exact currentness while only the closed selected surface can become
    public; future upstream changes require a reviewed compatibility update.
- Currentness and qualification posture: current and accepted as the Block 2
  design/provenance input only; no compatibility or client behavior is yet
  implemented and this is not a consumer-ready package handoff.
- Source-adaptation and downstream audit: only official CLI/schema/package/tag
  inputs were inspected. No prior client or consumer repository/API/type was
  inspected, copied, opened, executed, imported, changed, or tested.
- License/release posture: `no-license-selected/unpublished`.

### Stop

Stop before implementing compatibility or client code.

---

## Block 3 — Implement app-server version and schema compatibility

Status: `completed`

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

- Exact accepted source: pushed commit
  `076053bc0a7187d15881774e96aab353439add18`, tree
  `4adb67e91771ab3275a953ac4fa0e75c421ceb0a`; `origin/main` matched the
  independently reviewed candidate.
- Distribution/version and public root: `codex-app-server-client==0.1.0` at
  `packages/codex-app-server-client`, import root `codex_app_server_client`.
  Block 3 exports the exact compatibility subset frozen by Block 2:
  `ProtocolTarget`, `BinaryIdentity`, `CompatibilityResult`, `FeatureSet`, four
  closed capability enums, resolver/inspection functions, and discriminating
  compatibility errors.
- Compatibility inputs and roots: official Codex `0.147.0`, source commit
  `be6e8eac029b183056b7e4402879f15d2c85f61b`, retained byte root
  `eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa`,
  canonical semantic root
  `4e5c64213673b670d2575d7b7670d2089d49f92a92c56f2d16618e4a8857813e`,
  and selected-surface root
  `9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`.
  The complete schema/protocol inputs are wheel-retained package data.
- Binary identity proof: explicit path syntax and all `PathLike` inputs resolve
  exactly; only bare string names search `PATH`, which rejects zero or multiple
  distinct resolutions. File bytes plus device/inode/size/mtime/ctime are
  stable before and after `--version`; deletion or replacement fails typed and
  the returned SHA-256 binds the bytes actually probed.
- Schema/error-order proof: public compatibility inspection rehashes actual
  selected-surface content, validates required files/unions/selected methods
  before whole-tree comparison, and then verifies byte/semantic/file-count
  roots. Missing selected files raise `SchemaMissingError`, absent selected
  methods raise `UnsupportedFeatureError`, malformed JSON raises
  `SchemaMalformedError`, and other semantic drift raises
  `SchemaRootMismatchError`.
- Focused and negative validation: 18 compatibility tests cover exact and
  ambiguous resolution, `./codex`/`Path` intent, malformed/stale probes,
  self-replacement/deletion, retained no-process inspection, target/surface
  drift, missing/malformed schemas, public missing-feature behavior, exact
  non-experimental generation argv, and zero transport side effects. Five
  frozen-contract mutation tests also pass.
- Artifact proof: isolated installed-wheel tests passed on Python 3.11 and 3.14
  with identical wheel SHA-256
  `ff513518b9d20ee7e6b49770690328c59b2c3c93af9441a00a80d5ed26db4b2e`.
- Official currentness proof: one bounded explicit official-CLI regeneration
  reported wrapper SHA-256
  `134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477`,
  version `0.147.0`, semantic root above, and the exact 8 request/15
  notification/3 callback/3 transport feature projection.
- Independent review: distinct read-only reviewer `/root/block0_reviewer`
  returned `ACCEPT` for the exact pushed source after one remediation cycle,
  independently reproduced all four corrected boundary failures, reran the 18
  tests, both isolated wheels, full quality, official currentness, and scope
  audit, and found no material issue.
- Product-capability review: compared version-only checking, the selected
  version plus semantic/schema/feature owner, and eager transport/session
  startup. The middle path was selected because it supplies exact fail-closed
  compatibility without runtime lifecycle effects. Protected protocol fidelity
  and downstream replaceability are preserved; PATH ambiguity, mixed binary
  identity, recorded-but-unhashed surface metadata, and root-first masked
  errors were rejected.
- Currentness and qualification posture: current and accepted for the Block 3
  compatibility layer; later client layers and final package qualification
  remain pending.
- Downstream and Stop audit: retained inspection starts no subprocess, socket,
  transport, request state, or session. Only explicit version probing and the
  bounded non-experimental generator invoke the official CLI. No consumer
  repository/API/type was opened, executed, imported, changed, copied, or
  tested.
- License/release posture: `no-license-selected/unpublished`.

### Stop

Stop before implementing JSON-RPC state or any transport.

---

## Block 4 — Implement bounded JSON-RPC request state

Status: `completed`

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

- Exact accepted source: pushed commit
  `3d56fe1d30c8902a2dbb9007c6f9de3f12bc749f`, tree
  `0a441abc53e5de34c228d8ef8b1f08417c789e2a`; `origin/main` matched the
  independently reviewed candidate. The candidate incorporates the initial
  implementation plus two independently requested race/diagnostic remediation
  commits.
- Distribution/version and artifact root: `codex-app-server-client==0.1.0` at
  `packages/codex-app-server-client`, import root `codex_app_server_client`.
  The root exports the exact frozen `ByteChannel` protocol and Block 4 error
  classes; request allocation, arbitrary method strings, framing writes, the
  RPC engine, and RPC limits remain private.
- Compatibility inputs: the engine requires Block 3's exact
  `CompatibilityResult`, canonical semantic schema root
  `4e5c64213673b670d2575d7b7670d2089d49f92a92c56f2d16618e4a8857813e`,
  and closed `RequestCapability` membership. Envelopes validate against the
  wheel-retained official Codex `0.147.0` `JSONRPCRequest`,
  `JSONRPCResponse`, and `JSONRPCError` schemas; the package deliberately
  narrows upstream string-or-integer IDs to positive bounded `int64` values.
- Framing/bounds proof: strict UTF-8 JSON lines accept LF or CRLF and reject
  absent or embedded newlines, empty/non-object/malformed records, duplicate
  JSON keys, nonstandard constants, invalid envelopes, non-integer IDs, and
  inbound or outbound byte-limit violations. Pending calls, message bytes,
  and request-ID allocation are bounded before use.
- Correlation/lifecycle proof: concurrent out-of-order responses resolve the
  matching call exactly once. Success, remote error, timeout, cancellation,
  malformed input, unmatched/duplicate IDs, peer closure, immediate write
  failure, and partial-write success/error races all remove pending state.
  One late response to a timed-out or cancelled call is consumed without
  resurrecting or fatally corrupting the call.
- Diagnostic-minimization proof: validated `RemoteRpcError` retains only
  request ID, integer code, and whether data was present. Forced malformed
  inbound, outbound serialization, read-channel, write-channel, and
  partial-write failures expose no request/response/channel content through
  the delivered exception, its cause/context graph, arguments, or attributes.
- Focused and negative validation: 26 deterministic RPC tests pass under
  asyncio debug mode with runtime warnings promoted. They include forced
  queued-response/cancellation schedules for success and remote error and
  forced response-before-write-failure schedules for both outcome families;
  no unretrieved future warning or pending leak remains.
- Consolidated validation: all 44 package source tests, repository quality,
  retained protocol/root checks, and five frozen-contract mutation checks
  pass. Isolated installed-wheel tests pass on Python 3.11 and 3.14 with
  identical wheel SHA-256
  `d8ae36a06b3e03fdb5ffbf6036511ed50375317846017862221888eebc1282c5`.
- Independent review: distinct read-only reviewer `/root/block0_reviewer`
  returned `ACCEPT` on the exact pushed candidate after two rejected
  candidates exposed and drove closure of cancellation, content-retention,
  immediate-write, and partial-write races. The final review independently
  reproduced every forced schedule, reran full quality and both wheel tests,
  and found no material issue.
- Currentness and qualification posture: current and accepted for the Block 4
  transport-independent RPC package layer using Block 3's accepted Codex
  `0.147.0` compatibility input. Concrete transports, initialization, typed
  session behavior, complete client conformance, and final distribution
  qualification remain pending Blocks 5–9.
- Downstream and Stop audit: implementation and tests use only an injected
  in-memory byte channel. No subprocess, socket, concrete transport,
  initialization/session, notification/callback, retry/restart, raw public RPC
  escape hatch, downstream repository/API/type, license, publish, or release
  effect is present.
- License/release posture: `no-license-selected/unpublished`.

### Stop

Stop before starting a subprocess or opening a Unix socket.

---

## Block 5 — Implement local transports and explicit process ownership

Status: `completed`

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

- Exact accepted source: pushed commit
  `793a7d591a8b351f6ea771dd6591f1abc52316ba`, tree
  `02dc5491359ef4a6f777644af67ab0bb44bd2e83`; `origin/main` matched the
  independently reviewed candidate and the worktree was clean.
- Distribution/version and artifact root: `codex-app-server-client==0.1.0` at
  `packages/codex-app-server-client`, import root `codex_app_server_client`.
  The root exports only `ClientTransport`, `StdioTransport`,
  `UnixSocketTransport`, `InjectedTransport`, exact `TransportOwnership`, the
  Block 4 `ByteChannel`, and discriminating transport errors; channel engines,
  subprocess ownership, and cleanup state remain private.
- Transport contract: owned stdio uses exact argv
  `<resolved-binary> app-server --listen stdio://` through
  `create_subprocess_exec`, with no shell or ambient singleton. Unix sockets
  require an absolute, NUL-free, parent-traversal-free path within the portable
  byte bound. Injected channels require explicit `owned` or `borrowed`
  ownership. Every transport is single-claim, serializes writes, bounds reads,
  and fails closed after partial write, EOF, or close.
- Ownership and cleanup proof: stdio revalidates the accepted Block 3 binary
  path, version `0.147.0`, and SHA-256 immediately before and after spawn. On
  POSIX it owns a new process group, closes the pipe, waits for EOF, escalates
  through bounded TERM/KILL, verifies direct-process reap, and proves the group
  absent. Unix and injected cleanup cancel and retrieve pending reads/writes;
  owned injected resources close exactly once while borrowed resources remain
  caller-owned.
- Cancellation and diagnostic proof: retained completion events keep stream,
  injected, and process-wait cleanup running when a caller is cancelled without
  abandoning a failing shield future. A retry observes the one retained typed
  result. Forced cleanup and process-wait failures expose no private byte,
  request, path, or subprocess content through exception causes, contexts,
  attributes, or the Python 3.14 event-loop exception handler.
- Focused and negative validation: 28 transport tests cover exact stdio argv,
  stale/unresolved identity, real echo and stubborn process/group teardown,
  safe Unix-socket paths and real local connection closure, single ownership,
  serialized and partial writes, bounded reads, EOF/post-close behavior,
  cancelled close continuation, failed cleanup, `ProcessLookupError` without
  reap proof, timeout-then-wait failure, and absence of shell, TCP listener, or
  singleton behavior. The full client source suite passes 72 tests.
- Artifact and repository proof: full maintained repository quality passed;
  isolated installed-wheel tests passed on Python 3.11 and 3.14 with identical
  wheel SHA-256
  `8fe58194d1b347581ab2d10197d97ddc55c7e13318cba47606d4494ebffac777`.
  The compatibility input remains the accepted official Codex `0.147.0`
  selected-surface root
  `9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`.
- Independent review: distinct read-only reviewer `/root/block0_reviewer`
  returned `ACCEPT` for the exact pushed source after three remediation cycles.
  The reviewer independently reproduced cancellation, partial-write,
  process-group, reap-proof, Python 3.14 cleanup-failure, and
  timeout-then-process-wait-failure schedules; reran all 28 focused and 72
  source tests, full quality, both installed wheels, and the scope audit; and
  found no remaining material issue.
- Currentness and qualification posture: current and accepted for the Block 5
  local-transport layer over Blocks 3–4. Initialization, typed operations,
  asynchronous coordination, restart safety, complete client conformance, and
  final package qualification remain pending Blocks 6–9 and 14.
- Downstream and Stop audit: source, tests, fixtures, docs, and proof remain
  repository-local and domain-neutral. No consumer repository, adapter, pin,
  fixture, test, process, or acceptance was imported, invoked, changed, or
  claimed. No app-server initialization, typed operation, callback,
  notification, retry, restart, public listener, or service runtime is present.
- License/release posture: `no-license-selected/unpublished`.

### Stop

Stop before app-server initialization or typed operations.

---

## Block 6 — Implement typed app-server session and operations

Status: `completed`

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

- Exact accepted source: pushed commit
  `3dc57c61cbe18ea4d1f6af6ec4179615066ce044`, tree
  `521a4520843a8827f1f99c641d6f1834f544b959`; `origin/main` matched the
  independently reviewed candidate and the worktree was clean.
- Distribution/version and artifact root: `codex-app-server-client==0.1.0` at
  `packages/codex-app-server-client`, import root `codex_app_server_client`.
  The root exports `AppServerClient`, `Session`, `ClientLimits`,
  `ClientIdentity`, the 16 selected top-level operation parameter/result
  models, and discriminating session/initialization errors. Raw JSON-RPC
  methods, payloads, connections, and session roots remain private.
- Exact model graph: the accepted official Codex `0.147.0` selected-surface
  root
  `9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`
  resolves to 193 registered retained schema names/types, including 97 frozen,
  slotted object dataclasses. Same-name unequal definitions are rejected;
  required fields have no default, optional fields use `None`, arrays become
  tuples, string enums are closed, unions remain closed aliases, and only
  explicitly open objects retain additional properties.
- Handshake and negotiated surface: one compatible transport sends exactly one
  `initialize`, advertises the explicit Block 6 false/empty feature posture,
  opts out of all 70 retained server notifications, validates the typed
  initialize result, and then sends `initialized`. The resulting session
  exposes eight request capabilities, zero notification capabilities, zero
  callback capabilities, and only its active owned transport.
- Typed operations: the exact public request surface is thread start, resume,
  read, and list; turn start, steer, and interrupt; and review start. Every
  operation applies its independent compatibility/capability gate and decodes
  its exact typed result. Invalid results fail the session closed without
  publishing an unvalidated value or enabling another write.
- Lifecycle and diagnostic proof: incompatibility fails before transport claim;
  cancelled close preserves and retrieves one retained cleanup result; and an
  unexpected notification immediately after initialization or while a request
  is pending closes the engine once, fails the session, completes cleanup, and
  exposes no protocol content through exceptions or event-loop diagnostics.
  The pending-request schedule is clean on Python 3.11 and 3.14.
- Focused and artifact validation: all 14 focused session tests and all 86
  complete client source tests passed, as did the full maintained repository
  quality command. Isolated installed-wheel tests passed on Python 3.11 and
  3.14 with identical wheel SHA-256
  `606c41283474c816c9e6ca6ccb29c7167ad96d270976d1ac5d6f40a31d667061`.
- Bounded official smoke: the official Codex `0.147.0` wrapper with SHA-256
  `134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477`
  initialized generation 1, reported the exact 8/0/0 request/notification/
  callback capability split, used owned stdio, and exited with return code 0.
  Ambiguous ambient binary resolution was separately rejected before transport
  claim.
- Independent review: distinct read-only reviewer `/root/block0_reviewer`
  returned `ACCEPT` for the exact pushed source after one remediation cycle.
  The reviewer independently replayed both Python versions and both retained
  notification-failure schedules, audited the model graph and exact public
  exports, ran the official process smoke, reran focused, complete-source,
  quality, and installed-wheel proof, and found no remaining material issue.
- Currentness and qualification posture: current and accepted for the Block 6
  initialized typed-session layer over Blocks 3–5. Notification/callback and
  call-termination coordination, restart safety, complete client conformance,
  and final package qualification remain pending Blocks 7–9 and 14.
- Downstream and Stop audit: source, models, tests, fixtures, docs, and proof
  remain repository-local and domain-neutral. No consumer repository, adapter,
  pin, fixture, test, process, cutover, or acceptance was imported, invoked,
  changed, or claimed. No notification projection, server callback answer,
  retry, restart, product policy, public listener, or service runtime is
  present.
- License/release posture: `no-license-selected/unpublished`.

### Stop

Stop before notifications, server callbacks, cancellation, or restart behavior.

---

## Block 7 — Implement asynchronous events, callbacks, and call termination

Status: `completed`

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

- Exact accepted source: pushed repository commit
  `5db9f582d94f1468f9cc6d4c1a2df27e11477d6d`, tree
  `9eb3bfd28b63022c22675c637dbb2e11e1f6ebe0`, for
  `codex-app-server-client==0.1.0`. The public surface remains exactly 88
  exports with the frozen 8 request, 15 notification, 3 callback, and 3
  transport capability projection.
- Coordination behavior: one reader owns typed response, notification, and
  callback publication; event and callback queues are bounded; callback
  results are exact-type and exactly-once; pending calls, retained writes,
  timeouts, cancellation, disconnect, explicit close, and cleanup each select
  one terminal result without leaking capacity or replacing an already selected
  response. Iterator claims release after close or cancellation, and callback
  decisions remain entirely caller-owned.
- Boundary and failure proof: forced interleavings cover one and repeated
  cancellation, response-versus-write/close races, timeout and late-response
  correlation, callback preflight and retained response writes, disconnect,
  cleanup failure, queue/request bounds, duplicate/stale callback resolution,
  integer limits, and reader finalization. Inbound JSON-lines now decode only
  strict UTF-8 without a BOM; UTF-16LE/BE, UTF-32LE/BE, UTF-8 BOM, invalid
  UTF-8, and non-scalar strings fail before any response, event, or callback is
  published, with content-free diagnostics.
- Focused, full-source, and artifact validation: all 61 session tests and all
  133 client source tests passed on Python 3.11 and 3.14 with asyncio debug and
  runtime-warning enforcement. The full maintained repository quality command
  passed. Isolated installed-wheel tests passed on both interpreters for
  `codex_app_server_client-0.1.0-py3-none-any.whl`, with identical wheel
  SHA-256
  `df563b386cab68f17db6fcfdacea110793573299731dd634b417680bfe5c3ae6`.
- Compatibility inputs and roots: official Codex `0.147.0`, source commit
  `be6e8eac029b183056b7e4402879f15d2c85f61b`, retained byte root
  `eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa`,
  canonical semantic root
  `4e5c64213673b670d2575d7b7670d2089d49f92a92c56f2d16618e4a8857813e`,
  and selected-surface root
  `9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`.
  The accepted Block 6 official-binary smoke remains valid because no binary,
  retained protocol, compatibility root, initialization, or typed-operation
  input changed; the Block resource contract therefore avoided repeating it.
- Independent review: distinct read-only reviewer `/root/block0_reviewer`
  returned `ACCEPT` for the exact pushed source after independently reproducing
  and closing all fourteen findings across attribution, bounds, race ordering,
  cancellation state, strict framing, and cleanup. The reviewer reran the
  dual-interpreter source and wheel suites, full quality, export/scope audits,
  and found no remaining material issue.
- Currentness and qualification posture: current and accepted for the Block 7
  single-connection coordination layer over Blocks 3–6. Generation-bound
  restart safety, complete client conformance, internal combined-package proof,
  and final package-set qualification remain pending Blocks 8–9, 13, and 14.
- Downstream and Stop audit: source, tests, fixtures, documentation, builds, and
  review remained repository-local and domain-neutral. No downstream consumer,
  adapter, pin, repository operation, fixture, test, cutover, or acceptance was
  imported, invoked, changed, or claimed. No automatic restart, backoff,
  cross-generation state replacement, product approval policy, public listener,
  or service runtime was added.
- License/release posture: `no-license-selected/unpublished`.

### Stop

Stop before automatic restart, backoff, or cross-generation state replacement.

---

## Block 8 — Implement generation-bound restart safety

Status: `completed`

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

- Exact accepted source: pushed repository commit
  `ee429fcb99c6e75bd0ba0e327e86a87fde5d9b9d`, tree
  `0f7f6a69dc5f0e004387daa4ea6ad4904d39145e`; `HEAD`, `main`, and
  `origin/main` matched with a clean worktree after exact-revision review.
- Distribution/version and artifact root: `codex-app-server-client==0.1.0` at
  `packages/codex-app-server-client`, import root
  `codex_app_server_client`. Both isolated builds produced
  `codex_app_server_client-0.1.0-py3-none-any.whl` with identical SHA-256
  `6998c5c0427ddd4f5c44f8b9b587686ec008fe641a9a433f89b602cbe56e1bc4`;
  the frozen root remains exactly 92 exports and the `ClientLimits` and
  `replace` signatures remain exact.
- Generation and ownership behavior: replacement retires and quiesces the old
  engine before claiming a new owner, assigns one immutable integer generation
  per attempt, and gates calls, writes, responses, notifications, callbacks,
  cancellation, timeout, close, and publication against that generation.
  Replacement accepts only exact package-owned stdio/socket transports and
  cleanup-proven owned injected transport on a lifetime that began with a
  cleanup-provable package transport. Structural and borrowed injected wrapper
  reuse reject before claim, including fresh-wrapper identities over one
  buffered wire. Declared and actual weak lineage identities are independently
  checked, capacity-reserved, recorded before acceptance or cleanup, pruned,
  and privately bounded.
- Cancellation and cleanup behavior: component-originated zero-count
  cancellation at hook, lineage, start, initialization, raw read, or raw close
  boundaries becomes a content-free typed failure. Genuine caller cancellation
  remains cancellation after retained cleanup; cancellation after transport
  claim leaves terminal `cleanup-failed`, prevents a successor claim, and makes
  close return the retained typed diagnostic rather than imply cleanup.
  Backoff remains one caller-supplied bounded synchronous delay decision, not a
  package retry loop or retry policy. Public request capacity now rejects any
  value whose derived request history is not representable before transport
  claim.
- Focused, full-source, quality, and artifact proof: all 88 session tests and
  all 160 client source tests passed on Python 3.11 and 3.14 with asyncio debug
  and runtime-warning enforcement. The full maintained repository quality and
  protocol mutation checks passed after one targeted formatting pass over only
  touched Python files. Isolated installed-wheel suites passed on both
  interpreters with the identical artifact hash above.
- Compatibility inputs and roots: official Codex `0.147.0`, source commit
  `be6e8eac029b183056b7e4402879f15d2c85f61b`, retained byte root
  `eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa`,
  public API root
  `11e02c9c460821ebd5dd08f80b6544eb45b2217a53b90918ca472c26d14e1a21`,
  and selected-surface root
  `9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`.
  No retained protocol, official-binary input, or selected capability changed,
  so the accepted Block 6 official-binary smoke remains valid.
- Independent review: distinct reviewer `/root/block0_reviewer` returned
  `ACCEPT` for the exact pushed commit after independently reproducing the 160
  tests on both interpreters, full quality/protocol checks, both installed-wheel
  suites, the 92-export surface, exact signatures, scope, and clean remote
  revision. No material finding remained.
- Currentness and qualification posture: current and accepted for the Block 8
  generation-bound recovery layer over accepted Blocks 3–7. Complete client
  distribution conformance, internal combined-package compatibility, and final
  current package-set qualification remain pending Blocks 9, 13, and 14. This
  evidence is an internal source/artifact handoff only; it is not a publication,
  release, or public reuse claim.
- Downstream and Stop audit: the exact diff is limited to restart documentation,
  client RPC/session implementation, and client tests. It imports, invokes,
  mutates, or validates no downstream consumer, adapter, pin, repository,
  fixture, test, cutover, or acceptance. No license, publication, release,
  automatic retry loop, retry budget, provider selection, process pool, remote
  failover, durable event ledger, supervision policy, or Block 9 work was added.

### Stop

Stop before full-distribution qualification or cross-package work.

---

## Block 9 — Freeze app-server client distribution conformance

Status: `completed`

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

- Repository commit: accepted pushed source
  `08c416da4202b7036110e33e43d34ea590054e2e`, tree
  `794650275e9a583c9f47276a271f65cc1020c4e8`; `HEAD`, local `main`,
  `origin/main`, and GitHub `main` independently resolved to that commit with a
  clean worktree.
- Package capability ID and version:
  `codex-app-server-client-package`,
  `codex-app-server-client==0.1.0`, package root
  `packages/codex-app-server-client`, public import
  `codex_app_server_client`.
- Artifact/root: `codex_app_server_client-0.1.0-py3-none-any.whl`, identical
  Python 3.11/3.14 SHA-256
  `1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9`.
  Its content root is
  `6ecc26e75197d06682fe9d8d0612edb1e56ead6d04c3a41cde1132e2618efd8f`:
  SHA-256 of compact sorted-key JSON plus terminal LF over all 302
  lexicographically sorted non-directory wheel members, with each entry
  recording path, uncompressed-byte SHA-256, and size; total uncompressed
  bytes `3,206,562`.
- Public API and compatibility roots: exactly 92 root exports, no raw RPC API,
  unchanged frozen public signatures, public API SHA-256
  `7a032cfe32425aae9166217bae18e59202afe509a465e34c8c74794b6b1fdf93`,
  and compatibility-fixture SHA-256
  `82e97c4564c04790d03750397d65b6989df529fbb21aedc14ae67cf96d759651`.
- Official inputs/currentness: Codex `0.147.0`, source commit
  `be6e8eac029b183056b7e4402879f15d2c85f61b`, official wrapper SHA-256
  `134063e133f0b4244fa3b251acf973d4fe4b4aeeacbdc135211bf480f59f1477`,
  retained schema root
  `eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa`,
  semantic schema root
  `4e5c64213673b670d2575d7b7670d2089d49f92a92c56f2d16618e4a8857813e`,
  and selected-surface root
  `9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`.
  The bounded official smoke resolved the exact binary, initialized one owned
  generation, completed one typed `thread/list(limit=1)`, confirmed the exact
  8 request/15 notification/3 callback/3 transport projection, and closed it.
- Deterministic conformance: one in-memory JSON-lines fake covers all eight
  typed operations, all 15 selected notifications, all three policy-neutral
  callbacks, disconnect, generation-safe replacement, stale-generation
  rejection, and exactly-once close. Installed/public-only tests execute the
  README example, verify the 92-export fixture and signatures, and use no
  private RPC escape, process, socket, filesystem, repository, or ambient
  singleton.
- Validation: the focused directionality/conformance proof passed; all 92
  focused session tests and all 167 client source tests passed on CPython
  3.11.15 and 3.14.4 under asyncio debug with runtime warnings promoted. Full
  repository quality and five protocol-contract mutation checks passed. Both
  isolated installed-wheel suites passed with the identical artifact hash
  above.
- Remediation closure: the first pushed candidate was rejected because a model
  shared by inbound and outbound schema documents could forward untyped nested
  extras. The accepted correction propagates exact inbound context through
  references, arrays, unions, named models, and anonymous objects while
  recursively rejecting omitted-schema extras in outbound operation params,
  callback responses, and initialization params before any write. Exact
  `TextUserInput`, `NetworkPolicyAmendment`, direct-construction serialization,
  anonymous granular-approval, no-write, and corrected-retry regressions pass.
- Independent review: distinct reviewer `/root/block0_reviewer` returned
  `ACCEPT` for the exact pushed commit after reproducing both rejected
  directionality cases and the anonymous inbound case; independently running
  focused and full dual-interpreter source tests, quality, both installed-wheel
  suites, official smoke/currentness, artifact/content-root recomputation,
  API/signature/export checks, remote-currentness, scope, and clean-tree audit.
  No material finding remains.
- Package qualification posture: `program-qualified` at exact pushed Block 14
  qualification revision `7f1674aa31dd64a1621bf1a746ba78e8f4c51305`,
  over unchanged package source `08c416da4202b7036110e33e43d34ea590054e2e`,
  package tree `17772f61da62b41d6d3551deebc474792aafe922`, and the
  immutable wheel/API/protocol roots above. The complete internal matrix and
  independent exact-revision review passed; currentness is proven through the
  frozen technical-source root
  `9ab96149f63a45429a44ae07e309b68bb4204b4e2e6f4da6a7a93acbd5547068`.
  Posture remains `no-license-selected/unpublished`. This is the first exact
  internal package handoff for a consumer adapter, but it does not claim any
  consumer pin, adoption, availability, production qualification, or reuse
  right. Registry collision warning: PyPI contains an unrelated third-party
  `codex-app-server-client==0.1.0` whose wheel SHA-256 is
  `8e2c9d322beb99702f3661c5366afede7fe89294c571ef5260fd9db23f597593`,
  not this program's exact wheel SHA-256
  `1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9`.
  That publication and its MIT license do not apply here. This internal
  package record must be resolved by the trusted source revision and artifact
  hashes above, never by bare public name/version or unconstrained registry
  installation.
- Downstream, Stop, and license audit: the accepted implementation is confined
  to this distribution, its repository verifier, and package-local smoke. It
  imports, invokes, mutates, or validates no downstream consumer, adapter, pin,
  repository, fixture, test, cutover, or acceptance; no Block 10+ behavior is
  present. Posture remains `no-license-selected/unpublished`; no license,
  publication, release, redistribution authority, or public reuse claim was
  added.

### Stop

Stop before implementing other package behavior or cross-package composition.

---

## Block 10 — Implement the embedded/service structural contract

Status: `completed`

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

- Accepted exact source: pushed commit
  `401f87a64349c636a66be2da656498e7d9cb58e3`, tree
  `3f208324277bcd51b29dde8c394ccca3fb64a017`. Local `HEAD`, local
  `main`, `origin/main`, and GitHub `main` independently resolved to that
  commit with a clean worktree.
- Package capability ID and version:
  `embedded-service-contract-package`,
  `embedded-service-contract==0.1.0`, package root
  `packages/embedded-service-contract`, public import
  `embedded_service_contract`.
- Artifact/root: `embedded_service_contract-0.1.0-py3-none-any.whl`, identical
  Python 3.11/3.14 SHA-256
  `2b36d7307c08cd6d7d95bfb86d4a240b6ab2a69de5b2c61bf75a54507c7ea18d`.
  Its content root is
  `c53432ff83c6b80483a95384af3c9058a3cd82c56ac774126f123a93dbff7113`:
  SHA-256 of compact sorted-key JSON plus terminal LF over all 10
  lexicographically sorted non-directory wheel members, with each entry
  recording path, uncompressed-byte SHA-256, and size; total uncompressed
  bytes `36,778`.
- Public API and compatibility inputs: exactly 19 root exports plus the frozen
  testing exports, constructor and protocol signatures, enum values, and error
  hierarchy; structural/public-API root
  `c59856708a4ac80a266a83c382e6541da2afc78a920379f654dd2af20211facd`,
  conformance-fixture root
  `31b33341b51c48b1e552f19600238b3dffd44c197cbfed5c1dd370e08de71ed4`,
  and supported-Python root
  `ffd6652354d681053411ad82de6e7e8c8a687cdf873514c773fbad03ad834d73`.
  The acceptance interpreters are CPython 3.11 and 3.14.
- Structural behavior: the package exposes only generic start, status, ordered
  event, idempotent cancel, terminal outcome, and structural-error shapes.
  Embedded references declare zero process owners and service-shaped
  references declare one; neither reference host starts a process. Explicit
  caller-supplied lineage keeps reference ownership deterministic and
  order-independent without a global allocator, shared state, or shared
  implementation runtime.
- Conformance and negative proof: both distinct neutral reference hosts pass
  the same contract. Exact envelope/ref/state coherence, terminal
  immutability, repeated-cancel idempotency, success/failure/cancelled history
  retention after a successor start, fresh-instance isolation, unique
  same-instance refs, cross-lineage isolation, unknown refs, cursor validity,
  single-process ownership, and exact public signatures are enforced.
  Deterministic fixtures reject duck envelopes, mismatched refs, stale state,
  terminal or repeated-cancel mutation, session-only history, reused refs,
  shared instance state, and out-of-order events.
- Validation: all 13 package tests passed from source and from the isolated
  installed wheel on CPython 3.11 and 3.14 with runtime warnings promoted.
  Full maintained repository quality and five protocol-contract mutation
  checks passed; the two interpreter builds produced the identical wheel hash
  above. Package-data resources in each installed wheel exactly matched the
  three recorded roots.
- Independent review: distinct reviewer `/root/block0_reviewer` rejected four
  earlier exact candidates, reproducing structural-envelope, history,
  ownership, API-freeze, ambient-lineage, and cancellation-schedule gaps. The
  reviewer then returned `ACCEPT` for exact commit `401f87a...` after
  reproducing every prior adversarial case; independently rerunning both
  source and installed-wheel interpreter suites, repository quality, artifact
  and content-root computation, resource/API checks, remote-currentness,
  inward-scope, license, and clean-tree audits. No material finding remains.
- Package qualification posture: `program-qualified` at exact pushed Block 14
  qualification revision `7f1674aa31dd64a1621bf1a746ba78e8f4c51305`,
  over unchanged package source `401f87a64349c636a66be2da656498e7d9cb58e3`,
  package tree `203c809f3d1ab2588df5ed83c08affde99f8010c`, and the
  immutable wheel/contract roots above. The complete internal matrix and
  independent exact-revision review passed; currentness is proven through the
  frozen technical-source root
  `9ab96149f63a45429a44ae07e309b68bb4204b4e2e6f4da6a7a93acbd5547068`.
  Posture remains `no-license-selected/unpublished`. These immutable values are
  the first eligible internal source/package handoff for structural conformance
  consumption, but they record no consumer adapter, pin, adoption,
  availability, production qualification, or reuse right.
- Downstream, Stop, and license audit: the accepted implementation is confined
  to this distribution and repository-owned quality checks. It imports,
  invokes, mutates, or validates no downstream consumer, adapter, repository,
  fixture, test, cutover, or acceptance; no Block 11+ behavior is present.
  Posture remains `no-license-selected/unpublished`; no license, publication,
  release, redistribution authority, or public reuse claim was added.

### Stop

Stop before cross-package composition or any service implementation.

---

## Block 11 — Implement the non-authoritative runtime-manifest package

Status: `completed`

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

- Accepted exact source: pushed commit
  `6f7a7ea3c105c7461e6cb4c83944dd094883f187`, tree
  `13aad3d7299095b02893e55356b1959929b525ca`. Local `HEAD`, local
  `main`, `origin/main`, and GitHub `main` independently resolved to that
  commit with a clean worktree.
- Package capability ID and version: `runtime-manifest-package`,
  `runtime-manifest==0.1.0`, package root `packages/runtime-manifest`, public
  import `runtime_manifest`.
- Artifact/root: `runtime_manifest-0.1.0-py3-none-any.whl`, identical Python
  3.11/3.14 SHA-256
  `f2e601d542272187998296f09d33b2235002d108fe07c0b3c89a678ea1d010ac`.
  Its content root is
  `db8f7f7d0b0105361f9b1380ff1d1cc432e720be02def65880a9ef484ad112a2`:
  SHA-256 of compact sorted-key JSON plus terminal LF over all 12
  lexicographically sorted non-directory wheel members, with each entry
  recording path, uncompressed-byte SHA-256, and size; total uncompressed
  bytes `33,954`.
- Public API and compatibility inputs: exactly 16 root exports plus three
  frozen testing exports, constructor and function signatures, error
  hierarchy, unavailable-reason enum values, and finite resource limits;
  public-API root
  `ab4c1d7fd98b6b405dc0a2f0fd2f31957dae8fb0872796f46ba4b448c34e0c37`,
  manifest-schema root
  `1f6a7c0a46e69600d0ec3ee0917da1be185fba0097e845e99f6152cd1a31ad18`,
  compatibility-fixture root
  `326aa3d0b865f24c12b385c5a6ac8b161cd1fa0c984ac9f7dadd7c2b05b0c7f9`,
  and supported-Python root
  `ffd6652354d681053411ad82de6e7e8c8a687cdf873514c773fbad03ad834d73`.
  The acceptance interpreters are CPython 3.11 and 3.14.
- Descriptive behavior: exact frozen component/version/content, protocol/schema
  feature, capability, and dependency records serialize to one canonical
  sorted compact JSON form with a terminal LF. Comparison is deterministic,
  treats observed descriptive supersets as compatible, and projects exact
  ordered unavailable reasons for every mismatch without taking runtime
  action. Unknown schema versions and malformed, recursive, oversized, or
  non-canonical scalar inputs fail through explicit package errors.
- Bounds and schema proof: document bytes, collection cardinality, feature
  cardinality, reason count, names, roots, and reason subjects are bounded
  before traversal, regex, hashing, sorting, or UTF-8 allocation. Tests cover
  lone surrogates, recursion, oversized integers and hostile object tuples,
  JSON integer `1` versus `1.0`, unknown-version discrimination before v1
  shape validation, and ECMA-262-safe treatment of U+2028/U+2029, later C0
  controls, and terminal newlines. Runtime-only cross-field and scalar-form
  invariants are explicitly recorded by the schema rather than implied.
- Validation: all 24 package tests passed from source and from the isolated
  installed wheel on CPython 3.11 and 3.14. Full maintained repository quality,
  pinned Ruff lint/format, and five protocol-contract mutation checks passed;
  the two interpreter builds produced the identical wheel hash above.
  Package-data resources in each installed wheel exactly matched the four
  recorded roots.
- Independent review: distinct reviewer `/root/block0_reviewer` rejected two
  earlier exact candidates, reproducing nine canonicality, limit-ordering,
  recursion, schema-parity, schema-version, and text-pattern defects. The
  reviewer then returned `ACCEPT` for exact commit `6f7a7ea...` after
  independently rerunning both source and installed-wheel interpreter suites,
  repository quality, artifact and content-root computation, resource/API
  checks, adversarial limit and schema cases, remote-currentness, inward-scope,
  license, and clean-tree audits. No material finding remains; standard JSON
  Schema consumers must honor the documented extension invariants or use the
  strict package parser.
- Package qualification posture: `program-qualified` at exact pushed Block 14
  qualification revision `7f1674aa31dd64a1621bf1a746ba78e8f4c51305`,
  over unchanged package source `6f7a7ea3c105c7461e6cb4c83944dd094883f187`,
  package tree `42cb7171d3de021a99f75ac741ea0a0cf97c84ae`, and the
  immutable wheel/schema/API roots above. The complete internal matrix and
  independent exact-revision review passed; currentness is proven through the
  frozen technical-source root
  `9ab96149f63a45429a44ae07e309b68bb4204b4e2e6f4da6a7a93acbd5547068`.
  Posture remains `no-license-selected/unpublished`. These immutable values are
  the first eligible internal source/package handoff for descriptive runtime
  metadata consumption, but they record no consumer adapter, pin, adoption,
  availability, authorization, acceptance, production qualification, or reuse
  right.
- Downstream, Stop, and license audit: the accepted implementation is confined
  to this distribution and repository-owned quality checks. It imports,
  invokes, discovers, mutates, or validates no downstream consumer, adapter,
  repository, fixture, test, cutover, or acceptance; no Block 12+ behavior is
  present. Posture remains `no-license-selected/unpublished`; no license,
  publication, release, redistribution authority, or public reuse claim was
  added.

### Stop

Stop before cross-package composition or downstream manifest adoption.

---

## Block 12 — Prove independent distribution isolation

Status: `completed`

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

- Exact accepted source: pushed commit
  `dbdc63a2f678980f1834555410541afaefc1e967`, tree
  `6633cdaa7c1f73950aefa8383b40b1a4bcc37968`; `HEAD`, `main`,
  `origin/main`, and the remote branch matched the independently reviewed
  candidate and the worktree was clean.
- Maintained isolation owner: `scripts/check_package.py`, its 22-test negative
  audit contract in `scripts/test_check_package.py`, the frozen distribution
  and dependency input in `tools/package_matrix.json`, package-isolation CI in
  `.github/workflows/ci.yml`, and the operator contract in
  `docs/development.md`. The command requires package-local tests and builds
  each wheel into its own clean environment with no other admitted package
  installed.
- Frozen-input and wheel-boundary proof: every package is copied into separate
  pristine-acceptance and PEP 517 build snapshots. Exact whole-file snapshot
  records are verified before and after build; metadata, retained resources,
  source members/bytes, and tests are read only from the pristine snapshot.
  The audit rejects source injection or mutation, build/test/resource
  rewriting, duplicate or unsafe ZIP members including directories,
  file/directory collisions, unexpected top-level roots, missing wheel
  metadata, and source/package-data divergence.
- Exact declared-dependency proof: each source `pyproject.toml` and built wheel
  has the frozen ordered empty runtime-requirement tuple. Observed wheel imports
  have no external roots. Unadmitted, undeclared, unobserved, circular, and
  source-self-authorized dependencies fail with explicit diagnostics; no
  package is admitted implicitly from mutable source metadata.
- Exact distribution artifacts on Python 3.11 and 3.14:
  `codex-app-server-client==0.1.0` at
  `packages/codex-app-server-client`, import root
  `codex_app_server_client`, wheel SHA-256
  `1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9`,
  content root
  `6ecc26e75197d06682fe9d8d0612edb1e56ead6d04c3a41cde1132e2618efd8f`,
  pristine snapshot root
  `00e12d1bc4c9828219973936c1101da7d0e19488a5c683e99f7eb6b635fa6f4b`,
  and 167 tests;
  `embedded-service-contract==0.1.0` at
  `packages/embedded-service-contract`, import root
  `embedded_service_contract`, wheel SHA-256
  `2b36d7307c08cd6d7d95bfb86d4a240b6ab2a69de5b2c61bf75a54507c7ea18d`,
  content root
  `c53432ff83c6b80483a95384af3c9058a3cd82c56ac774126f123a93dbff7113`,
  pristine snapshot root
  `44c22f3efda218b3f4873b1772a00dcf60530e121613f36c3651ec80c73fb9ba`,
  and 13 tests; and `runtime-manifest==0.1.0` at
  `packages/runtime-manifest`, import root `runtime_manifest`, wheel SHA-256
  `f2e601d542272187998296f09d33b2235002d108fe07c0b3c89a678ea1d010ac`,
  content root
  `db8f7f7d0b0105361f9b1380ff1d1cc432e720be02def65880a9ef484ad112a2`,
  pristine snapshot root
  `94b073384b23c41b9b7a1c8b26ae1e4baaddbe6d35477f7c3b1e8f644f884b72`,
  and 24 tests. All artifact values were byte-identical across interpreters.
- Validation: both complete `UV_OFFLINE=1` Python 3.11 and Python 3.14
  isolated-wheel matrices passed, as did all 22 focused verifier tests, the
  maintained repository quality command, Ruff, the exact protocol checks, and
  all five protocol-mutation negatives. Child command failures retain bounded
  output and exact exit diagnostics.
- Independent review: distinct read-only reviewer `/root/block0_reviewer`
  returned `ACCEPT` for the exact pushed candidate after closing pristine-build
  separation and ZIP-entry type/path findings. The reviewer independently
  reproduced both interpreters, the full isolated matrices, all focused and
  maintained quality checks, exact wheel/content/resource counts and roots,
  and the repository-scope audit, and found no remaining material issue.
- Currentness and qualification posture: current and accepted for independent
  distribution isolation over the frozen Block 9–11 package sources. This is
  an internal technical verification boundary only; combined installation and
  composition remain Block 13, and final package-set qualification remains
  Block 14.
- Downstream and Stop audit: the accepted delta is confined to repository
  tooling, tests, CI, matrix metadata, and documentation. It imports, installs,
  invokes, discovers, mutates, or validates no downstream consumer, adapter,
  repository, fixture, test, cutover, or acceptance; it did not install all
  three distributions together or implement Block 13 composition. Posture
  remains `no-license-selected/unpublished`; no license, publication, release,
  redistribution authority, or public reuse claim was added.

### Stop

Stop before installing all distributions together or testing composition.

---

## Block 13 — Prove neutral cross-package composition

Status: `completed`

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

- Exact accepted source: pushed commit
  `0261d9ede7ef458b9a8ecf57461ee6449c6f5147`, tree
  `0dde0408e65a65a214e1b6558d70a936a1dc7262`; `HEAD`, `main`,
  `origin/main`, and the independently reviewed immutable candidate matched and
  the worktrees were clean.
- Combined-install owner: `scripts/check_composition.py` rebuilds the three
  accepted package snapshots separately, requires their exact Block 12 wheel
  byte and content roots from `tools/composition_matrix.json`, installs only
  those local wheels together without dependency resolution into one clean
  environment, and runs the test-only `tests/neutral_composition.py` fixture
  under isolated Python. CI exercises the same job on Python 3.11 and 3.14.
- Exact unchanged artifacts: `codex-app-server-client==0.1.0` wheel SHA-256
  `1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9`
  and content root
  `6ecc26e75197d06682fe9d8d0612edb1e56ead6d04c3a41cde1132e2618efd8f`;
  `embedded-service-contract==0.1.0` wheel SHA-256
  `2b36d7307c08cd6d7d95bfb86d4a240b6ab2a69de5b2c61bf75a54507c7ea18d`
  and content root
  `c53432ff83c6b80483a95384af3c9058a3cd82c56ac774126f123a93dbff7113`;
  and `runtime-manifest==0.1.0` wheel SHA-256
  `f2e601d542272187998296f09d33b2235002d108fe07c0b3c89a678ea1d010ac`
  and content root
  `db8f7f7d0b0105361f9b1380ff1d1cc432e720be02def65880a9ef484ad112a2`.
  Both interpreter runs reproduced every value exactly.
- Public-only fixture proof: the formatted fixture is frozen at SHA-256
  `7a7a112b345d1f7aa979b1627a6a9d90b76f3548953cafb97f45e2d3ff3e9f49`.
  Its exact ordered imports, aliases, complete documented root-module attribute
  sets, and non-escaping module-object uses are statically enforced. Private or
  nested package access, alias/reflection bypass, dynamic import/evaluation,
  module-registry access, effectful stdlib imports, external imports, and
  incomplete public reachability all reject.
- Neutral scenario result: the installed app-server client validates the
  packaged Codex `0.147.0` schema and selected surface, initializes generation
  1 over one owned in-memory injected channel, performs one typed empty thread
  list, and closes the channel exactly once. Installed embedded and service
  reference fixtures each pass three structural scenarios with six observed
  events; their combined declared process-owner count is exactly one.
- Manifest and incompatibility proof: the exact three package content roots,
  app-server schema root
  `eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa`,
  and selected-surface root
  `9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`
  produce canonical manifest SHA-256
  `ebf1ec63705d7731adb7ec19501cdb33cf36ace5a11475fa2f2499bea00bc51f`.
  Independent single-root mutations return one exact full diagnostic each:
  `dependency-root` for `embedded-service-contract` and `protocol-schema` for
  `codex-app-server-surface`, with exact accepted and zeroed `sha256:` values.
  Boolean schema versions, hidden capability/field drift, reordered or
  duplicate diagnostics, mixed roots, and changed package/protocol versions
  fail closed.
- Validation and independent review: both complete `UV_OFFLINE=1` Python 3.11
  and 3.14 combined jobs passed with identical outputs, as did all four focused
  composition-audit groups and the maintained quality, Ruff, protocol,
  protocol-mutation, repository-boundary, and Block 12 isolation checks.
  Distinct reviewer `/root/block0_reviewer` returned `ACCEPT` after four
  remediation cycles and independently reproduced the exact artifacts,
  manifest, diagnostics, lifecycle/client results, and scope audit.
- Currentness and qualification posture: current and accepted for the one
  frozen neutral installed-wheel composition over Blocks 9–12. This is an
  internal test boundary only; complete technical package-set qualification
  remains Block 14.
- Downstream and Stop audit: the accepted delta contains only repository
  tooling, CI, documentation, frozen matrix inputs, and a test-only fixture. No
  package source or public API changed; no production facade, service, adapter,
  product field, downstream identifier, checkout, process, fixture, test,
  cutover, pin, or acceptance was added or invoked. Posture remains
  `no-license-selected/unpublished`; no license, publication, release,
  redistribution authority, or public reuse claim was added.

### Stop

Stop before terminal qualification, authority audit, or release posture.

---

## Block 14 — Qualify the frozen technical package set

Status: `completed`

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

- Exact frozen revisions: technical candidate
  `2150966402474bb633c01d04eca0a1bc8309d941` and exact pushed qualification
  revision `7f1674aa31dd64a1621bf1a746ba78e8f4c51305`, tree
  `45b097ed4f297ed15238e5d6ef865b4b8a84ebd5`. Local `HEAD`, local `main`,
  `origin/main`, and GitHub `refs/heads/main` matched the qualification
  revision and the worktree was clean.
- Frozen technical source: `tools/qualification_matrix.json` binds all 367
  tracked files and Git modes at the candidate to SHA-256
  `9ab96149f63a45429a44ae07e309b68bb4204b4e2e6f4da6a7a93acbd5547068`.
  Only mutable `docs/tracker.md` evidence and the self-referential
  qualification JSON are excluded. Maintained quality and CI require an exact
  externally supplied `HEAD`; new, changed, deleted, or mode-changed tracked
  technical files reject stale proof.
- Exact package reconciliation: `codex-app-server-client==0.1.0` preserves
  source `08c416da4202b7036110e33e43d34ea590054e2e`, package tree
  `17772f61da62b41d6d3551deebc474792aafe922`, wheel SHA-256
  `1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9`,
  and content root
  `6ecc26e75197d06682fe9d8d0612edb1e56ead6d04c3a41cde1132e2618efd8f`;
  `embedded-service-contract==0.1.0` preserves source
  `401f87a64349c636a66be2da656498e7d9cb58e3`, package tree
  `203c809f3d1ab2588df5ed83c08affde99f8010c`, wheel SHA-256
  `2b36d7307c08cd6d7d95bfb86d4a240b6ab2a69de5b2c61bf75a54507c7ea18d`,
  and content root
  `c53432ff83c6b80483a95384af3c9058a3cd82c56ac774126f123a93dbff7113`;
  `runtime-manifest==0.1.0` preserves source
  `6f7a7ea3c105c7461e6cb4c83944dd094883f187`, package tree
  `42cb7171d3de021a99f75ac741ea0a0cf97c84ae`, wheel SHA-256
  `f2e601d542272187998296f09d33b2235002d108fe07c0b3c89a678ea1d010ac`,
  and content root
  `db8f7f7d0b0105361f9b1380ff1d1cc432e720be02def65880a9ef484ad112a2`.
  Every runtime-dependency and observed external-import inventory is empty.
- API, compatibility, and documentation proof: each distribution's exact
  package-owned API/schema/fixture set is required without additions or
  omissions; protocol schema root
  `eb325d394d19f2f8d133203885b3d1c2f74dbc5a176f22078a4f99aae5926faa`,
  selected-surface root
  `9a773e75f2e5aa827b4cc711345bd9ca1bc2a037f19d114284a04f306097a42f`,
  neutral fixture SHA-256
  `7a7a112b345d1f7aa979b1627a6a9d90b76f3548953cafb97f45e2d3ff3e9f49`,
  and canonical manifest SHA-256
  `ebf1ec63705d7731adb7ec19501cdb33cf36ace5a11475fa2f2499bea00bc51f`
  remain unchanged. Each exact package README contains and executes its own
  public-import example; swapped, missing, duplicated, or invalid examples
  fail qualification.
- Complete internal matrix: one consolidated offline exact-revision run passed
  maintained quality, 16 focused qualification negatives, protocol/schema
  mutations, Ruff lint/format, all-package isolated build/install/import/test
  on CPython 3.11 and 3.14, and neutral combined composition on both
  interpreters. Both interpreters produced byte-identical wheels and identical
  typed composition results.
- Independent review: distinct reviewer `/root/block0_reviewer` rejected two
  earlier candidates after directly reproducing loose source ancestry,
  incomplete contract inventories, misowned examples, incomplete source
  inventory, and optional-currentness defects. The reviewer returned `ACCEPT`
  for exact pushed revision `7f1674aa...` only after every prior mutation
  failed closed, the one consolidated matrix passed, all roots were
  independently recomputed, and remote currentness and clean-tree state were
  confirmed. No technical finding remains open.
- Final technical posture: all three package records are `program-qualified`
  at exact pushed revision `7f1674aa...` and remain
  `no-license-selected/unpublished`. This is internal package evidence only;
  no downstream repository, adapter, pin, fixture, test, cutover, adoption,
  availability, production acceptance, license, publication, release,
  redistribution authority, or public reuse claim was touched or inferred.

### Stop

Stop before authority/downstream audit, license action, publication, or release.

---

## Block 15 — Audit authority and downstream non-interaction

Status: `completed`

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

- Exact reviewed candidate: pushed revision
  `4d6658e103180320fb8d2a1faab6051a57ccd4cc`, tree
  `d9f68a953b18d3a65fd108f761c2f8b9113d5297`; local `HEAD`, local
  `main`, `origin/main`, and GitHub `refs/heads/main` matched and the worktree
  was clean. Its delta from accepted Block 14 changes only tracker status, so
  the accepted technical proof remained current without rerunning the complete
  matrix.
- Downstream-interaction audit: no package source, test, fixture, artifact
  input, composition input, tool command, qualification record, or CI runtime
  path imports, names, opens, invokes, mutates, or validates Software Factory,
  libRSI, Patent Studio, or another downstream consumer. Their names occur
  only in repository-level admission/boundary documentation and negative
  import checks; no consumer pin, handoff operation, adapter, or acceptance
  state exists.
- Authority/import matrix:

  | Surface | Imports or effects | Authority boundary | Result |
  | --- | --- | --- | --- |
  | `codex-app-server-client` | Standard library; explicit official Codex binary, local socket, or caller-injected channel | Caller supplies identity, transport, backoff, requests, configuration values, and approval responses; Codex supplies protocol results/events | clean |
  | `embedded-service-contract` | Standard library; starts no process and owns no server, runner, scheduler, or persistence | Host owns execution and request/event/result/failure meaning; package checks structural lifecycle invariants only | clean |
  | `runtime-manifest` | Standard library; no discovery, credential lookup, installation inference, or mutation | Caller supplies every descriptive component, version, root, protocol, feature, capability, and dependency | clean |
  | tests, composition, CI | Package-local fakes, temporary local process/socket fixtures, isolated wheels, and public-only neutral composition | Internal conformance only; no product, downstream, or release authority | clean |
  | release surface | Read-only CI permissions; no credentials, publish/upload/release job, tag, license file, or license metadata | No release authority exists in this repository | clean |

- Exported-authority audit: the client has 92 exact root exports, the lifecycle
  contract 19, and the manifest 16; none is authority-named or imports an
  external distribution. Approval callbacks carry typed requests and require
  caller-supplied responses; they never choose approval or policy. Lifecycle
  terminal states are structural observations, not product outcomes or QA
  acceptance. Manifest `compatible` means only that no exact descriptive
  mismatch was found and cannot authorize execution, adoption, or release.
- Retained upstream limitation: the exact 285-file official Codex schema
  snapshot includes passive account, authentication, API-key,
  configuration-write, marketplace, plugin, and MCP-management definitions.
  None overlaps the closed selected surface or generated public model graph;
  there is no raw-call API, sensitive method export, or credential owner, and
  unselected traffic fails closed. Selected thread operations may transport
  caller-provided configuration, sandbox, or approval values, but this package
  supplies no defaults or policy meaning.
- Finding closure: targeted searches, AST import/export inspection,
  dependency metadata, retained contract/schema inspection, exact
  qualification currentness, CI permissions/effects, Git tags, and license
  inventory all passed. Every apparent authority term was either explicit
  negative exclusion metadata, neutral protocol terminology, or passive
  unselected upstream compatibility data; no corrective code change or
  technical-proof invalidation was required.
- Independent semantic review: distinct reviewer `/root/block0_reviewer`
  returned `ACCEPT` for exact revision `4d6658e...` after independently
  inspecting package source, retained schemas, public APIs, tests, fixtures,
  examples, commands, artifact composition evidence, and CI paths. The review
  confirmed the matrix and retained limitations above and found no open
  authority or downstream-interaction issue.
- Scope and posture: the audit was entirely inward-facing and read-only. No
  downstream repository was opened or tested; no license, publication,
  release, credential, announcement, adoption, or external mutation occurred.
  All package records remain `program-qualified` and
  `no-license-selected/unpublished`.

### Stop

Stop before license grant, publication, release, announcement, or downstream
adoption.

---

## Block 16 — Record no-license/unpublished posture and close the program

Status: `completed`

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

- Exact reviewed terminal candidate: pushed revision
  `fb97344bdccec2b05bc6ea4d158c1ac5b4b4e83e`, tree
  `239c8fde8887acde81933c252ff8d3ae909a5dad`; local `HEAD`, local
  `main`, `origin/main`, and GitHub `refs/heads/main` matched and the worktree
  was clean. Its delta from accepted Block 15 is confined to tracker status
  and terminal evidence; the exact qualification/currentness and maintained
  quality checks passed and no package or artifact byte changed.
- Final internal completion manifest: this canonical tracker retains all Block
  0–15 package, conformance, documentation, authority, review, and exact Git
  evidence. `tools/qualification_matrix.json` retains technical candidate
  `2150966402474bb633c01d04eca0a1bc8309d941`, source root
  `9ab96149f63a45429a44ae07e309b68bb4204b4e2e6f4da6a7a93acbd5547068`,
  the two-interpreter matrix, exact source commits/package trees, empty
  dependency inventories, and immutable wheel/API/schema/composition roots.
- Exact repository release posture: within the `estill01/utils` program, all
  three qualified artifacts remain `no-license-selected/unpublished`. There is
  no license file, package license field, license classifier, publication
  configuration, registry credential, publish/upload job, writable CI release
  permission, Git tag, GitHub Release, announcement, support promise, public
  reuse grant, or redistribution authority. Public repository visibility and
  internal technical qualification change none of those facts.
- Registry-name limitation, checked 2026-08-23: PyPI contains an unrelated
  third-party `codex-app-server-client==0.1.0` by Paras Doshi under MIT, with
  wheel SHA-256
  `8e2c9d322beb99702f3661c5366afede7fe89294c571ef5260fd9db23f597593`.
  It is not this program's exact internal wheel SHA-256
  `1e9dc5b9c7f2edb9676b5a47eb2c9b96498f1b429acec474cd26702fe8e3fdb9`;
  its publication and license apply only to its bytes and cannot be inherited
  by this package set. The internal client must be identified and consumed
  only by exact trusted repository revision and artifact hashes, never by bare
  public distribution name/version or unconstrained registry install.
  `embedded-service-contract` and `runtime-manifest` returned `404` from PyPI
  at review time; that neither reserves those names nor promises future
  availability.
- Final package records: client source `08c416da...`, embedded-contract source
  `401f87a...`, and runtime-manifest source `6f7a7ea...` retain their exact
  Block 14 package trees, wheel/content hashes, public contracts, and
  `program-qualified` posture. They record internal source/artifact identity
  only and describe no publicly installable or reusable dependency, consumer
  pin, downstream availability, adoption, production acceptance, or release.
- Retained technical and semantic limitations: the client retains the full
  passive official upstream schema snapshot while exposing only its closed
  selected surface; explicit Codex operations can cause upstream work and
  caller-provided approval/configuration values keep caller/upstream meaning.
  The lifecycle contract owns structure rather than product outcome meaning,
  and runtime-manifest compatibility remains descriptive rather than
  authoritative. Block 15's exact semantic audit remains controlling.
- Separately authorized successor conditions:

  - License selection requires explicit legal/owner authority that names the
    exact terms, artifacts, and scope.
  - Registry publication requires separate release authority, registry
    ownership, a collision-safe distribution identity/version, credentials,
    fresh artifact qualification, and explicit publication checks.
  - A Git tag or GitHub Release requires a separately authorized version and
    release plan plus fresh exact-revision review.
  - Downstream adoption requires a consumer-owned tracker, exact trusted
    revision/artifact-hash selection, consumer-side adapters, fixtures, tests,
    cutover, and acceptance in that consumer repository.
  - An unrelated utility requires fresh two-consumer admission and its own
    dependency-ordered tracker work; terminal cleanup cannot admit it.

- Prohibited effects and final Stop: this Block performed metadata,
  registry-currentness, Git-currentness, and release-surface checks only. It
  added no license, package metadata, tag, GitHub Release, publication,
  credential, announcement, consumer handoff, downstream repository action,
  adapter, pin, fixture, test, cutover, adoption, or unrelated package.
- Terminal review: distinct reviewer `/root/block0_reviewer` independently
  confirmed the exact package metadata/artifacts, qualification posture,
  license inventory, read-only CI, empty tag/Release state, registry facts,
  downstream boundary, and Git currentness. The reviewer rejected predecessor
  `fdf9953...` until the registry collision and successor-activation conditions
  were explicit, then returned `ACCEPT` for exact pushed candidate
  `fb97344...`. No terminal finding remains open.

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
