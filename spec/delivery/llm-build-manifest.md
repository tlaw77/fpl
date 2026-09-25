# LLM Build Manifest

## How to use this manifest

Give the implementing LLM one slice at a time with the repository. Do not ask it to
“rebuild the whole app” in one pass. A slice is merged only after its acceptance
gate passes.

For every slice, the LLM must:

1. read all listed specifications;
2. inspect relevant legacy evidence without copying its architecture;
3. add tests before or with implementation;
4. run the required validation;
5. update traceability;
6. stop if an open decision materially changes the result.

## Slice 01 — Rebuild scaffold and quality gates

**Read first:** product vision, target architecture, ADR-001, design system,
acceptance catalogue.

**Implement:** Vite/TypeScript app scaffold, test runner, lint/typecheck/build,
responsive shell placeholder and CI quality job.

**Do not change:** legacy production deployment or data pipeline.

**Must pass:** shell builds, 390px no-overflow smoke test, reduced-motion baseline.

## Slice 02 — Contract library and legacy adapters

**Read first:** truth taxonomy, contract index, all JSON Schemas, source register.

**Implement:** generated/static TypeScript types, runtime schema validation,
applicability/freshness results and adapters for current `latest.json` and
`live_gameweek.json`.

**Do not change:** scoring values or producer output.

**Must pass:** wrong-GW rejection, invalid-contract retention, schema fixtures;
ACC-SHELL-002 and ACC-OPS-001.

## Slice 03 — Lifecycle and shell

**Read first:** lifecycle, page contracts, component catalogue, design system.

**Implement:** canonical lifecycle selector, header, phase/freshness, navigation,
tab persistence and lazy view boundaries.

**Do not change:** recommendation or live-scoring logic.

**Must pass:** ACC-SHELL-001–004 and GOLD-PHASE scenarios.

## Slice 04 — Effective squad and action ledger

**Read first:** glossary, truth taxonomy, action/effective-squad schemas, transfer
page contract, DEC-003/005/013.

**Implement:** append-only action ledger domain, working plan, explicit declared
execution, correction/supersession, official reconciliation and effective-squad
selector.

**Do not change:** recommendation ranking model.

**Must pass:** ACC-TRN-001–006 and GOLD-TX scenarios.

## Slice 05 — Deterministic live-scoring engine

**Read first:** live scoring, lifecycle, live schema, golden scenarios.

**Implement:** fixture/player state, confirmed DNP, autosubs, captain fallback,
raw/net/overall totals, coverage and ranks as pure domain functions.

**Do not change:** live UI or model forecasts.

**Must pass:** all machine-readable golden live cases, ACC-LIVE-001–007 and legacy
`tests.test_live_gameweek` parity.

## Slice 06 — Live experience and manager matrix

**Read first:** live page contract, component catalogue, design system, scoring
rules and schema.

**Implement:** personal scoreboard, player progress, matrix modes, threats/leverage,
state legend and freshness/degraded behaviour.

**Do not change:** underlying score calculations.

**Must pass:** ACC-LIVE-008–010, GOLD-UI scenarios, 390px and desktop screenshots.

## Slice 07 — Transfer decision page

**Read first:** Transfer page contract, effective squad/action contracts, source
register and current recommendation evidence.

**Implement:** current action state, authoritative decision hero, route comparison,
hold/roll, evidence, decision breakers, explicit working/executed controls.

**Do not change:** simulation algorithms unless a separate model slice requests it.

**Must pass:** all ACC-TRN scenarios and cross-view effective-squad identity.

## Slice 08 — Pick Team

**Read first:** Pick Team page contract, component catalogue, effective-squad
contract and official formation rules.

**Implement:** legal XI selector, captain/vice, bench order, pitch, incoming-player
outcome and rationale.

**Do not change:** transfer route selection.

**Must pass:** ACC-TEAM-001–002 and legal formation fixtures.

## Slice 09 — Squad Strategy and Player Pool

**Read first:** relevant page contracts, source register, design system and model
authority distinctions.

**Implement:** shape summary, fixture outlook, decision timeline, chip windows,
bounded searchable player list, factors, fixtures and badges.

**Do not change:** challenger promotion status.

**Must pass:** ACC-PLY-001, mobile bounding and new strategy/chip acceptance tests.

## Slice 10 — Between-Games Watch and workload

**Read first:** Between-Games contract, source register, components and freshness.

**Implement:** change baseline, trends, next events, workload observations,
research/price changes and workflow health.

**Do not change:** source authority; no unsourced player ratings.

**Must pass:** ACC-PLY-002, ACC-BTW-001–002 and source-failure fixtures.

## Slice 11 — Canonical pipeline and atomic publication

**Read first:** target architecture, ADR-002, runbook, schemas and source register.

**Implement:** canonical producers, cross-contract validation, immutable artifact
sets, normal/live manifests and last-known-good publication.

**Do not change:** deployed client contract until adapters support the new version.

**Must pass:** ACC-OPS-001–003, simulated producer failure and rollback drill.

## Slice 12 — Cutover and legacy retirement

**Read first:** all page contracts, traceability, runbook and decision register.

**Implement:** production deployment, full critical-journey/browser verification,
archive compatibility and controlled removal of stage assets.

**Do not change:** frozen historical artifacts.

**Must pass:** every linked acceptance scenario, all golden data, full CI, mobile
and desktop visual review, production smoke test and rollback rehearsal.

## Standard completion report

Each slice returns:

```text
Outcome:
Requirements implemented:
Contracts changed:
Tests and results:
Visual evidence:
Traceability updated:
Known limitations/open decisions:
Rollback:
```

## Prompt wrapper

Use this wrapper when handing a slice to an LLM:

```text
Implement Slice NN from spec/delivery/llm-build-manifest.md.
Treat /spec as authoritative in the order defined by spec/README.md.
Read every “Read first” artefact completely before editing.
Preserve all “Do not change” boundaries.
Run every stated acceptance and validation check.
If code and spec disagree, implement the spec unless it records the matter as open;
for an open decision, stop and report the smallest concrete choice required.
Return the standard completion report with file paths and test evidence.
```
