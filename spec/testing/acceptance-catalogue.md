# Acceptance Catalogue

These scenarios are product acceptance requirements. Unit tests may cover the same
rule at a lower level; acceptance IDs remain stable across implementations.

## Shell and lifecycle

### ACC-SHELL-001 — Applicable phase

```gherkin
Given the official next deadline and fixture states are available
When the application starts
Then it derives exactly one canonical lifecycle phase
And every phase-aware view uses the same target gameweek and phase
```

### ACC-SHELL-002 — Wrong-gameweek live artifact

```gherkin
Given the lifecycle target is GW5
And the latest live artifact targets GW4
When the shell loads live data
Then it rejects the artifact as inapplicable
And GW5 KPIs are not overwritten
And the last valid current context remains visible
```

### ACC-SHELL-003 — Background refresh preserves interaction

```gherkin
Given Terry is viewing an expanded manager row on League Intel
When a valid refreshed artifact arrives
Then the active tab remains League Intel
And the expanded row and keyboard focus are preserved where the row still exists
```

### ACC-SHELL-004 — Mobile containment

```gherkin
Given a 390px-wide viewport
When each primary page and live composition renders
Then the page has no horizontal overflow
And any wide matrix scrolls only inside its bounded container
```

## Transfer and effective squad

### ACC-TRN-001 — Working plan is reversible

```gherkin
Given the official operational squad
When Terry selects a legal transfer route for exploration
Then the route is stored as a working plan
And exploratory views use the projected squad
And the operational current squad remains labelled as not executed
```

### ACC-TRN-002 — Declared execution applies immediately

```gherkin
Given a selected route is not yet visible in the FPL API
When Terry explicitly records that the route was executed in FPL
Then an immutable declared-executed action is appended
And the operational effective squad applies every move exactly once
And Transfer, Pick Team, Squad Strategy and Player Pool use that same squad
```

### ACC-TRN-003 — Official reconciliation

```gherkin
Given a declared-executed transfer is active as an overlay
When official FPL history contains the same target gameweek and moves
Then the action becomes officially confirmed
And the overlay no longer changes the already-official squad
And bank, free transfers and player membership are not applied twice
```

### ACC-TRN-004 — Correct a declaration

```gherkin
Given Terry previously declared an incorrect executed route
When he explicitly records the correction
Then a new action supersedes the old action
And the audit record retains both entries
And only the current non-superseded action affects the effective squad
```

### ACC-TRN-005 — Route legality

```gherkin
Given a route exceeds budget, violates position replacement, exceeds three players
from a club or produces an invalid 15-player squad
When route selection is attempted
Then the route is rejected with named violations
And it cannot become a working or declared-executed action
```

### ACC-TRN-006 — Free transfers and hits

```gherkin
Given N available free transfers
When M transfers are executed for the deadline
Then remaining free transfers are max(N - M, 0)
And incurred hit is max(M - N, 0) multiplied by four
And the same values appear in every consuming view
```

## Pick Team

### ACC-TEAM-001 — Legal recommended XI

```gherkin
Given a valid effective 15-player squad
When Pick Team generates a recommendation
Then it selects exactly 11 players
And selects exactly one goalkeeper, 3-5 defenders, 2-5 midfielders and 1-3 forwards
And provides captain, vice-captain and four-player bench order
```

### ACC-TEAM-002 — Transfer outcome is explicit

```gherkin
Given the effective squad includes an incoming working or declared player
When Pick Team renders
Then the incoming player is visibly identified
And the page states whether the player starts or is benched
And a benched incoming player is not presented as an immediate XI gain
```

## Live scoring

### ACC-LIVE-001 — Multiplier and hit arithmetic

```gherkin
Given a captain has five raw points and a submitted multiplier of two
And the manager has a four-point transfer hit
When live totals are calculated
Then calculated live raw is 10
And calculated live net is 6
And the hit is displayed separately from player contributions
```

### ACC-LIVE-002 — Upcoming zero minutes

```gherkin
Given a submitted starter has zero minutes
And a relevant fixture is still upcoming
When projected-rule substitutions are calculated
Then the starter is not a confirmed DNP
And no bench player is promoted for that starter
```

### ACC-LIVE-003 — Legal projected autosub

```gherkin
Given a submitted starter is a confirmed DNP
And the first eligible bench player has appeared
And the resulting formation is legal
When projected-rule scoring is calculated
Then the starter is projected out
And the bench player is projected in with multiplier one
And their points appear in projected-rule totals, KPIs and manager matrix
```

### ACC-LIVE-004 — Pending first substitute retains priority

```gherkin
Given a submitted starter is a confirmed DNP
And the first legal bench player's fixture is upcoming
And a later bench player has already scored
When projected-rule scoring is calculated
Then the first bench player is projected-in-pending
And the later bench player's score is not counted yet
```

### ACC-LIVE-005 — Formation skip

```gherkin
Given replacing a confirmed-DNP defender with the first outfield substitute would
leave fewer than three defenders
And a later bench defender is eligible
When autosubs are projected
Then the first substitute is skipped
And the later defender is projected in
```

### ACC-LIVE-006 — Captain fallback

```gherkin
Given the submitted captain is a confirmed DNP
And the submitted vice-captain has appeared and remains active
When captaincy is projected
Then the captain multiplier becomes zero
And the vice-captain receives the captain's original multiplier
And the change remains labelled projected until official processing
```

### ACC-LIVE-007 — Partial reveal

```gherkin
Given at least one mini-league manager has fewer than 15 revealed picks
When provisional ranks are calculated
Then that manager is excluded from the provisional rank set
And coverage identifies the missing entry
And the manager is not treated as having zero points
```

### ACC-LIVE-008 — Consistent score basis

```gherkin
Given projected autosubs change Terry's expected eventual score
When League Intel renders
Then the headline KPI and manager matrix show the same projected-rule score
And the official/current score basis remains identifiable
```

### ACC-LIVE-009 — State palette

```gherkin
Given upcoming, live and completed players appear together
When live components render
Then live is cyan across player strip, matrix, fixtures and progress pills
And complete uses a distinct solid slate treatment
And upcoming remains neutral or unfilled
```

### ACC-LIVE-010 — Freshness warning

```gherkin
Given the phase is LIVE
And the newest valid live artifact is more than eight minutes old
When the page renders
Then the last score remains visible
And the interface says update delayed
And it does not claim the browser view is current
```

## Player and monitoring

### ACC-PLY-001 — Evidence completeness

```gherkin
Given an optional research or workload source is unavailable
When a player ranking renders
Then the missing factor is labelled unavailable
And it is not silently converted to a zero score
And official player/fixture evidence remains usable
```

### ACC-PLY-002 — Workload provenance

```gherkin
Given midweek or international minutes, goals, assists or ratings are displayed
When Terry opens the workload evidence
Then each observation names its competition/date and source
And a subjective rating names its provider
```

### ACC-BTW-001 — Named trend baseline

```gherkin
Given a metric is shown as rising or falling between gameweeks
When the trend renders
Then the metric and comparison baseline are named
And missing snapshots are visible rather than interpolated as facts
```

### ACC-BTW-002 — Executed transfer during API limbo

```gherkin
Given Terry executed a permanent transfer after the last deadline
And official picks for the next gameweek are not yet visible
When Between-Games Watch renders
Then the incoming player appears in the operational squad
And the transfer is labelled declared, awaiting official reconciliation
```

## Resilience and operations

### ACC-OPS-001 — Last known good

```gherkin
Given a validated snapshot is currently published
And the next pipeline run fails schema or semantic validation
When publication completes
Then the manifest still references the prior valid snapshot
And workflow diagnostics record the failed candidate
```

### ACC-OPS-002 — Atomic artifact set

```gherkin
Given a normal pipeline generates several dependent contracts
When the new manifest is advanced
Then every referenced contract belongs to the same coherent run/input set
And no consumer can observe a partially published set
```

### ACC-OPS-003 — Optional failure isolation

```gherkin
Given an external research producer fails
When the normal pipeline runs
Then official and deterministic contracts can still publish
And affected research/model confidence is degraded explicitly
```

## Release definition of done

A slice is complete only when:

- all linked acceptance IDs pass;
- schemas and semantic invariants pass;
- 390px and desktop visual checks pass for UI work;
- accessibility state labels and keyboard behaviour pass;
- traceability is updated;
- no adjacent capability listed as “Do not change” regresses.
