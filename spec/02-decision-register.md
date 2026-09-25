# Decision Register

This register records product and architecture choices that a clean-room rebuild
must preserve or explicitly revisit. It prevents later implementation work from
quietly reversing decisions made during iteration.

## Accepted decisions

| ID | Decision | Rationale / consequence |
|---|---|---|
| DEC-001 | Use a collection of linked specifications, contracts and tests rather than one master prompt. | Keeps LLM implementation slices bounded and prevents contradictions from being hidden in a long prompt. |
| DEC-002 | The current application is evidence, not the sole specification. | The baseline contains historical stage layers, superseded mechanisms and partial implementations. |
| DEC-003 | A user-declared executed transfer immediately changes the effective squad locally. | The official FPL API may not expose the permanent move until the next deadline; the app must remain useful in that interval. |
| DEC-004 | Preserve separate truth states for official, calculated live, projected eventual and modelled values. | Combining these values makes KPIs and league comparisons misleading. |
| DEC-005 | Project an autosub only when the outgoing player's fixture is complete and minutes are zero. | An upcoming player is not a confirmed DNP. |
| DEC-006 | Projected autosubs must obey goalkeeper matching, bench priority and legal formation constraints. | Mirrors FPL substitution rules and avoids impossible projected totals. |
| DEC-007 | Forward-looking totals may include a valid projected bench substitution, but official/raw totals remain available and labelled. | Terry wants the likely eventual score while retaining auditability. |
| DEC-008 | Live fixture state is cyan everywhere it appears. | Cross-view consistency allows rapid scanning. |
| DEC-009 | Completed and live states must be visually unmistakable; completed progress pills are solid and upcoming/non-completed pills remain visibly unfilled or neutral. | Earlier live/completed colours were too similar. |
| DEC-010 | KPI totals, manager matrix totals and player-level points use the same canonical scoring output. | Prevents mismatched views of the same manager/gameweek. |
| DEC-011 | Mobile/iPhone Safari stability is a release requirement, not optional polish. | The application is frequently used live on mobile. |
| DEC-012 | Heavy player, rival and history data is lazy-loaded or otherwise bounded. | Protects first paint and mobile DOM stability. |
| DEC-013 | Saved-plan writes occur only following explicit user action. | Avoids unsafe loops and accidental state mutation. |
| DEC-014 | All data freshness states identify what was refreshed and when. | A pipeline timestamp, source timestamp and browser fetch time are not interchangeable. |
| DEC-015 | A failed refresh retains the last valid snapshot and shows degraded freshness. | Failure should not replace usable data with a broken or empty view. |
| DEC-016 | The target rebuild uses cohesive modules/components, not the historical numbered stage-file structure. | The stage files document evolution but should not define the new architecture. |
| DEC-017 | Current player, club, price and squad facts are data-driven and never permanently hard-coded into UI logic. | Football state changes continuously. |
| DEC-018 | Every implementation slice must identify requirements, contracts, tests and non-goals before code changes. | Enables deterministic LLM delivery and controlled review. |

## Provisional decisions

| ID | Direction | Validation needed |
|---|---|---|
| DEC-P01 | Retain five primary tabs and treat live/between-gameweek experiences as phase-aware layers rather than additional permanent tabs. | Confirm after page hierarchy and mobile navigation are mapped. |
| DEC-P02 | Use a single effective-squad domain service for official squad plus working/declared overlays. | Confirm target framework and persistence boundary. |
| DEC-P03 | Consolidate scheduled analysis behind one orchestrated pipeline with dependent stages. | Compare with the resilience and cadence benefits of current independent workflows. |
| DEC-P04 | Treat Decision Twin and challenger simulations as explainability/advisory modules, not primary domain sources. | Classify which model output is authoritative for each decision surface. |
| DEC-P05 | Keep a six-gameweek default planning horizon. | Confirm whether chip planning needs a longer separate horizon. |

## Open decisions

| ID | Question | Why it matters | Needed by |
|---|---|---|---|
| DEC-O01 | Which tab is the canonical landing view in each phase? | Current markup and navigation order do not express one unambiguous rule. | Page specifications |
| DEC-O02 | Should projected totals replace or sit beside calculated-live totals in headline KPIs? | Affects labels, space and user trust. | Live scoring spec |
| DEC-O03 | How should declared transfers be corrected or withdrawn before official confirmation? | Required for safe state management after a mistaken declaration. | Transfer workflow spec |
| DEC-O04 | What exact visual colour represents completed fixtures? | It must be distinct from cyan live and pass contrast checks. | Design tokens |
| DEC-O05 | What external source provides midweek match ratings? | Minutes, goals and assists may be sourced differently from subjective ratings. | Source register |
| DEC-O06 | Which generated model outputs are authoritative versus experimental challengers? | Prevents competing recommendations from confusing the UI. | Data/source contracts |
| DEC-O07 | Should the clean rebuild remain a static GitHub Pages application or adopt an API/backend? | Determines authentication, persistence, refresh and deployment architecture. | Architecture specification |
| DEC-O08 | Should generated snapshots continue to be committed to `main`? | Current jobs can race and mix source code with frequently changing runtime data. | Architecture/operations spec |

## Known conflicts or ambiguities

| ID | Evidence | Conflict | Required treatment |
|---|---|---|---|
| CON-001 | `docs/index.html` navigation begins with League Intel while Transfer view markup starts active. | Default landing behaviour is distributed across later scripts. | Resolve in DEC-O01; do not copy incidental DOM defaults. |
| CON-002 | `REQUIREMENTS_RECONCILIATION.md` says no MutationObserver in the recovered production path, but `render-coordinator-stage72.js` uses a bounded observer. | Historical document predates or generalises a later bounded stabilisation mechanism. | Preserve the product constraint (no self-triggering/unbounded observer); target architecture should not require DOM observation for normal rendering. |
| CON-003 | `data/latest.json` was generated on 2026-09-24 while `data/live_gameweek.json` represents GW4 live state from 2026-09-12. | Live data is intentionally phase-specific but can look stale if consumed without phase checks. | State model must gate live artefacts by GW and freshness. |
| CON-004 | UI features are implemented across many ordered script layers that can override earlier output. | File presence does not prove the final visible behaviour. | Page specs and browser verification must capture final behaviour. |
| CON-005 | “Confirmed” is used colloquially for a user-executed transfer while the stored status is `pending_official_api`. | Confirmation source is ambiguous. | Use `declared_executed` for local truth and `official_confirmed` for API truth in the new contract. |

## Retired decisions

| ID | Retired approach | Replacement intent |
|---|---|---|
| RET-001 | Recursive plan-change events and automatic persistence loops | Explicit command followed by one-way state update and render |
| RET-002 | Automatic local-storage backfill as an authoritative history mechanism | Versioned decision/history contracts |
| RET-003 | Eager full player and league rendering | Bounded/lazy queries and progressive disclosure |
| RET-004 | Reproducing numbered stage patches in a clean build | Cohesive domain and UI modules |

## Decision change protocol

When changing an accepted decision:

1. Add the replacement decision with a new ID.
2. Mark the old decision superseded; do not delete it.
3. Link the affected requirements and contracts.
4. Update or add acceptance/golden tests.
5. Record the migration effect on stored user state and historical snapshots.
