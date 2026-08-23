# Architecture and ownership contract

## Distribution graph

```text
codex-app-server-client      embedded-service-contract      runtime-manifest
            |                          |                           |
            +--------------------------+---------------------------+
                                       |
                    development-only neutral composition tests

external products -> independently installed distributions
distributions -X-> external products
```

The three distributions have no required runtime dependency on one another.
Composition is exercised only by repository-owned development tests after each
distribution independently qualifies.

## Public-boundary owners

| Distribution | Owns | Must not own |
|---|---|---|
| `codex-app-server-client` | exact upstream version/schema compatibility; bounded JSON-RPC state; local byte transports; typed app-server sessions; policy-neutral callbacks/events; generation-safe restart | raw public RPC; product prompts/missions/records; approval policy; provider policy; consumer adapters |
| `embedded-service-contract` | structural start/status/event/cancel/outcome/error protocols and conformance assertions | service runner; web framework; persistence; scheduling; canonical product outcome; host state |
| `runtime-manifest` | immutable caller-supplied descriptive versions, roots, features, dependencies, and compatibility comparison | discovery; ambient inventory; authorization; acceptance; product identity; registry or release authority |

## Dependency and process rules

1. Runtime dependencies are declared independently by each distribution.
2. Repository-wide tooling is development-only and cannot be imported by a
   distribution at runtime.
3. No `utils` Python namespace exists.
4. App-server transports require one explicit process or connection owner.
5. An injected transport never creates or discovers another process owner.
6. No package imports, shells into, launches, pins, or tests a downstream
   consumer.
7. Official upstream app-server schemas and a bounded official-binary smoke are
   compatibility inputs, not consumer interactions.
8. Shared records are descriptive and non-authoritative.

## External-consumer boundary

Consumer-specific identifiers are confined to governing repository
instructions/documentation and the bounded `docs/admission.md` record.
Production source, schemas, fixtures, examples, tests, build metadata,
artifacts, and package records remain consumer-neutral. A package record can
state an exact source revision, version, artifact root, public API root,
compatibility inputs, currentness, and qualification posture. It cannot select
a consumer revision, claim adoption, or grant reuse rights.

## Change authority

- This repository owns only the three admitted package contracts and their
  internal proof.
- Each external product owns its adapters, pins, persistence, policy,
  deployment, acceptance, and release decisions.
- Adding a distribution requires a new admission decision.
- Adding a license, publishing, creating a release, or claiming reuse rights
  requires separate explicit authority.
