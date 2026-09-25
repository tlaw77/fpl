# Live Scoring and Rule Projection

## Scope

This specification defines deterministic live manager scoring. It does not forecast
points a player may earn later. It consumes official submitted picks, current
official event-live points, fixture state and official transfer-hit cost.

## Inputs

For each manager:

- exactly 15 submitted picks;
- original squad slot/bench order;
- submitted multiplier, captain and vice-captain flags;
- active chip;
- official transfer-hit cost;
- current raw player points and minutes;
- all relevant fixture states for each player's club.

If the 15-player squad is incomplete, the manager has partial coverage and must not
be ranked as though missing players scored zero.

## Fixture and player state

For a player's relevant gameweek fixtures:

1. If any is live, player state is `live`.
2. Else if any is upcoming, player state is `upcoming`.
3. Else if at least one exists and all are complete, state is `complete`.
4. Otherwise state is `unknown`.

This handles double gameweeks: zero minutes after the first completed fixture is not
a confirmed DNP while another relevant fixture remains upcoming.

## Base calculations

For pick `p`:

```text
calculated_live_counted_points(p)
  = raw_player_points(p) × submitted_multiplier(p)
```

For manager `m`:

```text
calculated_live_raw(m)
  = Σ calculated_live_counted_points(p)

calculated_live_net(m)
  = calculated_live_raw(m) − submitted_hit(m)

calculated_live_overall(m)
  = official_total_before_gw(m) + calculated_live_net(m)
```

The player points build-up displays the raw score. The hit is a separate deduction;
do not make player contributions appear negative to explain a large hit.

## Confirmed DNP

A player is a `confirmed_dnp` only when:

```text
player fixture state = complete
AND official minutes across the event = 0
```

`upcoming`, `live` and `unknown` players are never confirmed DNPs.

## Autosub algorithm

Skip all autosub projection when Bench Boost is active; all 15 submitted multipliers
already count according to the official picks contract.

Otherwise:

1. Copy every submitted multiplier into `projected_rule_multiplier`.
2. Process confirmed-DNP submitted starters in ascending submitted slot order.
3. For a goalkeeper DNP, consider only the bench goalkeeper.
4. For an outfield DNP, consider outfield bench players in submitted bench order.
5. Skip a candidate already used for another substitution.
6. Skip a candidate who is themselves a confirmed DNP.
7. Temporarily apply the substitution and validate the resulting active XI:
   - exactly one goalkeeper;
   - 3–5 defenders;
   - 2–5 midfielders;
   - 1–3 forwards;
   - 11 active players.
8. If illegal, restore multipliers and continue to the next eligible bench player.
9. If legal:
   - outgoing multiplier becomes zero and state `projected_out`;
   - incoming multiplier becomes one;
   - if incoming has appeared, state `projected_in`;
   - if incoming fixture is upcoming/live with zero minutes, state
     `projected_in_pending` and reserve their priority position;
   - stop searching for that outgoing player.

A `projected_in_pending` player can contribute zero current points. Do not skip them
for a later bench scorer merely because their fixture has not occurred. If they
later become a confirmed DNP, recomputation may move to the next eligible candidate.

## Captaincy projection

After projected autosubs:

1. Find the submitted captain and vice-captain.
2. If the captain is not a confirmed DNP, retain submitted captain multiplier.
3. If the captain is a confirmed DNP, set their projected multiplier to zero.
4. Promote the vice-captain only when:
   - the vice-captain has appeared (`minutes > 0`); and
   - the vice-captain remains active after projected autosubs.
5. The promoted multiplier equals the captain's original submitted multiplier:
   normally two, or three for Triple Captain.
6. If the vice-captain has not yet appeared, do not award a projected captain
   multiplier. Recompute when new official evidence arrives.

## Projected-rule totals

```text
projected_rule_counted_points(p)
  = raw_player_points(p) × projected_rule_multiplier(p)

projected_rule_raw(m)
  = Σ projected_rule_counted_points(p)

projected_rule_net(m)
  = projected_rule_raw(m) − submitted_hit(m)

projected_rule_overall(m)
  = official_total_before_gw(m) + projected_rule_net(m)
```

These are deterministic rule projections, not forecasts. They include no assumed
future points.

## Ranking

Calculate separate ranks for each basis:

- official rank from FPL standings;
- calculated-live rank from `calculated_live_overall`;
- projected-rule rank from `projected_rule_overall`.

Use standard competition ranking unless the page specification explicitly defines
another display. Tie-break behaviour must be deterministic and must not imply a
points difference where none exists.

Managers with incomplete revealed squads are excluded from provisional ranking and
reported in coverage.

## Exposure

For player `p` and comparison cohort of `N` complete managers:

```text
cohort_average_multiplier(p)
  = Σ manager multiplier(p) / N

damage_per_point(p)
  = max(cohort_average_multiplier(p) − Terry multiplier(p), 0)

gain_per_point(p)
  = max(Terry multiplier(p) − cohort_average_multiplier(p), 0)
```

Both submitted and projected-rule exposure may be useful; the displayed basis must
be labelled and consistent with the selected manager score basis.

## Display requirements

- Live fixture/player state uses cyan.
- Completed state is a distinct solid colour/token.
- Upcoming state is neutral/unfilled.
- A player tile shows raw points and, when different, counted points.
- Autosub and captaincy projection markers are visible but do not imply official
  processing.
- KPI, manager matrix and charts use one shared score-basis selector.
- Freshness identifies the live artifact generation time and target GW.

## Invariants

1. Sum of pick counted points equals the corresponding manager raw total.
2. Net total equals raw total minus hit.
3. Overall equals pre-GW baseline plus net total.
4. No bench player has projected multiplier greater than one unless separately
   promoted as vice-captain after becoming active.
5. Projected XI is legal or contains fewer than 11 only when no legal playing bench
   replacement exists.
6. A player is never both projected in and projected out.
7. Artifact GW must match the lifecycle target before scores enter current KPIs.
