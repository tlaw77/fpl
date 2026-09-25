# Specification Delivery Plan

The goal is a complete rebuild pack, not documentation for documentation's sake.
Each phase ends with artefacts that can be handed to an LLM as a bounded delivery
context.

## Phase 1 — Recovery and classification

**Outputs**

- product vision;
- feature inventory;
- decision register;
- current-system map;
- data-source and generated-artefact register.

**Exit gate**

Every major current capability is classified as accepted, accepted gap,
provisional, retired or historical. No stage file is assumed authoritative solely
because it is loaded by `index.html`.

## Phase 2 — Domain and state contracts

**Outputs**

- domain glossary;
- gameweek lifecycle/state machine;
- effective-squad state machine;
- live scoring and autosub rules;
- transfer, captaincy, chip and formation rules;
- official/calculated/projected/modelled truth taxonomy.

**Exit gate**

The same input squad and live fixture data has one deterministic expected scoring
result, independent of UI.

## Phase 3 — Data contracts and provenance

**Outputs**

- external source register;
- canonical internal entities;
- versioned JSON/API schemas;
- derived-field ownership;
- freshness, caching and last-known-good behaviour;
- mapping from current JSON files to target contracts.

**Exit gate**

Every displayed field has a producer, source timestamp, semantics and consumer.

## Phase 4 — Experience specification

**Outputs**

- page specifications for all five views;
- live and between-gameweek phase adaptations;
- component catalogue;
- responsive/mobile behaviour;
- accessibility and semantic colour tokens;
- annotated reference screenshots or wireframes.

**Exit gate**

Each page can be built without reading historical JavaScript or conversations.

## Phase 5 — Verification pack

**Outputs**

- requirement-level acceptance criteria;
- golden calculation datasets;
- page fixtures for loading, empty, stale and error states;
- visual regression references;
- end-to-end critical journeys;
- non-functional mobile and freshness tests.

**Exit gate**

An implementation can prove parity through automated tests and bounded visual
review rather than subjective comparison alone.

## Phase 6 — Target architecture and build manifest

**Outputs**

- architecture decision records;
- target application and pipeline architecture;
- persistence and deployment design;
- operations runbook;
- ordered LLM work packages;
- final traceability matrix.

**Exit gate**

Each work package lists exactly what to read, implement, test and leave unchanged.

## Standard LLM work-package template

```markdown
# Slice <number>: <outcome>

## Read first
- requirement IDs
- page/component specifications
- calculation rules
- data contracts
- relevant ADRs

## Implement
- bounded list of outcomes

## Do not change
- explicit adjacent capabilities

## Required tests
- acceptance IDs
- golden datasets
- viewport/browser checks

## Completion evidence
- automated test result
- screenshots where visual
- contract/traceability updates
```

## Recommended next slice of specification work

Create the domain glossary, lifecycle model and truth taxonomy together. They are
the dependency for live scoring, transfers, freshness, page language and nearly
all later acceptance tests.
