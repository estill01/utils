# Neutral installed-wheel composition

The repository owns one development-only composition proof after all three
distributions qualify independently. `scripts/check_composition.py` builds the
accepted package sources separately, requires the exact Block 12 wheel byte and
content roots frozen in `tools/composition_matrix.json`, installs the three
local wheels together without dependency resolution, and runs
`tests/neutral_composition.py` from outside every package source tree.

The fixture has one bounded purpose:

- initialize the installed app-server client through its public injected-byte
  transport and run one typed list operation against an in-memory JSON-lines
  peer;
- run the installed embedded and service reference fixtures through the public
  structural conformance API and prove their combined declared process-owner
  count is exactly one; and
- construct, serialize, parse, and compare an immutable runtime manifest that
  names the exact installed package content roots plus the frozen app-server
  schema and selected-surface roots.

Separate manifest comparisons alter one package root and one protocol root.
Each must return one exact typed reason, including its subject and expected and
observed `sha256:` roots. The runner rejects private package modules or
attributes, extra result fields, altered artifact roots, mixed versions,
unexpected lifecycle results, and package/protocol input drift.

This is a test fixture and CI job, not a fourth distribution or production
abstraction. No package imports a sibling distribution. The proof performs no
consumer discovery, checkout, process launch, adapter work, persistence,
network access, publication, release, or authority decision.
