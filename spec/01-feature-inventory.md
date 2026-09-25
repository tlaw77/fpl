# Feature Inventory

This is the baseline capability inventory recovered from the application at commit
`566045e4`, the generated datasets and the most recent accepted user iterations.
It is an inventory, not yet the detailed page or rule specification.

## Product shell and navigation

| ID | Capability | Intended status | Baseline evidence | Notes |
|---|---|---|---|---|
| SHELL-001 | Five primary tabs: League Intel, Transfer, Pick Team, Squad Strategy, Player Pool | Accepted / Implemented | `docs/index.html` | Navigation order currently begins with League Intel; Transfer markup is initially active before tab-state logic runs. Rebuild must define one canonical default. |
| SHELL-002 | Phase-aware content and language | Accepted / Implemented | phase/choreography and monitoring scripts | Detailed state model still required. |
| SHELL-003 | Fast first paint with heavy data lazy-loaded | Accepted / Implemented | `core-boot.js`, reconciliation document | Must become an architectural acceptance criterion. |
| SHELL-004 | Persistent tab selection | Implemented / Provisional | `tab-state-stage37.js` | Exact persistence rule needs verification. |
| SHELL-005 | Responsive mobile navigation and bounded content | Accepted / Implemented | mobile stage assets | iPhone Safari is a release gate. |
| SHELL-006 | Global KPIs for rank, score, gaps, bank and team value | Accepted / Implemented | `core-boot.js` | KPI values must use the same live/projected scoring contract as matrices. |

## Transfer decision

| ID | Capability | Intended status | Baseline evidence | Notes |
|---|---|---|---|---|
| TRN-001 | Authoritative preferred recommendation | Accepted / Implemented | `decision_synthesis.py`, transfer UI layers | Must expose evidence and uncertainty. |
| TRN-002 | Hold/roll as a selectable working choice | Accepted / Implemented | reconciliation document, roll-choice script | Clears tentative route; does not erase confirmed history. |
| TRN-003 | Compare multiple budget- and club-valid routes | Accepted / Implemented | transfer route scripts, simulation data | Detailed legality contract pending. |
| TRN-004 | Lower variance, leverage, ownership and outgoing-player evidence | Accepted / Implemented | reconciliation document | Terms require glossary and canonical thresholds. |
| TRN-005 | Select a route and project it across every view | Accepted / Implemented | working-plan and effective-squad scripts | One effective-squad service is required in rebuild. |
| TRN-006 | Plan more than one transfer and account for free transfers/hits | Accepted / Implemented | multi-transfer tests, portfolio scripts | Golden scenarios required. |
| TRN-007 | Confirm that a real transfer has been executed | Accepted / Implemented | `executed-plan-stage124.js`, `declared_transfers.json` | Declared action is authoritative locally until official API catches up. |
| TRN-008 | Distinguish recommendation, working choice, declared action and official transfer | Accepted gap | current overlay exists but terminology is distributed | Requires explicit state machine and visual treatments. |
| TRN-009 | Preserve replaced recommendations for historical review | Accepted / Implemented | recommendation and decision history datasets | Must never continue presenting the old route as the active instruction. |
| TRN-010 | Current declared GW6 transfer: Kinsky out, Tzolakis in | Historical current-state evidence | `data/declared_transfers.json`, `data/latest.json` | This is mutable user data, not a permanent product rule. |

## Pick Team

| ID | Capability | Intended status | Baseline evidence | Notes |
|---|---|---|---|---|
| TEAM-001 | Recommend a legal XI and formation | Accepted / Implemented | Pick Team scripts, rules tests | Formation constraints must live in rule spec. |
| TEAM-002 | Captain, vice-captain and bench order | Accepted / Implemented | captaincy model/review and UI | Separate recommendation from submitted/official picks. |
| TEAM-003 | Apply the working or declared transfer before selection | Accepted / Implemented | effective-squad projection | Must use the same effective squad as all other views. |
| TEAM-004 | Explain marginal starter and bench decisions | Accepted / Implemented | pitch rationale layers | Explanation inputs must match scoring inputs. |
| TEAM-005 | Show whether incoming player starts or is benched | Accepted / Implemented | transfer-outcome script | Avoid implying immediate XI benefit when none exists. |
| TEAM-006 | Rich pitch view plus compact, accessible fallback | Accepted / Implemented | pitch scripts/styles | Responsive contract pending. |

## Squad strategy and planning

| ID | Capability | Intended status | Baseline evidence | Notes |
|---|---|---|---|---|
| SQD-001 | Position spend, bench value, club concentration and flags | Accepted / Implemented | squad intelligence | Derived field contracts pending. |
| SQD-002 | Six-gameweek fixture outlook and fixture cliffs | Accepted / Implemented | player pool, path and schedule datasets | Canonical horizon currently six GWs. |
| SQD-003 | Decision timeline for team, captaincy and transfer pressure | Accepted / Implemented | reconciliation document | Needs page contract. |
| SQD-004 | Chip window evaluation and comparison | Accepted / Implemented | chip datasets and UI | Authoritative versus challenger results must be labelled. |
| SQD-005 | Wildcard/Free Hit optimisation and TC/Bench Boost paths | Implemented / Provisional | optimiser and chip simulation datasets | Computational and product promotion rules require documentation. |
| SQD-006 | Fixture calendar intelligence for blanks/doubles | Accepted / Implemented | fixture workflow/data | Confidence and confirmed/potential distinction required. |

## Player pool and research

| ID | Capability | Intended status | Baseline evidence | Notes |
|---|---|---|---|---|
| PLY-001 | Search, position filtering and sorting | Accepted / Implemented | player pool UI | Mobile result count must remain bounded. |
| PLY-002 | Model, fixtures, minutes, value, ownership, Scout and Market factors | Accepted / Implemented | `player_pool.json` and UI | Every factor needs source/freshness metadata. |
| PLY-003 | Profiles: start now, medium-term, differential, value, watch, minutes risk | Accepted / Implemented | reconciliation document | Thresholds pending. |
| PLY-004 | Mark current squad, working-plan in and out | Accepted / Implemented | squad badges layers | Add declared/official distinction. |
| PLY-005 | Price rise/fall and timing pressure | Accepted / Implemented | market data/UI | Must avoid false precision. |
| PLY-006 | Midweek/international minutes, rating, goals, assists and injuries between GWs | Accepted gap | schedule-load data partially covers minutes | Rating/event/injury presentation and source contract not yet proven complete. |
| PLY-007 | Press conference and scout corroboration | Accepted / Implemented | dedicated workflows/data | Source failure must degrade visibly. |

## League intelligence

| ID | Capability | Intended status | Baseline evidence | Notes |
|---|---|---|---|---|
| LG-001 | Standings, nearest target and gap to leader | Accepted / Implemented | latest data and intel UI | Live versus official ranks must be explicit. |
| LG-002 | Threat, shield, neutral and leverage classification | Accepted / Implemented | exposure semantics | Canonical thresholds require rule spec. |
| LG-003 | Manager ownership/player matrix | Accepted / Implemented | league matrix scripts | Includes starters, captaincy, bench and fixture progress. |
| LG-004 | Recent rank and points trend | Accepted / Implemented | history data and trend UI | Trend period and missing history rules pending. |
| LG-005 | Rival strategy posture | Accepted / Implemented | strategy scripts | Protect/balanced/controlled chase/chase thresholds pending. |
| LG-006 | Effective squad reflected in rival comparison | Accepted / Implemented | reconciliation document | Tentative and declared actions need distinct markings. |
| LG-007 | Live player points and eventual autosub impact in manager matrix | Accepted gap / Partially implemented | live snapshot, matrix layers | The same projected points must feed KPIs and matrix. |

## Live gameweek

| ID | Capability | Intended status | Baseline evidence | Notes |
|---|---|---|---|---|
| LIVE-001 | Scheduled live snapshot generation | Accepted / Implemented | `live_gameweek.py`, workflow | Refresh cadence depends on phase. |
| LIVE-002 | Live score, overall total and mini-league rank | Accepted / Implemented | `live_gameweek.json` | Calculated versus official must be labelled. |
| LIVE-003 | Player states: upcoming, live and completed | Accepted / Implemented | live calculation and UI | State vocabulary becomes canonical. |
| LIVE-004 | Current score shown for live players | Accepted gap / Partially implemented | live picks contain points; recent UI request | Verify all player presentations. |
| LIVE-005 | Threats, leverage, damage and recent swings | Accepted / Implemented | live snapshot fields | Exact definitions pending. |
| LIVE-006 | Project valid autosubs only after a starter is a confirmed DNP | Accepted / Implemented in backend | `apply_projected_autosubs` and tests | Never guess DNP while a fixture remains upcoming. |
| LIVE-007 | Project captain to vice-captain when conditions are satisfied | Accepted / Implemented in backend | live calculation | Golden cases required. |
| LIVE-008 | Incorporate projected bench points into forward-looking KPI and manager matrix | Accepted gap | recent accepted iteration | Must retain a separate official/raw total. |
| LIVE-009 | Consistent fixture-state colours across cards, matrix, graphs and progress pills | Accepted gap / Partially implemented | status palette and recent iteration | Live = cyan. Completed must be clearly distinct and solid; upcoming remains unfilled/neutral. |
| LIVE-010 | Provisional and officially finalised states | Accepted / Implemented | live snapshot | UI wording and rollover behaviour pending. |
| LIVE-011 | Preserve previous snapshot to explain score/rank swings | Implemented | live backend fields | Retention and reset rules pending. |

## Between-gameweek monitoring

| ID | Capability | Intended status | Baseline evidence | Notes |
|---|---|---|---|---|
| BTW-001 | Consolidated monitoring view between deadlines | Accepted / Implemented | monitoring and between-games scripts | Page-level hierarchy needs specification. |
| BTW-002 | Positive/negative trend over time | Accepted gap / Partially implemented | history/signals and user iteration | Trend baseline must be named. |
| BTW-003 | Surface actions required, watch items, wins and changes | Accepted / Implemented | monitoring/decision signal layers | Avoid repeating identical panels. |
| BTW-004 | Show time since last event and next relevant fixture/deadline | Accepted gap / Partially implemented | schedule/deadline data | Exact placements pending. |
| BTW-005 | Merge graphs and detail where it reduces duplication | Accepted design direction | recent iteration | Must be captured in page wireframe, not applied blindly. |

## Data, history and operations

| ID | Capability | Intended status | Baseline evidence | Notes |
|---|---|---|---|---|
| OPS-001 | Main ETL every 30 minutes | Implemented | `fpl-etl.yml` | Target cadence needs cost/freshness review. |
| OPS-002 | Live-gameweek refresh workflow | Implemented | `live-gameweek.yml` | Exact phase gating to document. |
| OPS-003 | Decision Twin every 15 minutes | Implemented | `decision-twin.yml` | Rebuild may consolidate schedules. |
| OPS-004 | Separate press, fixture, simulation, stability and benchmark jobs | Implemented | workflows | Target orchestration and race handling need architecture spec. |
| OPS-005 | Jobs commit generated JSON to `main` | Implemented / Architecture review required | workflow commit steps | Functional but creates concurrent-writer complexity. |
| OPS-006 | Retry push races after rebase | Implemented | workflows | Operational mitigation, not necessarily target design. |
| OPS-007 | Archive completed gameweeks and recommendation history | Accepted / Implemented | history directory and archive scripts | Retention schema pending. |
| OPS-008 | Last refresh, age and failure visibility | Accepted gap / Partially implemented | freshness UI | Distinguish source time, pipeline time and UI fetch time. |
| OPS-009 | Last known-good data survives a failed refresh | Accepted | implicit current architecture | Must become explicit contract/test. |

## Retired mechanisms

These are historical implementation approaches and must not be recreated merely
to reproduce the current code structure:

- self-triggering or unbounded `MutationObserver` behaviour;
- recursive plan-change event loops;
- automatic background local-storage backfills;
- transfer-uplift persistence loops;
- duplicate secondary-data loaders;
- eager full-season/all-player rendering on first paint;
- a chain of numbered patch files as the target rebuild architecture.

## Inventory gaps to resolve next

1. Define the exact default landing tab for each gameweek phase.
2. Inventory every displayed KPI and assign a canonical producer.
3. Reconcile live/projection field names across `latest.json` and
   `live_gameweek.json`.
4. Capture exact state palette tokens and accessibility contrast.
5. Map every generated JSON artefact to producers and UI consumers.
6. Separate accepted modelling features from experimental challengers.
7. Convert the accepted gaps above into page specifications and acceptance tests.
