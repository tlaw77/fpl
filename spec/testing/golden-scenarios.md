# Golden Scenarios

The machine-readable starter dataset is
[`golden/live-scoring-v1.json`](golden/live-scoring-v1.json). These scenarios must
pass in any clean rebuild before live UI parity is assessed.

## Scoring scenarios

| ID | Scenario | Essential expectation |
|---|---|---|
| GOLD-LIVE-001 | Captain scores with a four-point hit | Raw includes captain multiplier; hit is deducted only from net |
| GOLD-LIVE-002 | Upcoming starter has zero minutes | No autosub is projected |
| GOLD-LIVE-003 | Confirmed-DNP starter; first eligible bench player has appeared | Starter becomes projected out; first sub contributes their current points |
| GOLD-LIVE-004 | Confirmed-DNP starter; first eligible sub has not yet played | First sub is reserved as projected-in-pending; later bench score is not used yet |
| GOLD-LIVE-005 | First bench candidate would break minimum defenders | Skip them and use the next legal defender |
| GOLD-LIVE-006 | Goalkeeper DNP | Only bench goalkeeper can replace them |
| GOLD-LIVE-007 | Captain confirmed DNP; vice has appeared | Vice receives captain's original multiplier |
| GOLD-LIVE-008 | Captain confirmed DNP; vice still upcoming | No vice multiplier is awarded yet |
| GOLD-LIVE-009 | Bench Boost active | Do not run normal autosub projection |
| GOLD-LIVE-010 | Double-gameweek player has zero minutes in first match and another upcoming | Player is upcoming, not confirmed DNP |
| GOLD-LIVE-011 | Manager picks endpoint missing/partial | Exclude manager from provisional ranking and report coverage |
| GOLD-LIVE-012 | Live artifact GW differs from lifecycle target | Artifact is inapplicable and cannot update current KPIs |

## Transfer/effective-squad scenarios

| ID | Scenario | Essential expectation |
|---|---|---|
| GOLD-TX-001 | One working transfer selected | Exploratory views show projected squad; operational current squad remains unchanged |
| GOLD-TX-002 | User declares route executed before API visibility | Operational effective squad applies route exactly once |
| GOLD-TX-003 | Official API later contains the declared route | Overlay reconciles without duplicating player/bank/FT changes |
| GOLD-TX-004 | User corrects mistaken declaration | New ledger entry supersedes previous action; audit history remains |
| GOLD-TX-005 | Two free transfers used in same GW | No hit; remaining FT and next-transfer cost are correct |
| GOLD-TX-006 | Transfers exceed available FT | Four points per excess transfer are recorded as incurred hit |
| GOLD-TX-007 | Route violates three-player club limit | Route is invalid and cannot become working or declared state |

## Lifecycle/freshness scenarios

| ID | Scenario | Essential expectation |
|---|---|---|
| GOLD-PHASE-001 | More than 72 hours to deadline | `PLANNING_NORMAL` |
| GOLD-PHASE-002 | Deadline passed, no fixture started | `LOCKED_AWAITING_REVEAL` |
| GOLD-PHASE-003 | At least one fixture active | `LIVE` |
| GOLD-PHASE-004 | Some complete, others upcoming, none live | `BETWEEN_FIXTURES` |
| GOLD-PHASE-005 | All fixtures complete, event not final | `FIXTURES_COMPLETE_SETTLING` |
| GOLD-PHASE-006 | Official event final | `FINALISED` and archive/rollover eligible |
| GOLD-PHASE-007 | Live snapshot older than eight minutes during play | Data retained but marked update delayed |
| GOLD-PHASE-008 | New snapshot fails validation | Last known good remains active with degraded warning |

## UI state scenarios

| ID | Scenario | Essential expectation |
|---|---|---|
| GOLD-UI-001 | Upcoming, live and completed players in one manager row | Upcoming neutral/unfilled, live cyan, complete distinct solid token |
| GOLD-UI-002 | Projected autosub changes total | Player marker, KPI and manager matrix agree; official total remains visible or identifiable |
| GOLD-UI-003 | Live score correction decreases points | Negative movement is displayed temporarily without changing semantic fixture state |
| GOLD-UI-004 | Partial manager reveal | Coverage warning; missing manager is not shown with zero points |
| GOLD-UI-005 | 390px viewport | No horizontal page overflow; essential score/state remains visible |

## Dataset evolution

- Never change expected output of an existing scenario without a decision-register
  entry and version bump.
- Add a regression scenario whenever a real gameweek exposes a scoring/state defect.
- Keep player and club identities synthetic where football identity is irrelevant.
- Store official rule-version assumptions with each dataset.
