# Build and Operations Runbook

## Purpose

Operate, validate and recover the FPL Decision Centre without losing the last known
good decision or live snapshot.

## Local prerequisites

- Python 3.12
- Node.js current LTS for the target TypeScript client
- Git
- Network access to configured official/supporting sources

Legacy baseline tests require only the Python standard library for the four core
test modules currently used by this specification.

## Validation commands

From the repository root:

```bash
python -m unittest \
  tests.test_live_gameweek \
  tests.test_free_transfer_logic \
  tests.test_multi_transfer_planning \
  tests.test_rules_edges -v

python -m json.tool spec/testing/golden/live-scoring-v1.json >/dev/null
python -m json.tool spec/schemas/action-ledger.schema.json >/dev/null
python -m json.tool spec/schemas/effective-squad.schema.json >/dev/null
python -m json.tool spec/schemas/live-gameweek.schema.json >/dev/null
git diff --check
```

When the TypeScript client is introduced, the release gate also includes lint,
typecheck, unit tests, production build and browser critical journeys.

## Operational cadences

| Process | Target cadence | Notes |
|---|---:|---|
| Normal decision pipeline | 30 minutes | May increase near deadline through an explicit policy |
| Decision/research evidence | As orchestrated within normal run | Avoid duplicate independent writers |
| Live gate | Every 5 minutes | Lightweight when no session is needed |
| Live session | Approximately every 5 minutes while fixture live | Bounded session; stops at complete/limit |
| Locked reveal | Approximately every 10 minutes | Coverage may initially be partial |
| Between fixtures | Approximately every 25–30 minutes | No active fixture |
| Complete settling | Approximately every 25–30 minutes until official finalisation | Stop after finalisation |
| Browser live check | Approximately every 30 seconds while live page visible | Checks published artifact; does not call FPL directly |

## Pre-publication gates

1. All required sources captured or a valid degraded policy applies.
2. JSON Schema validation succeeds.
3. Semantic invariants succeed.
4. Contract target GW matches lifecycle target.
5. Cross-contract snapshot/input identifiers agree.
6. Required coverage threshold is met or status is explicitly partial.
7. Golden/regression tests pass for changed rule code.
8. Only then advance the current manifest.

## Health checks

| Check | Expected |
|---|---|
| Lifecycle | Phase and target GW agree with official deadline/fixtures |
| Core squad | Exactly 15 unique players and valid club/position counts |
| Declared overlay | Every applied action appears once and remains legal |
| Live coverage | Visible/complete/expected manager counts are explicit |
| Live scoring | Pick totals reconcile to manager raw/net/overall values |
| Freshness | Within phase threshold or visibly delayed |
| Recommendation | Input versions are current and action is legal |
| Publication | Manifest references only validated artifacts from one run |

## Failure handling

### Official FPL unavailable

- Do not publish empty replacements.
- Retain last known good official and derived contracts.
- Mark freshness delayed/degraded.
- Suspend actions requiring current official validation.

### Partial manager reveal

- Publish `partial` coverage if useful.
- Exclude incomplete managers from provisional rank calculations.
- Retry at locked/live cadence.

### Optional research failure

- Continue official/deterministic pipeline.
- Mark the affected evidence source unavailable.
- Reduce model/recommendation confidence only according to documented policy.

### Schema or invariant failure

- Fail the candidate artifact set.
- Do not advance the manifest.
- Preserve diagnostic logs and last known good snapshot.

### Publication race

- A producer that does not own the manifest must not publish it.
- The owning workflow verifies the expected prior manifest before advancing.
- On conflict, rebuild/reconcile against the newest inputs rather than merging JSON
  files manually.

### Client contract failure

- Reject the incompatible artifact.
- Retain last validated value in the session/cache if applicable.
- Display a degraded warning with schema and target-GW reason.
- Never silently coerce a forecast into a live/official value.

## Manual live incident checklist

1. Confirm official fixture state and target GW.
2. Check latest Live Gameweek workflow conclusion.
3. Inspect source/artifact generation timestamps.
4. Check manager coverage and failures.
5. Re-run the live workflow if source state is current but artifact publication
   failed.
6. Verify raw player points, multiplier and hit arithmetic for Terry.
7. Confirm client loaded the live manifest rather than an old main-branch fallback.

## Rollback

### Data only

Point the manifest to the prior validated artifact set. Do not edit a published
historical artifact in place.

### Client only

Redeploy the prior successful static build while keeping compatible data contracts.
If a contract change is incompatible, deploy its compatibility adapter with the
rollback.

### Recommendation/model only

Revert promotion to the previous synthesis/model fingerprint. Official and live
contracts continue independently.

## Archive and rollover

- Freeze the finalised GW manifest, decisions, scoring and input versions.
- Reconcile declared actions against official history.
- Clear event-scoped UI movement and working-plan state.
- Keep audit/history records append-only.
- Verify next lifecycle target before exposing next-GW actions.

## Deployment release evidence

Every release records:

- commit SHA and client build ID;
- contract/schema versions;
- golden and automated test results;
- artifact manifest ID;
- 390px and desktop visual verification for affected views;
- known degraded optional sources;
- rollback reference.
