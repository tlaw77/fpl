# Page Contracts

## Shared page shell

Every primary view uses the same header, lifecycle, freshness, navigation and KPI
selectors. Background refresh must not switch the selected tab.

The page shell consumes only canonical contracts and rejects a live artifact whose
target GW does not match the current lifecycle.

## League Intel

### Primary question

Where does Terry stand, which managers and players matter now, and what is causing
or could cause movement?

### Information order

1. Phase-aware league position summary.
2. Personal score/rank context during live phases.
3. Manager matrix with toggle between player alignment and score build-up.
4. Threat and leverage ledger.
5. Target-rival comparison and strategic posture.
6. Historical rank/points trend and deeper squad profiles.

### Phase behaviour

- Planning: official standings, trends, target rival and next-decision exposure.
- Locked: coverage/reveal status; no unrevealed squads inferred.
- Live/between fixtures: provisional score/rank and matrix become primary.
- Complete settling: projected-rule totals lead, clearly provisional.
- Finalised: official result and movement replace projections.

### Acceptance essentials

- KPI and manager-matrix scores agree for the same score basis.
- Projected autosub/captain effects are visible at player and manager level.
- Missing rival picks reduce coverage rather than create zero scores.
- Matrix is horizontally bounded and page remains stable at 390px.

## Transfer

### Primary question

Should Terry hold/roll or make a transfer route, and what evidence would change the
answer?

### Information order

1. Current action state: no choice, working plan, declared executed or official.
2. Authoritative recommendation with concise rationale and confidence.
3. Route comparison including hold/roll and legal one/multi-transfer options.
4. Impact on XI, bank, free transfers, hit and multi-GW outlook.
5. Evidence: fixtures, minutes, availability, ownership, research and market.
6. Decision breakers, challengers and historical decision journal.

### Interaction rules

- Selecting a route creates/replaces a reversible working plan.
- Selecting hold/roll clears the transfer working plan only.
- “Executed in FPL” is a distinct explicit action with route summary confirmation.
- Declared execution updates effective squad across all views immediately.
- Official reconciliation removes overlay effect without erasing the audit record.

### Acceptance essentials

- Invalid budget, position or club-limit routes cannot be selected.
- Old recommendation is not presented as active after a different route is declared.
- Multi-transfer hit/free-transfer arithmetic is consistent everywhere.
- Optional research failure does not hide the core recommendation and legality.

## Pick Team

### Primary question

What legal XI, captain, vice-captain and bench order should be submitted for the
target gameweek?

### Information order

1. Effective-squad basis and target GW.
2. Recommended legal pitch XI and formation.
3. Captain and vice-captain with rationale.
4. Bench order.
5. Marginal decisions and effect of the selected/declared transfer.

### Acceptance essentials

- Exactly 11 starters with legal formation and one goalkeeper.
- Effective squad matches Transfer, Strategy and Player Pool views.
- Incoming player explicitly says starts or benched.
- Recommendation is not confused with already submitted official picks.

## Squad Strategy

### Primary question

What structural strengths, risks and future windows should shape decisions beyond
the immediate deadline?

### Information order

1. Squad health/shape summary and current effective-squad basis.
2. Six-GW fixture and availability outlook.
3. Position spend, bench value and club concentration.
4. Decision timeline: team/captaincy checks and transfer pressure.
5. Chip window evaluation, confirmed/potential blanks and doubles.
6. Challenger scenarios and longer-horizon detail.

### Acceptance essentials

- Confirmed and potential blank/double events are distinct.
- Challenger model never appears as the promoted recommendation without promotion.
- A working/declared transfer updates structural metrics once, not twice.

## Player Pool

### Primary question

Which players are credible alternatives and why?

### Information order

1. Search, position and decision-profile filters.
2. Ranked, bounded player results.
3. Factor breakdown: model, fixtures, minutes, value, ownership, research and market.
4. Multi-GW fixtures and workload evidence.
5. Detailed comparison for selected candidates.

### Acceptance essentials

- Player data is current and data-driven; IDs, not names, join records.
- Current squad, working-plan in/out and declared route badges are distinct.
- Missing optional factors lower evidence completeness rather than becoming zero.
- Mobile results remain bounded and usable without page-level horizontal overflow.

## Live Gameweek experience

This is a phase adaptation led from League Intel, not necessarily a sixth permanent
tab.

### Primary question

What is happening to Terry's score and mini-league position right now?

### Required content

- target GW, phase and freshness;
- personal calculated-live/projected-rule score basis and provisional rank;
- raw score, hit and net explanation where material;
- players live, complete and remaining;
- live player points and counted points;
- projected autosub/captaincy changes;
- all-manager matrix;
- threats, leverage and recent movements;
- coverage/degraded warnings.

### Refresh

- Source target during live fixtures: approximately five minutes.
- Open client may check more frequently for a newly published artifact.
- More than eight minutes old during `LIVE` displays `update delayed`.
- Refresh never changes active tab or collapses an open manager row.

## Between-Games Watch

This is a planning-phase composition rather than a disconnected duplicate page.

### Primary question

What changed since the last deadline, what needs attention, and when is the next
meaningful decision point?

### Required content

1. Current operational squad including declared transfers.
2. Change summary against a named prior snapshot.
3. Upcoming deadline/fixtures and time until them.
4. Midweek/international minutes, starts, goals, assists, injury evidence and rating
   when a contracted source is available.
5. Price/research/press-conference changes.
6. Recommendation movement and decision breakers.
7. Workflow/data freshness and failures affecting the answer.

### Acceptance essentials

- Trend direction names its metric and baseline.
- Information is consolidated; charts and narrative do not repeat the same facts.
- No player rating is shown without its provider/source.
- A completed real transfer is reflected even while official picks remain hidden.

## Operations and degraded experience

Operational health may be a secondary panel, but it is accessible from every phase
through freshness status.

- Show last successful core, live and optional-evidence generations separately.
- Name affected surfaces for a failure.
- Provide safe manual retry/check guidance where available.
- Never imply a browser refresh repairs a failed upstream workflow.
