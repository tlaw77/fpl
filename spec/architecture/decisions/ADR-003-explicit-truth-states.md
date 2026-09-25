# ADR-003: Explicit Truth States

- Status: Accepted
- Date: 2026-09-25

## Context

The product must combine official values, calculated live scores, deterministic
autosub projections, model forecasts and user-declared executed transfers. Generic
labels such as “confirmed”, “live total” and “current squad” are ambiguous.

## Decision

Every decision-critical value carries or inherits a canonical truth state. Official,
declared, working, derived, rule-projected, modelled, challenger and historical
values remain separately named through contracts and selectors.

## Consequences

- KPIs and matrices can remain consistent without hiding provenance.
- Compatibility adapters must classify legacy fields.
- UI copy can be concise but accessible metadata and explanatory states must retain
  the distinction.
