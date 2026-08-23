# Shared Domain-Neutral Utilities Implementation Tracker

- Tracker status: `planning`
- Tracker sequence: Blocks 0–9
- Repository: `https://github.com/estill01/utils`
- Governing objective: provide narrow, independently versioned enabling
  packages that remove proven duplication across Software Factory, libRSI, and
  Patent Studio without centralizing product authority or policy.

## 1. Purpose and intended outcome

Create an organizational monorepo of individually named packages, beginning
with a typed Codex app-server client and small embedded/service and runtime
manifest contracts. Products import these packages; the packages import none of
the products.

Completion means:

- Software Factory's existing generic app-server process/RPC mechanics are
  extracted into a typed independently tested package and all three products
  can consume the same protocol/client contract;
- embedded and standalone-service hosts can prove lifecycle-equivalent use
  through a small non-authoritative conformance package;
- products can bind exact component/protocol/schema/capability versions through
  a non-authoritative runtime-manifest package;
- each product retains its own adapter, authority, policies, data, process
  ownership, QA, and acceptance;
- the monorepo has package-isolated CI, compatibility policy, consumer
  conformance, documentation, and a truthful license/release posture; and
- no top-level grab-bag `utils` API or universal ledger/model emerges.

### Mission frame

- Primary outcome: reduce duplicated enabling code while making the three
  products easier to run embedded or as services.
- Observable completion: Blocks 0–9 are accepted at current pushed revisions;
  all admitted packages build/install independently; exact consumer
  conformance passes; and the authority/import audit is clean.
- Ordinary effect classes needed: package source/tests/docs, extracted client
  code, consumer adapters and pins in their repositories, CI, builds, commits,
  pushes, and optionally license/release files after explicit authority.
- Hard direct authority or safety boundaries: utilities cannot own product
  semantics, missions, QA/supervision/acceptance, patent content, persistence,
  credentials, tenancy, billing, releases, or provider/product policy; no
  package publication or license grant without separate authority.
- Material goal alteration or reversal: turning this into a common product
  platform, universal model/ledger, product-specific adapter repository,
  mandatory shared service, or a single undifferentiated utility package.

### Target-product capability frame

- Applicability: `consequential`.
- Applicability rationale: this tracker introduces public package boundaries
  and changes dependency/version ownership across three products.
- Direct product sources: Software Factory
  `docs/software-factory-v2-implementation-plan.md`, libRSI
  `docs/tracker.md`, Patent Studio's planned product-solidification tracker,
  the existing Software Factory dashboard app-server client, and the direct
  user requirement to add shared enablers as justified.
- Product thesis and intended effect: boring cross-cutting mechanics should be
  implemented once behind narrow contracts so product teams focus on their
  interesting domain behavior.
- Protected capabilities: independent product operation, one process owner per
  composition, provider replaceability, exact protocol/version compatibility,
  low-level embedded use, standalone service use, and product-owned authority.
- Architecture strategy: monorepo containing independently distributed Python
  packages with one-way dependencies, deterministic fakes/conformance, and no
  runtime service of its own.
- Requested capability: shared Codex app-server client, embedded/service
  conformance contracts, runtime manifests, and an evidence-gated admission
  path for later enablers.
- Proportionality: admit only proven two-consumer utilities; keep adapters in
  products; do not generalize product records or prebuild speculative helpers.
- Tradeoffs: shared versioning reduces duplication but introduces release
  coordination; separate distributions add packaging overhead but prevent a
  grab-bag dependency.
- Uncertainty: the public license and any package-index publication are
  undecided and remain terminal gates.

## 2. Target architecture and authority boundaries

```text
packages/
  codex-app-server-client/     typed protocol/process/transport client
  embedded-service-contract/  small lifecycle equivalence protocols/fixtures
  runtime-manifest/            non-authoritative exact version/capability data

Software Factory ─┐
libRSI ───────────┼── imports packages; keeps product adapters and authority
Patent Studio ────┘

utils imports none of the products
```

The app-server client owns binary/version resolution, schema compatibility,
stdio/Unix transport, initialization, bounded request IDs, events,
server-initiated approval callbacks, cancellation/disconnect, restart-safe
client state, and deterministic fake-server conformance. It does not own
prompts, tasks, missions, patent context, QA, acceptance, provider budgets, or
application effects.

## 3. Existing owners to reuse

| Concern | Existing owner | Treatment |
|---|---|---|
| Generic app-server mechanics | Software Factory `dashboard/server/src/software_factory_dashboard/app_server.py` | extract only domain-neutral process/RPC/schema/event behavior |
| Factory projections and provider policy | Software Factory dashboard/runtime adapters | remain in Factory |
| libRSI capability and semantic contracts | libRSI `src/librsi/` | remain in libRSI; consume shared mechanics only |
| Patent Studio agent, privacy, budget, and effect contracts | Patent Studio `src/patent_studio/agent/` and controlled-task owners | remain in Studio |
| Codex app-server protocol | exact official Codex source/schema at implementation time | pin and test compatibility; do not fork protocol semantics |
| Package builds/quality | standard Python packaging and repository CI | implement per distribution |

## 4. Prior-work and source-adaptation map

| Source or predecessor | Exact revision/hash | Disposition | Owning Block | Remaining work |
|---|---|---|---:|---|
| Software Factory app-server client | resolve exact accepted extraction baseline in Block 1 | adapt/extract | 1–2, 6 | separate generic client from Factory projections |
| Software Factory v2 tracker/plan | exact accepted consumer revision at cutover | consume | 6 | pin package and remove duplicate code |
| libRSI managed-runtime tracker amendment | exact accepted consumer revision at cutover | consume | 7 | implement optional Codex adapter using shared client |
| Patent Studio solidification tracker | exact accepted consumer revision at cutover | consume | 8 | implement local gateway using shared client |
| Codex app-server upstream | exact reviewed commit and generated schema root at Block 1 | reference/pin | 1–2 | compatibility matrix and update policy |

## 5. Scope, non-goals, and admission rule

### In scope

- The three initial distributions, package-isolated tests/builds, protocol
  compatibility, deterministic fakes, consumer conformance, documentation, and
  exact consumer pins/cutovers.

### Out of scope

- A shared daemon/service, common product models, mission runtime, scheduler,
  QA/supervision, libRSI records, patent schemas/content, product database,
  tenancy/billing, credential manager, logging platform, or universal event
  ledger.

### Admission rule

A new package or exported primitive requires all of:

1. domain-neutral behavior;
2. two concrete consumers, or one current consumer plus an imminent active
   second implementation;
3. no product authority, policy, or product database schema;
4. one-way imports from products to the utility;
5. independent API, tests, versioning, and a named compatibility policy; and
6. net reduction in implementation and coordination complexity.

If a candidate fails one condition, keep it in its product. “Could be reused”
is not admission evidence.

## 6. Block execution contract

1. Execute Blocks 0–9 in dependency order; tracker authoring starts no Block.
2. Inspect the exact upstream and consumer revisions before each Block; preserve
   concurrent product work and use isolated branches.
3. Mark a Block `in-progress` at its first implementation-producing effect.
4. Before each first candidate, exercise the three most discriminating negative
   cases. Freeze one candidate, run focused then mapped proof, and obtain one
   distinct exact-revision audit.
5. A consumer cutover occurs only at that consumer's safe single-writer
   boundary and through its own tracker/owner. This tracker does not infer
   consumer acceptance.
6. On rejection, correct only supported findings and rerun affected proof; a
   second material rejection triggers bounded causal design review.
7. Push accepted coherent checkpoints without force. A package build, consumer
   pin, commit, or push is nonterminal.
8. Do not publish to a package index, create a GitHub Release, add a license, or
   claim open-source rights without the terminal gate.

### Continuation-first license gate

- Decision needed: the exact license grant or explicit no-license posture.
- Why non-delegable: a license grants persistent legal reuse rights and cannot
  be inferred from a public repository.
- Earliest complete packet: Block 9 after APIs, dependencies, notices, and
  release artifacts are frozen; compare at least MIT and Apache-2.0, including
  patent-grant implications, without giving legal advice.
- Blocked subset: adding `LICENSE`, license classifiers/notices, package-index
  publication, GitHub Release, and open-source reuse claims.
- Safe frontier: Blocks 0–8 and all license-independent Block 9 work.
- Revisit trigger: direct user selection or explicit no-license choice, plus
  separate release authority for any publication.

### Supervised execution and monitoring

Each implementation/consumer target uses its own isolated
`supervise-tracker-runs` group bound to the exact repository, tracker, range,
and active Block. Monitors may inspect only that target's changed state and
cannot implement, combine product contexts, or treat a package's acceptance as
consumer acceptance. Unchanged monitoring remains silent.

### Completion-evidence template

```markdown
### Completion evidence

- Repository commit: `<sha>`
- Upstream/consumer revisions: `<exact versions/hashes>`
- Inputs: `<paths/schemas/hashes>`
- Outputs: `<packages/artifacts/hashes>`
- Focused validation: `<commands/results>`
- Mapped/consumer validation: `<commands/results>`
- Candidate freeze: `<commit/content root/currentness>`
- Remediation closure: `<finding/change/proof or not-applicable>`
- Independent review: `<distinct reviewer/root>`
- Retained open work: `<items or none>`
- License/release posture: `<decision state and prohibited effects>`
- Post-block audit: `<accepted/reopened/blocked>`
- Git durability: `<commit/push posture>`
```

## 7. Status and required order

| Block | Scope | Depends on | Status |
|---:|---|---:|---|
| 0 | Repository, package, admission, and compatibility baseline | — | `not-started` |
| 1 | Codex app-server source/extraction contract | 0 | `not-started` |
| 2 | Typed Codex app-server client package | 1 | `not-started` |
| 3 | Embedded/service conformance package | 0, 2 | `not-started` |
| 4 | Runtime-manifest package | 0, 2 | `not-started` |
| 5 | Cross-package and consumer conformance harness | 2–4 | `not-started` |
| 6 | Software Factory consumer cutover | 5 | `not-started` |
| 7 | libRSI consumer cutover | 5, 6 | `not-started` |
| 8 | Patent Studio consumer cutover | 5–7 | `not-started` |
| 9 | Terminal package, authority, license, and release audit | 6–8 | `not-started` |

Required order:

`0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9`

## Block 0 — Establish repository, package, admission, and compatibility baseline

Status: `not-started`

### Objective

Create the independently distributable monorepo contract and freeze exact
consumer/upstream baselines before moving code.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: narrow package ownership and admission discipline.
- Potential capability loss or regression: a generic-sounding repository could
  become a dumping ground.
- Protected-capability effect: product ownership and independent operation
  remain.
- Architecture and operating-model effect: separate distributions in one
  organizational repository.
- Tradeoff and source evidence: direct user requirement and the three concrete
  consumer needs.

### Inputs and dependencies

- Exact Software Factory, libRSI, Patent Studio, and Codex app-server revisions.

### Required work

- Define package layout/namespaces, dependency rules, version policy, supported
  Python baseline, compatibility policy, CI matrix, and admission record.
- Classify every initial candidate against the six admission conditions.

### Scope and non-goals

- In scope: repository/package contract and frozen baselines.
- Not in scope: utility implementation or consumer changes.
- No top-level `utils` import.

### Deliverables and recorded state

- Architecture/admission docs, package registry, baseline roots, CI skeleton,
  and changed-test map.

### Resource and economy contract

Read/hash each source once; no broad consumer suite.

### QA and independent review

Review package necessity, direction, authority leakage, naming, and release
coupling.

### Acceptance

- Every initial package satisfies admission and has explicit consumers,
  boundaries, and compatibility owner.

### Negative tests

- Reject one-consumer speculation, product imports, common models, shared
  authority, or a package that cannot version/test independently.

### Completion evidence

Pending.

### Stop

Stop before extracting app-server code.

---

## Block 1 — Freeze Codex app-server source and extraction contract

Status: `not-started`

### Objective

Separate domain-neutral app-server mechanics from Software Factory projections
and bind an exact upstream protocol/schema compatibility target.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: safe extraction without redesigning protocol
  semantics.
- Potential capability loss or regression: missed Factory coupling or stale
  upstream schemas could make the client incomplete.
- Protected-capability effect: current Factory behavior and future consumer
  needs remain testable.
- Architecture and operating-model effect: defines package versus local
  adapter lines.
- Tradeoff and source evidence: existing Factory client and official app-server
  source/schema.

### Inputs and dependencies

- Block 0.

### Required work

- Inventory process, transport, JSON-RPC, initialization, request/event,
  approval, cancellation, retry/restart, schema, and Factory-specific code.
- Freeze exact upstream commit/schema roots and compatibility/update policy.

### Scope and non-goals

- In scope: source/protocol/extraction contract.
- Not in scope: implementation move or new protocol.
- Do not make experimental WebSocket transport required.

### Deliverables and recorded state

- Line/function classification, upstream manifest, API contract, and extraction
  proof plan.

### Resource and economy contract

Static inspection and existing focused tests only.

### QA and independent review

Review completeness, upstream fidelity, projection separation, and unsupported
feature invention.

### Acceptance

- Every existing client behavior is classified as package, Factory adapter, or
  retire with a consumer/compatibility reason.

### Negative tests

- Reject Factory task/project schema in package API, unpinned upstream,
  experimental transport as baseline, or missing server-initiated approval.

### Completion evidence

Pending.

### Stop

Stop before moving or implementing client code.

---

## Block 2 — Implement typed Codex app-server client package

Status: `not-started`

### Objective

Deliver a typed Python client that owns generic process/transport/protocol
mechanics and deterministic conformance, not product behavior.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: one maintained client for all consumers.
- Potential capability loss or regression: abstraction could hide protocol
  features or create ambient process ownership.
- Protected-capability effect: exact schemas, explicit process owner,
  cancellation, approvals, events, and restart remain.
- Architecture and operating-model effect: independent
  `codex-app-server-client` distribution.
- Tradeoff and source evidence: Block 1 contract.

### Inputs and dependencies

- Block 1.

### Required work

- Implement binary/version resolution, schema loading/generation,
  stdio/Unix transport, initialization, bounded RPC, event pump, approvals,
  cancellation/disconnect, retry/restart policy hooks, and structured errors.
- Provide a deterministic fake server and no-content logging defaults.

### Scope and non-goals

- In scope: generic typed client/process support.
- Not in scope: prompts, missions, tasks, product retry policy, acceptance,
  provider budgets, or public network proxy.
- Process ownership is explicit and injectable.

### Deliverables and recorded state

- Package source, typings, schemas/manifests, fake server, docs/examples, tests,
  wheel, and API compatibility fixture.

### Resource and economy contract

Offline fake tests are normal; one bounded upstream-binary smoke check at the
frozen candidate.

### QA and independent review

Review protocol fidelity, bounds, concurrency, lifecycle, error handling,
security/content logging, and no product leakage.

### Acceptance

- Wheel-installed client passes the exact protocol matrix and supports both
  owned-process and injected-transport composition.

### Negative tests

- Reject unbounded IDs/queues, dropped approval/event, secret/content logs,
  two owners, Factory/libRSI/Patent Studio types, stale schema acceptance, or
  provider completion semantics.

### Completion evidence

Pending.

### Stop

Stop before embedded/service or runtime-manifest packages.

---

## Block 3 — Implement embedded/service conformance package

Status: `not-started`

### Objective

Provide the smallest protocols and fixtures needed to prove that embedded and
service hosts expose equivalent lifecycle semantics.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: consumers avoid independently inventing mode
  equivalence tests.
- Potential capability loss or regression: shared contract could become a
  generic service framework or lifecycle authority.
- Protected-capability effect: each product retains its engine and state.
- Architecture and operating-model effect: protocol/test-only
  `embedded-service-contract` distribution.
- Tradeoff and source evidence: three products' first-class embedded/service
  requirements.

### Inputs and dependencies

- Blocks 0 and 2.

### Required work

- Define start/status/event/cancel/outcome/error equivalence protocols,
  conformance fixtures, and explicit process-owner composition.

### Scope and non-goals

- In scope: small structural protocols and tests.
- Not in scope: web framework, service runner, auth, scheduler, persistence, or
  product lifecycle semantics.
- Consumer-specific operations stay local.

### Deliverables and recorded state

- Package, fixtures, fake host, docs, and wheel.

### Resource and economy contract

Pure deterministic tests; no network/provider.

### QA and independent review

Review minimality, semantic neutrality, no authority, and consumer
implementability.

### Acceptance

- Two distinct toy engines pass the same conformance without sharing state or
  product types.

### Negative tests

- Reject framework dependency, canonical persistence, product-specific fields,
  host-selected acceptance, or session-only outcome.

### Completion evidence

Pending.

### Stop

Stop before runtime-manifest implementation.

---

## Block 4 — Implement runtime-manifest package

Status: `not-started`

### Objective

Represent exact component, protocol, schema, capability, and dependency
versions without becoming product authority.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: reproducible compatibility and currentness binding
  across compositions.
- Potential capability loss or regression: manifest could become a universal
  registry or falsely authorize capabilities.
- Protected-capability effect: products remain the source of availability,
  authority, and acceptance.
- Architecture and operating-model effect: independent `runtime-manifest`
  distribution with deterministic canonical projection.
- Tradeoff and source evidence: cross-project exact pin/compatibility needs.

### Inputs and dependencies

- Blocks 0 and 2.

### Required work

- Define immutable component/version/content-root, protocol/schema capability,
  dependency, compatibility, and unavailable-reason projections.
- Separate declared, installed, available, authorized, and accepted states.

### Scope and non-goals

- In scope: non-authoritative runtime metadata.
- Not in scope: product registry, discovery service, authority grant,
  persistence platform, or universal identity.
- A manifest cannot make a capability available.

### Deliverables and recorded state

- Package, canonical serialization, compatibility helpers, schemas, docs,
  fixtures, and wheel.

### Resource and economy contract

Pure deterministic tests.

### QA and independent review

Review state distinctions, extensibility, no authority, and no product schema.

### Acceptance

- All three consumer fixture manifests bind exact versions/roots while retaining
  product-owned availability and authority.

### Negative tests

- Reject manifest as authorization/acceptance, mutable root, product IDs/
  content, unknown schema silently accepted, or ambient dependency discovery.

### Completion evidence

Pending.

### Stop

Stop before integrated consumer conformance.

---

## Block 5 — Build cross-package and consumer conformance harness

Status: `not-started`

### Objective

Prove packages compose independently and define the exact consumer cutover
contract without implementing product adapters here.

### Target-product capability delta

- Posture: `routine`.
- Routine or not-applicable justification: this Block tests accepted package
  boundaries and produces no new product semantics.

### Inputs and dependencies

- Blocks 2–4 and frozen consumer adapter contracts.

### Required work

- Build install-isolated matrix, dependency/import audit, fake app-server
  scenarios, embedded/service equivalence, runtime-manifest compatibility, and
  consumer adapter skeleton conformance.

### Scope and non-goals

- In scope: utility and boundary conformance.
- Not in scope: consumer implementation or whole product suites.
- Test fixtures cannot become alternate production APIs.

### Deliverables and recorded state

- Consumer conformance kit, matrix, CI jobs, and failure diagnostics.

### Resource and economy contract

Run package tests in parallel; use no product content/provider/network.

### QA and independent review

Review failure discrimination, install isolation, import direction, and test-
only architecture.

### Acceptance

- Each package installs alone and together; consumer skeletons fail clearly on
  incompatible roots or boundary violations.

### Negative tests

- Reject undeclared dependency, circular import, mixed incompatible versions,
  hidden product fixture, or fake path unavailable to real consumers.

### Completion evidence

Pending.

### Stop

Stop before consumer repository changes.

---

## Block 6 — Cut over Software Factory consumer

Status: `not-started`

### Objective

Replace duplicate generic app-server client mechanics with the shared package
while preserving Factory provider, task, QA, supervision, and delivery behavior.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: first real consumer and deletion of duplicate code.
- Potential capability loss or regression: extraction could alter dashboard or
  provider lifecycle.
- Protected-capability effect: Factory remains the operational/process owner.
- Architecture and operating-model effect: Factory adapter maps shared client
  events to Factory records.
- Tradeoff and source evidence: Software Factory v2 tracker Block 4.

### Inputs and dependencies

- Block 5 and the exact eligible Factory consumer revision.

### Required work

- Pin package commit/version, move Factory projections/retry/policy to local
  adapter, replace generic code, and delete duplicate implementation after
  parity.

### Scope and non-goals

- In scope: Factory consumer cutover at its safe boundary.
- Not in scope: Factory mission/QA changes or Patent Studio/libRSI code.
- This repository does not edit Factory outside its owner handoff.

### Deliverables and recorded state

- Utility release candidate, Factory adapter commit, parity matrix, deletion
  proof, and exact pin.

### Resource and economy contract

Run utility and affected Factory focused/mapped tests; no broad replay.

### QA and independent review

Distinct cross-repository review checks behavior, ownership, currentness, and
deletion safety.

### Acceptance

- Factory uses the shared client and retains identical supported behavior with
  no duplicate generic owner.

### Negative tests

- Reject Factory projection in shared package, missing legacy behavior, changed
  retry/approval authority, mutable pin, or old client still active.

### Completion evidence

Pending.

### Stop

Stop before libRSI consumer cutover.

---

## Block 7 — Cut over libRSI consumer

Status: `not-started`

### Objective

Use the shared packages for libRSI's optional Codex adapter and embedded/
managed-service conformance without leaking semantic authority.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: second client consumer and managed-mode reuse.
- Potential capability loss or regression: provider/runtime metadata could
  enter canonical evidence or outcomes.
- Protected-capability effect: libRSI remains provider-free by default and
  owns semantic records/workflows.
- Architecture and operating-model effect: optional libRSI adapter imports
  shared packages.
- Tradeoff and source evidence: libRSI tracker Blocks 18, 21–22, and 24.

### Inputs and dependencies

- Blocks 5–6 and exact eligible libRSI revision.

### Required work

- Pin packages; implement adapter/process-owner injection; apply embedded/
  service conformance and runtime manifests; prove external-agent equivalence.

### Scope and non-goals

- In scope: libRSI optional consumer adapter.
- Not in scope: libRSI semantic changes or Software Factory scheduling.
- Shared packages cannot contain libRSI records.

### Deliverables and recorded state

- libRSI adapter commit, optional-extra build, conformance/equivalence proof,
  and exact pins.

### Resource and economy contract

Use fake providers and affected libRSI dogfoods; no hosted calls.

### QA and independent review

Review provider-free base import, semantic roots, process ownership, optional
dependency isolation, and reverse imports.

### Acceptance

- libRSI embedded and managed fake scenarios use shared packages with unchanged
  canonical outcomes.

### Negative tests

- Reject provider object in canonical record, mandatory extra, two process
  owners, managed/external root drift, or libRSI type in shared package.

### Completion evidence

Pending.

### Stop

Stop before Patent Studio consumer cutover.

---

## Block 8 — Cut over Patent Studio consumer

Status: `not-started`

### Objective

Use the shared packages for Patent Studio's local AgentGateway and exact
runtime compatibility while retaining all patent-domain owners.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: third consumer and removal of future duplicate
  app-server/service utilities.
- Potential capability loss or regression: shared transport could bypass Studio
  privacy, budget, project routing, or effect controls.
- Protected-capability effect: Studio owns context, workflows, authority
  revisions, project writes, and substantive review.
- Architecture and operating-model effect: local gateway imports shared client;
  Factory-managed gateway injects provider.
- Tradeoff and source evidence: Patent Studio solidification tracker Blocks
  3–4 and 10.

### Inputs and dependencies

- Blocks 5–7 and exact eligible Patent Studio revision.

### Required work

- Pin packages; implement local gateway and injected managed composition;
  apply runtime manifests and embedded/service conformance; delete duplicate
  generic mechanics if any.

### Scope and non-goals

- In scope: Patent Studio consumer adapter at its safe post-OMNI boundary.
- Not in scope: patent content, OMNI migration, or Factory/libRSI authority.
- Shared packages cannot receive patent context in logs/manifests.

### Deliverables and recorded state

- Studio adapter commit, conformance/currentness/privacy proof, exact pins, and
  duplicate-removal evidence.

### Resource and economy contract

Use neutral fixture, fake server, and affected tests; no OMNI/provider spend.

### QA and independent review

Review project isolation, privacy/budget, effect authority, process owner,
local/managed equivalence, and content-free shared metadata.

### Acceptance

- Both gateway modes use shared packages and reach the same Studio-authoritative
  neutral result without patent leakage.

### Negative tests

- Reject project/patent content in utilities, app-server completion as patent
  acceptance, two process owners, wrong project, weakened privacy/budget, or
  utility manifest as capability authority.

### Completion evidence

Pending.

### Stop

Stop before terminal package/license/release audit.

---

## Block 9 — Audit packages, authority, license, and release posture

Status: `not-started`

### Objective

Freeze exact packages and consumer pins, prove the authority boundary, and
prepare a truthful release decision without publishing automatically.

### Target-product capability delta

- Posture: `consequential`.
- Intended capability gain: reproducible independently consumable packages.
- Potential capability loss or regression: synchronized green tests could hide
  product coupling, mixed versions, or missing legal grant.
- Protected-capability effect: each product remains independently operable and
  authoritative.
- Architecture and operating-model effect: freezes package APIs, compatibility,
  notices, and consumer manifests.
- Tradeoff and source evidence: mission completion definition and license gate.

### Inputs and dependencies

- Blocks 6–8 and one frozen cross-repository revision set.

### Required work

- Build/install every wheel, verify exact consumer pins, run conformance/import/
  dependency/security scans, inspect artifacts/notices, prepare license packet,
  and obtain distinct exact-revision audits.

### Scope and non-goals

- In scope: qualification and license/release decision packet.
- Not in scope: package-index publication, GitHub Release, announcement, or
  automatic license selection.
- Public visibility is not an open-source grant.

### Deliverables and recorded state

- Wheels/checksums/SBOM or equivalent dependency manifest, compatibility
  matrix, consumer pin evidence, authority audit, license packet, and release
  runbook.

### Resource and economy contract

Run affected checks first and the frozen cross-package/consumer matrix once.
Reuse accepted Block evidence.

### QA and independent review

Distinct reviewers inspect source/artifacts, dependency direction, protocol
compatibility, consumer behavior, authority boundaries, and license posture.

### Acceptance

- All license-independent qualification passes at one exact revision set; final
  tracker completion additionally requires the explicit license/no-license
  decision and any separately authorized release effects.

### Negative tests

- Reject mixed package roots, mutable consumer pin, product import, patent/
  mission/semantic authority in utilities, unlicensed open-source claim,
  package publication without authority, or one consumer passing through a
  local duplicate.

### Completion evidence

Pending.

### Stop

Stop before package-index publication, GitHub Release, license grant without
direct selection, announcement, or unrelated utility admission.

## 8. Verification matrix

| Capability/invariant | Primary Block | Integration Blocks | Terminal proof |
|---|---:|---|---:|
| Admission and package isolation | 0 | 1–5 | 9 |
| App-server protocol/extraction | 1 | 2, 5–8 | 9 |
| Typed app-server client | 2 | 3–8 | 9 |
| Embedded/service equivalence | 3 | 5, 7–8 | 9 |
| Non-authoritative runtime manifests | 4 | 5, 7–8 | 9 |
| Consumer conformance | 5 | 6–8 | 9 |
| Software Factory cutover | 6 | 7–8 | 9 |
| libRSI cutover | 7 | 8 | 9 |
| Patent Studio cutover | 8 | 9 | 9 |

## 9. Final completion definition

The tracker is complete only when every admitted package and consumer cutover
is accepted at exact current pushed revisions, package/consumer conformance and
authority audits pass, no duplicate generic app-server owner remains, all three
products retain independent operation and authority, and the explicit license/
release posture is resolved without crossing Block 9's Stop.
