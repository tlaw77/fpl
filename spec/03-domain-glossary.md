# Domain Glossary

These terms are normative. UI copy may use a shorter friendly label, but contracts,
tests and implementation should use the canonical term.

## Time and gameweek

| Term | Definition |
|---|---|
| Current gameweek | The FPL event currently in progress or most recently active according to official event metadata. It is not automatically the event being monitored by an old live snapshot. |
| Next gameweek | The next event for which decisions can be planned. Before a deadline it may also be the event about to become current. |
| Deadline | The official FPL deadline timestamp for an event. Store and compare it in UTC; display it in the user's locale. |
| Gameweek lifecycle phase | The canonical product state derived from deadline, fixture and official-finalisation evidence. Defined in `rules/gameweek-lifecycle.md`. |
| Between gameweeks | The decision period after the previous event is operationally finalised and before the next event locks. It is a product mode, not merely the absence of live fixtures. |
| Between fixtures | A post-deadline interval inside one gameweek where at least one fixture is complete and another is still upcoming, with none currently live. |
| Finalised | Official scores, substitutions and event status have settled sufficiently for archiving and review. “All fixtures complete” alone may still precede official finalisation. |

## Squad and actions

| Term | Definition |
|---|---|
| Official squad | The most recent 15-player squad derivable from official FPL entry history and transfer data. |
| Submitted picks | The official 15 picks, multipliers, captaincy and bench order submitted for a locked gameweek. |
| Working plan | A reversible local choice used to explore hold/roll, one transfer or a multi-transfer route. It is not a claim that the action happened. |
| Declared executed transfer | A transfer Terry explicitly records as having been completed in FPL but which is not yet visible through the official API. New contracts should use `declared_executed`, not ambiguous `confirmed`. |
| Officially confirmed transfer | A transfer present in official FPL history or otherwise verified by the official API. New contracts should use `official_confirmed`. |
| Effective squad | The squad used for downstream planning. It is derived in priority order from official squad plus valid declared-executed overlay plus, only in exploratory contexts, a working plan. |
| Hold | Make no transfer at the current decision point. |
| Roll | Make no transfer and intentionally preserve an unused free transfer for a future deadline. A UI may use “Hold / roll” when both consequences apply. |
| Transfer route | One or more ordered outgoing/incoming player pairs evaluated as a unit, including cost, legality, hit and future effects. |
| Transfer hit | The official points deduction caused by transfers beyond the available free-transfer allowance. |
| Bank | Money available after accounting for the applicable squad truth state and transfer route. |

## Scoring

| Term | Definition |
|---|---|
| Raw player points | Points currently reported by the official event-live feed for a player, before a manager-specific multiplier. |
| Submitted multiplier | Multiplier in the official submitted picks: typically 0, 1, 2 or 3. |
| Projected multiplier | Manager-specific multiplier after only rule-determined projected autosubs and captaincy fallback are applied. |
| Counted points | Raw player points multiplied by the multiplier for the named truth state. A field must say whether the multiplier is submitted, projected or official-final. |
| Raw gameweek score | Sum of counted player points before transfer-hit deduction. |
| Net gameweek score | Raw gameweek score minus transfer hits. |
| Calculated live score | A locally calculated net score using current official player points and submitted multipliers. |
| Projected eventual score | A locally calculated net score including only already-determinable legal autosubs and captaincy fallback. It is not a model forecast of future player points. |
| Forecast score | A model estimate that includes points not yet earned. It must never be labelled live or projected eventual score. |
| Official gameweek score | The score currently published by FPL for the event. It may lag during live play. |
| Live overall points | Pre-gameweek official baseline plus the selected calculated live or projected eventual gameweek score. The field name must identify which basis is used. |

## Player and fixture states

| Term | Definition |
|---|---|
| Upcoming | The relevant fixture has not started. A player with zero minutes is not a DNP in this state. |
| Live | The relevant fixture has started and is not complete. |
| Complete | The relevant fixture is marked finished or finished provisional by FPL. This does not necessarily mean the whole gameweek is finalised. |
| Unknown | Fixture/player state cannot be safely derived. Unknown must not be coerced to upcoming or complete. |
| Confirmed DNP | A submitted player has zero minutes and all relevant gameweek fixtures for that player's team are complete. |
| Projected out | A confirmed-DNP starter whose submitted multiplier is projected to become zero under autosub rules. |
| Projected in | An eligible bench player with an appearance whose multiplier is projected to become one under autosub rules. |
| Projected in pending | The first currently eligible bench player for a confirmed-DNP starter, but the bench player's own appearance is not yet established. This state must not add unearned points. |
| Players remaining | Players whose points can still change because a relevant fixture is upcoming or live. Define whether captain multipliers count as an additional “play”; the preferred UI shows player count and captaincy separately. |

## Mini-league and strategy

| Term | Definition |
|---|---|
| Ownership | Share of the comparison cohort that owns a player. Cohort must be named: global, mini-league, target rivals or elite sample. |
| Effective ownership (EO) | Average manager-specific multiplier for a player in the named cohort. It can exceed 100%. |
| Threat | A player for whom the cohort's effective multiplier exceeds Terry's, producing relative loss per point. |
| Leverage | A player for whom Terry's effective multiplier exceeds the cohort's, producing relative gain per point. |
| Shield | A highly owned player whose ownership reduces rank volatility when Terry also owns/starts them. Threshold must be provided by the exposure rules. |
| Damage per point | `max(cohort average multiplier - Terry multiplier, 0)`. It is exposure, not a prediction. |
| Gain per point | `max(Terry multiplier - cohort average multiplier, 0)`. It is exposure, not a prediction. |
| Target rival | A manager selected for direct comparative strategy, usually the nearest meaningful manager above or a named priority competitor. |
| Strategy posture | Product recommendation for variance appetite, such as protect, balanced, controlled chase or chase. |

## Evidence and modelling

| Term | Definition |
|---|---|
| Official source | Fantasy Premier League API data. Official does not guarantee the data has reached final state during live processing. |
| Derived value | Deterministic value calculated from named inputs and rules. |
| Modelled value | Probabilistic or heuristic estimate whose uncertainty and model version must be available. |
| Authoritative recommendation | The single recommendation promoted by the decision synthesis for current use. |
| Challenger | A non-authoritative alternative intended to test the robustness of the promoted recommendation. |
| Decision Twin | Explainability/challenge layer that packages and contests the authoritative recommendation; it does not autonomously override it. |
| Decision breaker | Observable evidence that should cause the current recommendation to be re-evaluated. |
| Golden dataset | Frozen input and expected output used to verify rules and presentation deterministically. |

## Freshness

| Term | Definition |
|---|---|
| Source captured at | When the upstream data was obtained. |
| Artifact generated at | When the derived snapshot was completed. |
| Browser fetched at | When the current client retrieved the artifact. |
| Snapshot age | Current time minus artifact generation time unless explicitly labelled otherwise. |
| Fresh | Snapshot age is within the phase- and source-specific service threshold. |
| Delayed | The source is expected to update in the current phase but its last valid snapshot exceeds the warning threshold. |
| Stale/inapplicable | Snapshot belongs to another gameweek or state and must not be used as current evidence, even if it was valid when produced. |
| Last known good | Most recent artifact that passed its schema and semantic validation. |
