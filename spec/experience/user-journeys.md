# User Journeys

## Journey 1 — Routine between-gameweek review

**Trigger:** Previous gameweek is finalised.

**Goal:** Understand what changed and whether anything needs attention now.

1. Terry opens the app and sees the next deadline, current effective squad and last
   successful refresh.
2. Between-Games Watch summarises outcome, recommendation movement, workload,
   injuries, price/research changes and workflow issues against a named baseline.
3. Terry can distinguish “act”, “watch” and “no action”.
4. He opens a relevant player or evidence item for detail.
5. He leaves without choosing a route; no plan state is written automatically.

**Success:** Terry knows the next meaningful check time and has no false impression
that monitoring evidence is an executed decision.

## Journey 2 — Explore and choose a transfer

**Trigger:** Transfer decision becomes actionable.

**Goal:** Compare hold/roll and credible routes, then save a working choice.

1. Transfer opens with the authoritative recommendation and current action state.
2. Terry compares route legality, free transfers/hit, XI impact, multi-GW benefit,
   ownership, minutes and source freshness.
3. He may inspect challenger evidence without it replacing the promoted answer.
4. He selects hold/roll or a route as the working plan.
5. All exploratory views update from the same working effective squad.
6. The app continues to label the choice as not executed.

**Success:** One reversible plan is visible everywhere and the rationale remains
auditable.

## Journey 3 — Record an executed transfer during API limbo

**Trigger:** Terry completes a transfer on the FPL site before it is visible through
the next official picks/history response.

**Goal:** Keep the Decision Centre operationally accurate.

1. Terry opens the selected route and chooses `Executed in FPL`.
2. The app shows the exact move(s), target GW, cost and free-transfer/hit consequence.
3. Terry explicitly confirms the declaration.
4. An append-only `declared_executed` action is recorded.
5. Effective squad, Pick Team, Strategy and Player Pool update immediately.
6. The UI says the action awaits official reconciliation.
7. Later, the pipeline matches official history and marks it officially confirmed
   without applying it twice.

**Success:** The current squad is accurate during the hidden-transfer period and the
official/audit distinction remains clear.

## Journey 4 — Correct an incorrect declaration

**Trigger:** Terry realises the recorded executed route was wrong.

**Goal:** Correct operational state without destroying history.

1. Terry opens current action details and selects correction.
2. The app displays the existing declaration and requires the replacement/cancel
   intent explicitly.
3. A new ledger action supersedes the old one.
4. Effective squad is rebuilt from official state plus active actions.
5. Both records remain visible in audit history.

**Success:** No direct destructive edit is required and the squad is recalculated
exactly once.

## Journey 5 — Final deadline check

**Trigger:** Deadline is within six hours.

**Goal:** Submit one coherent team and transfer decision.

1. The shell prioritises unresolved blockers and data freshness.
2. Transfer shows current executed/working state and any decision breaker.
3. Pick Team shows the legal XI, captain, vice and bench order using the same
   effective squad.
4. Terry checks incoming-player start/bench consequence and captaincy rationale.
5. He performs the action externally and optionally records executed state.

**Success:** No view refers to a different squad or stale route, and unresolved
evidence is explicit.

## Journey 6 — Deadline lock and reveal

**Trigger:** Official deadline passes.

**Goal:** Transition safely from planning to observation.

1. Editing the locked-GW plan is disabled.
2. The app preserves the submitted/declared reference while waiting for official
   manager picks.
3. Reveal coverage shows expected, visible and complete managers.
4. Partial managers are not assigned zero points or ranks.
5. Once complete enough, the live experience becomes primary.

**Success:** No unrevealed rival data leaks and partial coverage is not mistaken for
a football outcome.

## Journey 7 — Monitor a live gameweek

**Trigger:** At least one fixture is live.

**Goal:** See Terry's score/rank and what is driving movement.

1. League Intel leads with personal score, provisional rank, players live/remaining
   and a freshness indicator.
2. Live players are cyan across the player strip, matrix and fixtures.
3. Terry inspects manager score build-up, threats and leverage.
4. A published refresh updates scores without switching tabs or collapsing context.
5. Score changes display a temporary movement cue.
6. If data exceeds the live threshold, the existing score stays visible with
   `update delayed`.

**Success:** KPI, player contributions and matrix totals reconcile exactly.

## Journey 8 — Understand a projected autosub

**Trigger:** A submitted starter becomes a confirmed DNP.

**Goal:** Understand the likely eventual score before FPL processes substitutions.

1. The engine evaluates bench priority and legal formation.
2. The starter is marked projected out and the eligible sub projected in/pending.
3. Personal and manager projected-rule totals update consistently.
4. Official/current totals remain separately identifiable.
5. If the first eligible sub is still upcoming, their priority is retained without
   counting a later bench player's points prematurely.

**Success:** Terry sees the expected consequence without it being misrepresented as
official final scoring.

## Journey 9 — All fixtures complete, FPL still settling

**Trigger:** Every fixture is complete but the event is not officially final.

**Goal:** Reconcile the likely result and wait safely for finalisation.

1. State changes to `FIXTURES_COMPLETE_SETTLING`.
2. Completed styling is solid slate, distinct from live cyan.
3. Rule-projected substitutions/captaincy lead the expected score view.
4. The page names outstanding official processing.
5. Settlement refresh continues at its slower cadence.

**Success:** The app neither stops too early nor calls a projected result official.

## Journey 10 — Producer failure

**Trigger:** An official, optional or publication step fails.

**Goal:** Preserve a useful and honest application.

1. The candidate artifact fails validation or carries a degraded status.
2. Required-source failure prevents manifest advancement; last known good remains.
3. Optional-source failure allows official/deterministic artifacts to publish with
   named missing evidence.
4. Freshness/health identifies the affected surface and last success.
5. Terry can use a manual check/retry where appropriate.

**Success:** A failure cannot replace valid data with empty, mixed-run or wrongly
classified information.
