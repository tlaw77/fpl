# ADR-002: Atomic Contract Publication

- Status: Accepted target; migration required
- Date: 2026-09-25

## Context

Current scheduled workflows independently commit shared generated files. They use
rebase/retry loops, but consumers can still observe artifacts from different input
runs and repository writers can race.

## Decision

Publish immutable, validated artifact sets and atomically advance a small manifest.
One orchestrator owns normal publication; one bounded workflow owns the live
manifest. Optional producers cannot directly replace shared final contracts.

## Consequences

- Consumers load a coherent snapshot set.
- Rollback is a manifest pointer change.
- Independent evidence producers remain possible but need orchestration or staged
  outputs.
- Initial migration may continue using Git branches as the artifact channel.
