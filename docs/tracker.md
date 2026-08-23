# Shared Domain-Neutral Utilities Implementation Tracker

- Tracker status: `planning`
- Tracker sequence: Blocks 0–8
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
- Observable completion: Blocks 0–8 are accepted at exact current pushed
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
- Direct product sources: repository `AGENTS.md`, repository `README.md`, the official
  Codex app-server protocol/schema selected in Block 1, and the direct user
  instruction that implementation remain inwardly focused.
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
  do not create adapters, product fixtures, generalized orchestration, or
  future-use helpers.
- Tradeoffs: separate distributions add packaging overhead but keep dependency
  and compatibility boundaries explicit; excluding downstream cutovers leaves
  adoption proof to each consumer's own repository and authority.
- Uncertainty: future downstream adoption, license selection, and publication
  are separate programs and do not block internal technical completion.

## 2. Target architecture and authority boundaries

```text
packages/
  codex-app-server-client/     official protocol/process/transport mechanics
  embedded-service-contract/  neutral lifecycle protocols/test fixtures
  runtime-manifest/            descriptive version/compatibility metadata

neutral in-repository fakes and reference hosts
                  │
                  └── prove package contracts and composition

downstream applications import packages under their own programs
utils imports, operates, and tests against no downstream application
```

The app-server client owns exact binary/version resolution, schema
compatibility, selected local transports, bounded JSON-RPC, initialization,
events, server-initiated callbacks, cancellation/disconnect, restart-safe client
state, and deterministic fake-server conformance. It does not own tasks,
prompts, missions, product retries, application effects, or downstream adapters.

The embedded/service package owns structural conformance protocols and fixtures
only. It does not own a runtime, service runner, product lifecycle, outcome, or
state. The runtime-manifest package owns deterministic descriptive metadata
only. Authorization and acceptance are deliberately absent from its schema.

### External consumer boundary

- Downstream systems may justify admission through read-only evidence.
- Consumer-specific identifiers may appear only in a bounded admission record
  when necessary to prove the admission rule; they do not appear in exported
  APIs, schemas, fixtures, examples, or test data.
- This program creates no downstream branch, adapter, pin, migration, test run,
  handoff requirement, cutover, deletion, or acceptance claim.
- Downstream repositories own every later adoption and all resulting behavior,
  authority, persistence, and release effects.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Codex app-server protocol | exact official CLI/source/schema selected in Block 1 | reference and pin; do not fork protocol semantics |
| App-server package API and compatibility | `codex-app-server-client` | own only domain-neutral client mechanics |
| Embedded/service structural contract | `embedded-service-contract` | own protocols and conformance fixtures, not host state |
| Runtime compatibility metadata | `runtime-manifest` | own descriptive projections, not authority |
| Package builds and quality | repository package metadata and CI | implement per distribution and in isolated environments |
| Downstream behavior and adoption | each external consumer's own repository | out of scope; never imported, operated, or modified here |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Repository instructions and initial tracker | repository commit `1dd28b20cbf817d94d418cd8d177c4182f687314`; predecessor tracker SHA-256 `dd76f3e968ed6a86e03110131e142b59d2e652e16ecdefa8e5ed976ca2ebfb31` | preserve instructions; replace plan prospectively | 0–8 | execute the inward-only program below |
| Official Codex app-server protocol | resolve exact CLI/source revision and generated schema root in Block 1 | reference/pin | 1–3 | freeze supported surface and compatibility policy |
| Existing generic client implementations | resolve any inspected source revisions in Block 1 | adapt selectively as read-only evidence | 1–3 | reimplement only neutral behavior; import or runtime dependency prohibited |
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
implementation. If a candidate fails one condition, omit or defer it rather
than building a speculative package.

## 6. Block execution contract

1. Execute Blocks 0–8 through the dependency graph below; tracker authoring
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
8. Push accepted coherent checkpoints without force. A package build, commit,
   review, or push is nonterminal.
9. Do not add a license, publish to a package index, create a GitHub Release,
   announce availability, or claim reuse rights under this program.

### Decision and continuation contract

- Ordinary package/API choices supported by the frozen contract proceed without
  a user gate.
- If admission evidence fails for a proposed distribution, that distribution
  and its descendants are omitted or deferred; dependency-independent packages
  continue.
- The current release posture is `no-license-selected/unpublished`. Recording
  that truthful posture requires no additional decision and does not grant
  reuse rights.
- A later request to add a license, publish, release, or implement downstream
  adoption is a separate successor with its own authority and scope.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
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

### 2026-08-23 inward-only amendment and numbering map

No predecessor Block had started or accumulated implementation evidence. The
prospective map is:

| Predecessor Block | Current disposition |
|---:|---|
| 0 | Current Block 0 |
| 1 | Current Block 1 |
| 2 | Split into current Blocks 2–3 |
| 3 | Current Block 4 |
| 4 | Current Block 5 |
| 5 | Current Block 6, narrowed to internal conformance |
| 6–8 | Removed from this repository program as downstream-consumer work |
| 9 | Split into current Blocks 7–8 |

| Block | Functionality targeted | Depends on | Status |
|---:|---|---:|---|
| 0 | Establish package layout, admission proof, dependency rules, CI baseline, and the no-downstream boundary | — | `not-started` |
| 1 | Freeze the exact official Codex app-server protocol surface and public client contract | 0 | `not-started` |
| 2 | Implement schema/version handling, local transports, and bounded JSON-RPC core | 1 | `not-started` |
| 3 | Implement initialization, typed lifecycle/events/callbacks, restart safety, and deterministic fake-server conformance | 2 | `not-started` |
| 4 | Implement neutral embedded-versus-service lifecycle protocols and fixtures | 0 | `not-started` |
| 5 | Implement deterministic non-authoritative runtime/version manifests | 0 | `not-started` |
| 6 | Prove isolated installation and neutral internal composition of all packages | 3–5 | `not-started` |
| 7 | Qualify the frozen internal package set and audit API, dependency, and authority boundaries | 6 | `not-started` |
| 8 | Record the no-license/unpublished posture and close without publication or downstream adoption | 7 | `not-started` |

Required order:

```text
0 → 1 → 2 → 3 ┐
0 → 4         ├→ 6 → 7 → 8
0 → 5         ┘
```

## Block 0 — Establish the inward-only repository and package baseline

Status: `not-started`

### Objective

Create the independently distributable monorepo contract, admit only supported
packages, and make downstream non-interaction an executable repository rule.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: narrow package ownership, admission discipline, and
  an enforceable inward-only implementation boundary.
- Potential capability loss or regression: a generic repository could become a
  dumping ground or quietly couple to named consumers.
- Protected-capability effect: independent distribution and external consumer
  ownership remain intact.
- Architecture and operating-model effect: separate packages share one
  repository and CI without sharing one import namespace.
- Tradeoff and source evidence: repository instructions and direct user scope;
  extra packaging work is accepted to prevent a grab-bag dependency.

### Inputs and dependencies

- Repository instructions, README, current tracker, and bounded read-only
  admission evidence for each proposed distribution.

### Required work

- Define package directories, import namespaces, dependency rules, version
  policy, supported Python baseline, build metadata, compatibility policy, CI
  matrix, and changed-test map.
- Classify each initial distribution against all six admission conditions.
- Define the exact prohibited downstream interactions for package source,
  tests, fixtures, examples, commands, and CI.

### Scope and non-goals

- In scope: repository/package contract, admission decisions, packaging
  skeletons, and internal quality baseline.
- Not in scope: utility behavior, downstream adapters, or consumer repository
  changes.
- No top-level `utils` import.

### Deliverables and recorded state

- Architecture/admission documentation, independent package skeletons, pinned
  baseline roots, CI skeleton, and internal changed-test map.

### Resource and economy contract

Read and hash each admission/source record once; run packaging smoke only and no
downstream suite or command.

### QA and independent review

Review package necessity, naming, dependency direction, authority leakage,
release coupling, and the enforceability of the external-consumer boundary.

### Acceptance

- Every retained package satisfies admission, builds as an independent
  skeleton, has one compatibility owner, and declares no downstream runtime or
  test dependency.

### Negative tests

- Reject a one-consumer speculation, product import/path/fixture, common model,
  shared authority, top-level `utils` API, or non-independent distribution.

### Completion evidence

Pending.

### Stop

Stop before implementing protocol or package behavior.

---

## Block 1 — Freeze the official app-server protocol and client contract

Status: `not-started`

### Objective

Bind one exact official app-server protocol/schema target and define the
domain-neutral public client surface before implementation.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: protocol fidelity and a reviewable package API.
- Potential capability loss or regression: an overbroad API could expose raw
  methods or freeze unstable upstream behavior.
- Protected-capability effect: exact compatibility, explicit process ownership,
  and downstream adapter freedom remain.
- Architecture and operating-model effect: separates protocol/transport core
  from typed lifecycle behavior implemented in Blocks 2–3.
- Tradeoff and source evidence: official generated schemas and current CLI
  behavior; a narrowed surface is preferred to a general raw RPC bridge.

### Inputs and dependencies

- Block 0 and an exact official Codex CLI/source revision.

### Required work

- Generate and hash the official schemas in a disposable directory.
- Select the stable methods, notifications, callbacks, transports, error
  shapes, and capability probes required by the package objective.
- Define the public Python API, schema compatibility rule, version policy, and
  deterministic update procedure.
- Classify any inspected prior implementation only as reusable neutral behavior
  or excluded product behavior; copy no consumer API or product type.

### Scope and non-goals

- In scope: official source/schema contract and public package design.
- Not in scope: package implementation, raw arbitrary methods, remote public
  proxying, WebSocket baseline, or consumer behavior.

### Deliverables and recorded state

- Upstream manifest, schema root, supported-feature matrix, public API contract,
  compatibility/update policy, and implementation proof plan.

### Resource and economy contract

Generate the official schemas once, reuse the resulting root, and perform only
bounded static classification before implementation review.

### QA and independent review

Review upstream fidelity, public-surface minimality, schema currentness,
transport selection, and absence of product semantics.

### Acceptance

- The exact upstream target and supported surface are reproducible, every
  exported capability is necessary, and Blocks 2–3 have unambiguous ownership
  and Stop boundaries.

### Negative tests

- Reject an unpinned schema, arbitrary RPC escape hatch, unstable feature as a
  baseline requirement, product type, hidden process owner, or undocumented
  compatibility change.

### Completion evidence

Pending.

### Stop

Stop before implementing transport or client code.

---

## Block 2 — Implement app-server compatibility and transport core

Status: `not-started`

### Objective

Deliver the low-level package core for exact version/schema validation,
selected local transports, and bounded JSON-RPC request/response mechanics.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: one reusable, typed, fail-closed protocol core.
- Potential capability loss or regression: transport convenience could weaken
  schema checks, bounds, or explicit ownership.
- Protected-capability effect: exact protocol compatibility and injectable
  composition remain.
- Architecture and operating-model effect: establishes the lower layer of the
  independent `codex-app-server-client` distribution.
- Tradeoff and source evidence: Block 1 contract; the split keeps lifecycle and
  restart review out of the transport acceptance boundary.

### Inputs and dependencies

- Block 1.

### Required work

- Implement exact binary/version resolution, schema loading/generation and
  validation, bounded request IDs/correlation, message-size limits, and
  structured protocol/transport errors.
- Implement the selected local transports from Block 1, including owned stdio
  and the frozen Unix-socket contract, plus an injectable byte transport for
  deterministic tests.
- Provide low-level deterministic peer fixtures for request/response framing.

### Scope and non-goals

- In scope: compatibility, framing, transport, bounds, and error core.
- Not in scope: initialization lifecycle, typed task methods, event pump,
  callbacks, cancellation, restart policy, consumer adapters, or public network
  transport.

### Deliverables and recorded state

- Installable package core, schemas/manifests, transport implementations,
  typed errors, low-level fixtures, focused tests, and API documentation.

### Resource and economy contract

Use deterministic local fixtures; one official-binary compatibility probe is
permitted at the frozen candidate and no network/provider call is required.

### QA and independent review

Review schema fidelity, framing, bounds, correlation, transport cleanup,
injectability, error stability, and absence of consumer coupling.

### Acceptance

- The installed package accepts only the frozen compatible protocol, completes
  bounded request/response round trips over each selected local transport, and
  fails closed on incompatible or malformed input.

### Negative tests

- Reject stale schemas, oversized/malformed messages, non-integer or duplicate
  response IDs, unmatched responses, partial writes, broken cleanup, ambient
  process ownership, or downstream imports.

### Completion evidence

Pending.

### Stop

Stop before implementing initialization, events, callbacks, or restart behavior.

---

## Block 3 — Implement typed app-server lifecycle and fake-server conformance

Status: `not-started`

### Objective

Complete the typed client lifecycle, asynchronous protocol behavior, restart
safety, and deterministic end-to-end conformance without adding product policy.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: a complete maintained client usable through owned
  process or injected transport composition.
- Potential capability loss or regression: callback, cancellation, or restart
  races could corrupt current client state or create two process owners.
- Protected-capability effect: exact schemas, callbacks, cancellation, events,
  and generation-bound restart behavior remain explicit and testable.
- Architecture and operating-model effect: completes the independent typed
  app-server client above Block 2's core.
- Tradeoff and source evidence: Block 1 lifecycle contract and Block 2 transport
  boundary; policy hooks remain injectable rather than becoming product policy.

### Inputs and dependencies

- Block 2.

### Required work

- Implement initialization/feature negotiation, typed narrowed operations,
  notification/event handling, server-initiated callbacks, cancellation,
  disconnect, timeouts, and generation-bound restart-safe state.
- Expose explicit owned-process and injected-transport composition; keep retry
  and restart decisions behind bounded hooks.
- Provide a deterministic fake server covering interleaving, callbacks,
  malformed input, disconnects, timeouts, and stale generations.
- Provide no-content diagnostic logging defaults.

### Scope and non-goals

- In scope: typed generic client lifecycle and deterministic conformance.
- Not in scope: prompts, tasks as product records, missions, product retry
  policy, provider budgets, acceptance, consumer adapters, or application
  effects.

### Deliverables and recorded state

- Complete distribution, typed client API, fake server, conformance fixtures,
  docs/examples, tests, wheel, and API compatibility fixture.

### Resource and economy contract

Offline fake-server tests are normal; reuse Block 2 schema/transport proof and
run one bounded official-binary lifecycle smoke after candidate freeze.

### QA and independent review

Review concurrency, generation isolation, callback attribution, bounds,
cleanup, content logging, process ownership, public API minimality, and no
consumer semantics.

### Acceptance

- A wheel-installed client passes the frozen lifecycle matrix and supports both
  owned-process and injected-transport composition without duplicate ownership
  or stale-generation effects.

### Negative tests

- Reject unbounded queues, dropped or duplicate callback/event delivery,
  secret/content logging, stale-generation publication, cancellation races, two
  process owners, raw arbitrary methods, or downstream types.

### Completion evidence

Pending.

### Stop

Stop before implementing the other distributions or cross-package composition.

---

## Block 4 — Implement the embedded/service structural contract

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

- Block 0 admission and package baseline.

### Required work

- Define minimal start/status/event/cancel/outcome/error structural protocols.
- Provide conformance assertions, explicit single-process-owner composition,
  two neutral in-repository reference hosts, and deterministic failure fixtures.

### Scope and non-goals

- In scope: structural protocols and test helpers.
- Not in scope: a web framework, server, service runner, auth, scheduler,
  persistence, product lifecycle, canonical outcome, or downstream fixture.

### Deliverables and recorded state

- Independent distribution, protocols, conformance helpers, neutral reference
  hosts, failure fixtures, documentation, tests, and wheel.

### Resource and economy contract

Use pure deterministic tests and neutral in-memory reference hosts; no network,
provider, downstream checkout, or consumer suite.

### QA and independent review

Review minimality, structural neutrality, implementability, process ownership,
and absence of runtime or product authority.

### Acceptance

- Two structurally different neutral reference hosts pass the same conformance
  contract without sharing state, product types, or an implementation runtime.

### Negative tests

- Reject framework dependencies, canonical persistence, semantic outcome
  authority, product fields, session-only results, two process owners, or a
  fixture that requires a downstream package.

### Completion evidence

Pending.

### Stop

Stop before cross-package integration or any service implementation.

---

## Block 5 — Implement the non-authoritative runtime-manifest package

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

- Block 0 admission and package baseline.

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

### Negative tests

- Reject mutable roots, product IDs/content, authorization/acceptance fields,
  unknown schemas silently accepted, ambient discovery, filesystem scanning, or
  a manifest that changes runtime authority.

### Completion evidence

Pending.

### Stop

Stop before cross-package composition or downstream manifest adoption.

---

## Block 6 — Prove internal package isolation and neutral composition

Status: `not-started`

### Objective

Prove that all admitted distributions install independently and compose through
their public neutral contracts entirely inside this repository.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block validates already implemented package
  boundaries and introduces no new runtime or product semantics.

### Inputs and dependencies

- Blocks 3–5 and their frozen wheels, schemas, and neutral fixtures.

### Required work

- Build an install-isolated matrix, import/dependency-direction audit, fake
  app-server lifecycle scenarios, embedded/service equivalence scenarios,
  runtime-manifest compatibility scenarios, and one neutral combined
  composition.
- Prove the conformance kit is test-only and every exercised path is reachable
  through installed public APIs.

### Scope and non-goals

- In scope: internal distribution and composition conformance.
- Not in scope: consumer skeletons, downstream adapters, downstream test suites,
  whole-product behavior, deployment, or a new production integration API.

### Deliverables and recorded state

- Internal conformance kit, isolated-install matrix, neutral composition
  fixture, CI jobs, import audit, and failure diagnostics.

### Resource and economy contract

Build each wheel once per candidate, run affected package tests first, then the
parallel isolated/combined matrix; use no downstream content, checkout, command,
provider, or network.

### QA and independent review

Review failure discrimination, install isolation, import direction, fixture
neutrality, public-API reachability, and absence of test-only architecture.

### Acceptance

- Each distribution installs alone and together; the neutral composition passes
  through public APIs; incompatible roots and dependency violations fail
  clearly; and no validation step touches a downstream repository.

### Negative tests

- Reject undeclared dependency, circular import, mixed incompatible versions,
  hidden product fixture, repository path assumption, test-only private API, or
  any downstream invocation.

### Completion evidence

Pending.

### Stop

Stop before terminal qualification, publication, or downstream adoption.

---

## Block 7 — Qualify the frozen internal package set and authority boundary

Status: `not-started`

### Objective

Freeze one exact internal package set and prove build, API, compatibility,
dependency, documentation, and authority boundaries without release activity.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block qualifies the frozen package behavior and
  does not add a feature, downstream integration, or release effect.

### Inputs and dependencies

- Block 6 and one frozen repository candidate.

### Required work

- Build/install every wheel, verify checksums and package metadata, run focused
  checks followed by the internal conformance matrix once, validate API docs and
  examples, and audit source/import/dependency direction.
- Audit package source, tests, fixtures, examples, commands, and CI for
  downstream imports, paths, identifiers, runtime calls, or acceptance claims.
- Obtain distinct exact-revision technical and authority-boundary review.

### Scope and non-goals

- In scope: technical qualification and authority isolation of repository-owned
  artifacts.
- Not in scope: license selection, publication, GitHub Release, announcement,
  downstream adapter, consumer test, cutover, or deletion.

### Deliverables and recorded state

- Wheels/checksums, dependency inventory, API/compatibility matrix,
  documentation proof, internal conformance evidence, downstream-interaction
  audit, and exact-revision review.

### Resource and economy contract

Reuse accepted Block artifacts, run affected checks first, and execute the
complete frozen matrix once after likely-mutating review; rerun only invalidated
proof after corrections.

### QA and independent review

Distinct reviewers inspect exact source/artifacts, API proportionality,
dependency direction, protocol compatibility, fixture neutrality, and the
absence of product or release authority.

### Acceptance

- Every distribution builds and installs independently at one exact repository
  revision; internal conformance passes; documentation matches behavior; and
  the no-downstream-interaction and authority audits are clean.

### Negative tests

- Reject mixed roots, undeclared dependency, consumer import/path/identifier in
  a distribution artifact or runtime test, product authority, unbounded public
  API, invalid documentation example, or pre-correction proof cited as current.

### Completion evidence

Pending.

### Stop

Stop before adding a license, publishing, releasing, announcing, or performing
downstream adoption.

---

## Block 8 — Record no-license/unpublished posture and close the program

Status: `not-started`

### Objective

Record the truthful internal-completion and release posture without granting a
license, publishing packages, or implying downstream adoption.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block records the existing authority boundary and
  terminal evidence; it performs no package behavior or external effect.

### Inputs and dependencies

- Accepted Block 7 exact revision and repository license/release instructions.

### Required work

- Confirm built artifacts and package metadata make no unsupported license,
  publication, release, support, or downstream-adoption claim.
- Record the exact `no-license-selected/unpublished` posture, prohibited effects,
  and activation conditions for any separately authorized successor.
- Freeze the final internal package, conformance, documentation, authority, and
  Git-currentness evidence set.

### Scope and non-goals

- In scope: truthful terminal posture and internal program closure.
- Not in scope: adding `LICENSE`, choosing legal terms, publishing to an index,
  creating a GitHub Release, announcement, consumer handoff, downstream
  integration, or unrelated package admission.

### Deliverables and recorded state

- Final internal completion manifest, package/artifact roots, release-posture
  record, retained limitations, and successor-activation boundary.

### Resource and economy contract

Reuse Block 7 artifacts and hashes; perform documentation/metadata/currentness
checks only and do not rebuild or rerun the full matrix unless exact bytes
changed.

### QA and independent review

Review that technical completion is proven, release/legal claims remain
truthful, no external effect occurred, and the Stop is explicit.

### Acceptance

- The exact internal package set is accepted, the repository remains
  `no-license-selected/unpublished`, no release or downstream-adoption claim is
  made, and future external work is clearly outside this program.

### Negative tests

- Reject an added license/classifier, publication configuration or effect,
  GitHub Release, open-source/reuse claim, consumer acceptance statement,
  downstream pin/handoff, or package admission hidden in terminal cleanup.

### Completion evidence

Pending.

### Stop

Stop before any license grant, publication, release, announcement, downstream
adapter or cutover, consumer test, or unrelated utility admission.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Package admission and independent distribution | 0 | 2–6 | 7–8 |
| Official app-server protocol contract | 1 | 2–3, 6 | 7 |
| Compatibility, transports, and bounded JSON-RPC | 2 | 3, 6 | 7 |
| Typed lifecycle, callbacks, and restart safety | 3 | 6 | 7 |
| Embedded/service structural equivalence | 4 | 6 | 7 |
| Non-authoritative runtime manifests | 5 | 6 | 7 |
| Isolated installation and neutral composition | 6 | 7 | 7 |
| No downstream implementation interaction | 0 | 1–7 | 7–8 |
| No-license/unpublished release posture | 8 | — | 8 |

## 9. Final completion definition

The tracker is complete only when Blocks 0–8 are accepted at exact current
pushed revisions; every admitted distribution builds, installs, versions,
tests, and documents independently; the exact official protocol and internal
conformance matrices pass; exported APIs and artifacts contain no downstream
consumer dependency or authority; no downstream repository was operated or
modified as implementation work; and the repository truthfully records its
`no-license-selected/unpublished` posture without crossing Block 8's Stop.

Completion does not mean that any downstream application has adopted, tested,
accepted, released, or even referenced these packages.
