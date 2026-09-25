# Truth-State Taxonomy

## Purpose

The application combines facts, user actions, deterministic projections and model
forecasts. Every value that can affect a decision or score must declare which truth
state it represents.

## Canonical truth states

| State | Meaning | Example | May replace official fact? |
|---|---|---|---|
| `official_current` | Latest value returned by an official FPL endpoint, not necessarily final | event-live player points during a match | No; it is itself the current official feed value |
| `official_final` | Official value after the event is finalised | processed autosubs and final GW score | Yes, for the completed event |
| `declared_executed` | Explicit user statement that an irreversible FPL action was completed but is not yet API-visible | Kinsky → Tzolakis recorded for GW6 | Temporarily overlays effective squad; never rewrites historical official data |
| `working_plan` | Reversible scenario selected for exploration | Cherki route selected but not executed | Only inside clearly labelled planning views |
| `derived_current` | Deterministic calculation over current inputs | current damage per point | No; show derivation/source |
| `projected_rule` | Deterministic consequence whose trigger is already established, though FPL has not processed it | valid autosub for a confirmed DNP | No; show beside or clearly label against official/current value |
| `model_forecast` | Estimate of future or uncertain outcome | six-GW expected points | Never |
| `challenger` | Alternative model or scenario not promoted as authoritative | calendar-adjusted chip challenger | Never |
| `historical_frozen` | Snapshot retained to evaluate what was known at decision time | decision certificate and baseline XI | Never update in place |

## Required metadata

Important values should carry or inherit:

```json
{
  "truth_state": "projected_rule",
  "source": "live_gameweek_engine",
  "source_gw": 5,
  "source_captured_at_utc": "...",
  "generated_at_utc": "...",
  "provisional": true,
  "explanation_code": "AUTOSUB_CONFIRMED_DNP"
}
```

The exact transport may normalise metadata at snapshot rather than field level, but
the UI must be able to answer these questions:

1. Where did this value come from?
2. When was its source captured?
3. Is it official, calculated, projected or forecast?
4. Can it still change?
5. Is it applicable to the gameweek being shown?

## Squad precedence

For operational next-gameweek views, derive the effective squad in this order:

1. Begin with the latest valid `official_current` squad.
2. Apply valid `declared_executed` transfers for the target gameweek that are not
   already present in official history.
3. In exploratory planning only, apply the active `working_plan` on top of the
   operational squad.
4. Never apply the same route twice; transfer identity includes target gameweek,
   outgoing player and incoming player.
5. When the official API reflects the declared route, mark it `official_confirmed`
   and remove the overlay effect while retaining the declaration audit record.

Views must name their basis:

- **Current squad** — official plus declared-executed overlay.
- **If you choose this plan** — current squad plus working plan.
- **Submitted GW squad** — locked official picks for the named event.

## Score precedence

During an active event, keep these values separately:

| Field concept | Inputs | Use |
|---|---|---|
| Official displayed GW | FPL standings/event history | Reference and reconciliation |
| Calculated live raw | event-live points × submitted multipliers | Explain current point build-up |
| Calculated live net | calculated live raw − official hit | Live comparison before projected rule effects |
| Projected eventual raw | event-live points × projected-rule multipliers | Forward-looking point build-up |
| Projected eventual net | projected eventual raw − official hit | Preferred likely eventual manager comparison when rule effects are established |
| Forecast final | model forecast including future scoring | Prediction surfaces only |

Headline KPIs must say which live basis they use. Player rows should expose raw
points plus counted points when a multiplier changes the contribution.

## Promotion and reconciliation rules

- `working_plan` becomes `declared_executed` only after an explicit user command.
- `declared_executed` becomes `official_confirmed` only after matching official
  evidence exists.
- `projected_rule` becomes `official_final` only through official FPL processing.
- `challenger` becomes authoritative only through an explicit product/model
  promotion decision and corresponding decision-register entry.
- `historical_frozen` is immutable; corrections create a superseding record.

## Prohibited ambiguity

Do not use these unqualified field or UI labels where more than one truth state can
exist:

- `confirmed`
- `current score`
- `total`
- `squad`
- `captain`
- `updated`
- `projection`

Qualify them, for example: `declared_executed`, `projected_eventual_net`,
`submitted_captain`, `artifact_generated_at_utc`.

## Failure behaviour

- If a newer artifact fails validation, retain the last known good artifact.
- If artifact GW does not match the requested GW, mark it inapplicable and do not
  merge it into current KPIs.
- If a required truth-state marker is missing, render the value as unavailable or
  legacy-unclassified; do not silently assume official.
- Optional model/research failure must not invalidate official or deterministic
  decision surfaces.
