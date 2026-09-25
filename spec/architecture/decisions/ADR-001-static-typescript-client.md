# ADR-001: Static TypeScript Client

- Status: Accepted for parity rebuild
- Date: 2026-09-25

## Context

The current static application is inexpensive and easy to host, but behaviour is
spread across a long ordered cascade of JavaScript stage patches. A rebuild needs
explicit modules and compile-time contract safety without introducing unnecessary
server operations.

## Decision

Use Vite and TypeScript to build a static client. Organise it around contracts,
domain selectors, components and pages. Do not reproduce the historical stage-file
cascade.

## Consequences

- GitHub Pages remains viable.
- Type generation from JSON Schema is possible.
- Domain rules can be shared as fixtures even when Python remains the authoritative
  producer.
- A build step and Node toolchain become required.
- Durable user commands still require an explicit write path; local storage is not
  treated as the authoritative ledger.
