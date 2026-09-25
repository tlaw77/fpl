# Canonical Contract Index

This index defines the target contract boundaries. Detailed JSON Schemas will be
added incrementally; this document controls ownership and naming now.

## Contract envelope

Every published snapshot uses a common envelope:

```json
{
  "schema": "fpl.live-gameweek",
  "schema_version": 1,
  "status": "success",
  "target_gw": 5,
  "truth_state": "derived_current",
  "source_captured_at_utc": "2026-09-24T20:43:00Z",
  "generated_at_utc": "2026-09-24T20:44:00Z",
  "inputs": [
    {"schema": "fpl.official-event-live", "version_or_capture": "2026-09-24T20:43:00Z"}
  ],
  "coverage": {},
  "warnings": [],
  "data": {}
}
```

Allowed top-level status values are `success`, `partial`, `degraded` and `failed`.
A `failed` build is not published over the last known good snapshot.

## Core contracts

| Schema name | Owner | Truth state | Key responsibilities |
|---|---|---|---|
| `fpl.lifecycle` | Lifecycle service | `derived_current` | Target/current/next GW, canonical phase, deadline, fixture summary and applicability |
| `fpl.official-squad` | Official ingestion | `official_current` | Latest verified 15-player permanent squad and official transfers |
| `fpl.action-ledger` | User command service | mixed, event-level | Working choices, declared-executed actions, reconciliation and corrections |
| `fpl.effective-squad` | Squad domain service | `derived_current` | Official squad plus valid declared overlay; optional working-plan projection |
| `fpl.submitted-picks` | Live ingestion | `official_current` | Locked GW picks, original multipliers, captaincy, chip and hit |
| `fpl.live-gameweek` | Live scoring service | mixed fields | Fixtures, live points, calculated totals, projected-rule totals, exposure and coverage |
| `fpl.decision-context` | Decision aggregation | mixed inputs | Current actionable evidence, freshness and blockers |
| `fpl.recommendation` | Decision synthesis | `model_forecast` | Single promoted action plus alternatives and decision breakers |
| `fpl.history-manifest` | Archive service | `historical_frozen` | Immutable references to completed-GW evidence |

## Entity identifiers

| Entity | Canonical identifier | Notes |
|---|---|---|
| Gameweek | integer `gw` | Never infer solely from filename |
| Player | integer FPL element ID `player_id` | Names are display fields, never join keys |
| Club | integer FPL team ID `club_id` | Store current display name separately |
| Manager entry | integer FPL entry ID `entry_id` | Team/manager names can change |
| Fixture | integer FPL fixture ID `fixture_id` | Use source namespace if non-FPL fixture is included |
| Transfer command | immutable string `action_id` | Separate from route/model identifiers |
| Recommendation | immutable string `recommendation_id` | Include model/input fingerprint |
| Snapshot | immutable string `snapshot_id` | Derived from schema, target and generation identity |

## Effective squad contract

Required data fields:

```json
{
  "entry_id": 5332809,
  "target_gw": 6,
  "basis": "official_plus_declared",
  "official_squad_capture": "...",
  "applied_action_ids": ["..."],
  "working_plan_id": null,
  "players": [],
  "bank_tenths": 4,
  "free_transfers_before": 1,
  "free_transfers_used": 1,
  "free_transfers_remaining": 0,
  "hit_already_incurred": 0,
  "next_transfer_cost": 4,
  "legality": {"valid": true, "violations": []}
}
```

Money is stored canonically in integer tenths of a million. Formatting as `£0.4m`
belongs to presentation.

## Live manager contract

Each manager record carries all score bases explicitly:

```json
{
  "entry_id": 5332809,
  "submitted_hit": 4,
  "official_gw_points": 20,
  "calculated_live_raw": 28,
  "calculated_live_net": 24,
  "projected_rule_raw": 34,
  "projected_rule_net": 30,
  "official_total_before_gw": 189,
  "calculated_live_overall": 213,
  "projected_rule_overall": 219,
  "official_rank": 3,
  "calculated_live_rank": 2,
  "projected_rule_rank": 1,
  "picks": []
}
```

Do not use a lone `live_points`, `total` or `live_rank` field in the new contract.

## Live pick contract

```json
{
  "slot": 13,
  "player_id": 212,
  "position_id": 3,
  "fixture_state": "complete",
  "minutes": 90,
  "raw_player_points": 6,
  "submitted_multiplier": 0,
  "projected_rule_multiplier": 1,
  "official_final_multiplier": null,
  "calculated_live_counted_points": 0,
  "projected_rule_counted_points": 6,
  "autosub_state": "projected_in",
  "autosub_counterpart_player_id": 165,
  "captaincy_state": "none"
}
```

Allowed `autosub_state` values:

- `none`
- `projected_out`
- `projected_in`
- `projected_in_pending`
- `official_out`
- `official_in`

Allowed `captaincy_state` values:

- `none`
- `submitted_captain`
- `submitted_vice`
- `projected_captain_out`
- `projected_vice_promoted`
- `official_captain`

## Fixture contract

Required fields include `fixture_id`, `gw`, `home_club_id`, `away_club_id`,
`kickoff_utc`, `state`, `minutes`, `finished_provisional` and source capture time.
Allowed canonical states are `upcoming`, `live`, `complete` and `unknown`.

## Action ledger contract

An action is append-only and may be superseded:

```json
{
  "action_id": "tx-...",
  "entry_id": 5332809,
  "target_gw": 6,
  "action_type": "transfer_route",
  "state": "declared_executed",
  "moves": [
    {"out_player_id": 496, "in_player_id": 572, "out_cost_tenths": 45, "in_cost_tenths": 46}
  ],
  "declared_at_utc": "...",
  "officially_reconciled_at_utc": null,
  "supersedes_action_id": null,
  "source": "explicit_user_command"
}
```

Allowed state transitions:

`working_plan → declared_executed → official_confirmed`

A correction produces a new action that supersedes the old record; history is not
deleted silently.

## Consumer ownership rule

- KPIs, manager matrix and charts consume the same live-manager selector.
- Pick Team, Transfer, Squad Strategy and Player Pool consume the same effective
  squad selector.
- Page components may format and filter, but may not recalculate domain totals.
- Compatibility adapters may translate legacy JSON during migration; adapters must
  not become new sources of business logic.

## Contract validation requirements

1. JSON Schema validation.
2. Semantic validation: squad count, legal positions, unique IDs, arithmetic totals.
3. Applicability validation: target GW and entry match the requested context.
4. Freshness validation against lifecycle phase.
5. Cross-contract reconciliation: declared transfers are not double-applied;
   projected score arithmetic agrees with pick contributions.
