# FPL Decision Centre — Canonical Specification

This directory is the product and engineering source of truth for rebuilding the
FPL Decision Centre. It describes intended behaviour independently of the current
incremental implementation.

The current application, generated data, screenshots and conversation history are
evidence. They are not automatically authoritative because they can include stale,
superseded or partially implemented behaviour.

## Authority order

When artefacts disagree, use this order:

1. Accepted requirements and calculation rules in this directory.
2. Versioned data contracts.
3. Acceptance tests and golden datasets.
4. Page and component specifications.
5. Design tokens and semantic state rules.
6. Current application behaviour on `main`.
7. Screenshots and historical requirements documents.
8. Conversation history.

An unresolved conflict must be recorded in the decision register; it must not be
silently resolved by an implementing LLM.

## Artefact status

| Artefact | Status | Purpose |
|---|---|---|
| [Product vision](00-product-vision.md) | Baseline drafted | Product intent, users, principles and scope |
| [Feature inventory](01-feature-inventory.md) | Baseline drafted | Current, accepted, planned and retired capabilities |
| [Decision register](02-decision-register.md) | Baseline drafted | Accepted decisions, conflicts and open questions |
| [Domain glossary](03-domain-glossary.md) | Baseline drafted | Canonical FPL and application terminology |
| [User journeys](experience/user-journeys.md) | Baseline drafted | Deadline, live-gameweek and review workflows |
| [Page contracts](experience/page-contracts.md) | Baseline drafted | Exact content and behaviour of each view |
| [Component catalogue](experience/component-catalogue.md) | Baseline drafted | Reusable visual and interaction contracts |
| [Design system](design/design-system.md) | Baseline drafted | Colour, typography, spacing and state semantics |
| [Source register](data/source-register.md) | Baseline drafted | External and generated data provenance |
| [Contract index](data/contract-index.md) and [schemas](schemas/) | Baseline drafted | Versioned schemas and ownership of derived fields |
| [Live scoring rules](rules/live-scoring.md) | Baseline drafted | Points, autosubs, captaincy and manager totals |
| [Truth-state taxonomy](rules/truth-state-taxonomy.md) | Baseline drafted | Official, declared, calculated, projected and modelled values |
| [Gameweek lifecycle](rules/gameweek-lifecycle.md) | Baseline drafted | Pre-deadline, locked, live, completed and between-GW behaviour |
| [Architecture specification](architecture/target-architecture.md) | Baseline drafted | Target rebuild architecture and boundaries |
| [Acceptance catalogue](testing/acceptance-catalogue.md) | Baseline drafted | Requirement IDs and Given/When/Then tests |
| [Golden scenarios](testing/golden-scenarios.md) | Baseline drafted | Deterministic scenarios for calculation and UI verification |
| [LLM delivery manifest](delivery/llm-build-manifest.md) | Baseline drafted | Ordered, bounded implementation slices |
| [Operations runbook](operations/runbook.md) | Baseline drafted | Setup, schedules, deployment and recovery |
| [Traceability matrix](delivery/traceability-matrix.md) | Baseline drafted | Requirement to data, UI, code and test mapping |

## Evidence baseline

The first discovery pass used:

- repository: `tlaw77/fpl`
- branch: `main`
- baseline commit: `566045e4`
- last reconciled `main`: `f7183d2b`
- discovery date: 2026-09-24
- primary UI entry point: `docs/index.html`
- historical recovery source: `REQUIREMENTS_RECONCILIATION.md`
- generated snapshot source: `data/latest.json`
- live snapshot source: `data/live_gameweek.json`
- pipeline source: `.github/workflows/*.yml`

## Status vocabulary

- **Accepted** — intended product behaviour and safe to implement.
- **Implemented** — present in the baseline code; not necessarily accepted forever.
- **Accepted gap** — explicitly wanted but not yet proven complete in the baseline.
- **Provisional** — direction is useful but details need validation.
- **Open** — a product decision is required before implementation.
- **Retired** — intentionally removed and must not be recreated.
- **Historical** — retained as evidence only.

## Rules for LLM-driven delivery

1. Implement one delivery slice at a time.
2. Read every artefact listed in that slice before editing code.
3. Do not invent fields when a contract is missing; record the gap.
4. Keep raw, official, calculated and projected values separately named.
5. Add or update acceptance tests before declaring a slice complete.
6. Validate desktop and iPhone Safari behaviour where the slice affects UI.
7. Never infer that a visual colour is decorative when it represents state.
8. Update the traceability matrix and decision register with every material change.
