# Data Source Register

## Source classes

| Class | Authority | Failure impact |
|---|---|---|
| Official FPL | Authoritative for FPL entities, deadlines, fixtures, squads, picks, transfers, points and standings | Core operational views degrade; last known good remains visible |
| User declaration | Authoritative for Terry's statement that an action was executed before official visibility | Effective next-GW squad uses the overlay; audit record must be retained |
| Deterministic internal | Authoritative only for the named derived rule/calculation | Affected derived surface degrades; raw source remains available |
| External research | Supporting evidence only | Recommendation confidence/evidence degrades; official views remain valid |
| Model/simulation | Advisory unless explicitly promoted by synthesis | Recommendation/model panel degrades; never corrupts official state |
| Historical snapshot | Authoritative for what the system knew at that recorded time | Review/backtest degrades; current operational state remains valid |

## External sources

| ID | Source | Current use | Authority and cautions | Freshness owner |
|---|---|---|---|---|
| SRC-FPL-BOOT | FPL `bootstrap-static` | Events, players, teams, positions, prices, availability, form and global ownership | Official current feed. Availability is reported data, not certainty. | Main ETL / phase-specific producers |
| SRC-FPL-FIX | FPL `fixtures` | Kickoffs, teams, difficulty, started/finished state, blanks/doubles | Official. `finished_provisional` is complete for fixture-state display but not necessarily event finalisation. | Deadline context, live, schedule/calendar jobs |
| SRC-FPL-LIVE | FPL `event/{gw}/live` | Player points, minutes and live statistics | Official current feed; provisional bonus/corrections can change. | Live gameweek job |
| SRC-FPL-PICKS | FPL `entry/{id}/event/{gw}/picks` | Submitted XI, bench, multipliers, captaincy, chip and hit context | Hide rivals before the deadline. Partial reveal is not a zero-score manager. | Live gameweek job |
| SRC-FPL-HIST | FPL entry history | Official event totals, transfers, chips and season history | Official after publication; current-event values can lag live calculations. | Main ETL / squad reconstruction |
| SRC-FPL-LEAGUE | FPL classic league standings | Rank, manager/team identity and totals | Official standings; during live play derive provisional rank separately. | Main ETL and live job |
| SRC-USER-TX | Explicit transfer declaration | Executed transfers not yet visible through FPL API | User-authoritative operational overlay, not official history. Must be reversible/correctable through an explicit command. | Transfer command handler |
| SRC-FOTMOB | FotMob data and match pages | Non-FPL club schedule and player-minute observations | Supporting third-party source; identifiers and access can change. Rating semantics are provider-specific. | Schedule-load job |
| SRC-FFSCOUT | Fantasy Football Scout pages | Scout consensus and chip/news context | Supporting editorial evidence; never overrides official state. | Scout/strategy jobs |
| SRC-PLNEWS | Premier League news | Supporting player/team news | First-party competition news but not the FPL scoring source. | Scout job |
| SRC-GNEWS | Google News RSS results | Press/news discovery | Aggregator. Article timestamp/source must be retained; deduplicate. | Scout/press jobs |
| SRC-REDDIT | r/FantasyPL search API | Community sentiment/evidence | Unverified supporting evidence only. | Scout job |

## Official endpoint requirements

Every capture of an official endpoint must record:

- endpoint/source identifier;
- target gameweek or entry where relevant;
- `source_captured_at_utc`;
- request success/failure;
- completeness/coverage where partial results are possible;
- source-specific identifiers used for joins.

Retries must not replace a last known good artifact with an empty or partial payload
unless the contract explicitly represents partial coverage.

## Generated artefact families

### Operational truth

| Contract | Current file | Producer | Primary consumers | Target classification |
|---|---|---|---|---|
| Core snapshot | `data/latest.json` | `fpl_etl.py` plus sequential enrichers | Global KPIs and most decision views | Split into smaller canonical contracts during rebuild |
| Current/effective squad | embedded in `latest.json` | `current_squad.py`, `declared_transfer_overlay.py` | Transfer, Pick Team, Squad Strategy, Player Pool | Canonical operational domain service |
| Live gameweek | `data/live_gameweek.json` | `live_gameweek.py` | Live command centre, manager matrix, live KPIs | Canonical live contract after schema revision |
| Declared transfers | `data/declared_transfers.json` | explicit user action/UI | Effective squad overlay and journal | Durable command/audit contract |
| Deadline/fixture context | embedded in `latest.json` | `deadline_context.py` | Phase choreography and monitoring | Canonical lifecycle contract |

### Deterministic derived intelligence

| Contract | Current file | Producer | Notes |
|---|---|---|---|
| Budget state | `data/budget_state.json` | `budget_state.py` | Selling-price reconstruction can carry confidence, not always exact |
| Squad intelligence | `data/squad_intelligence.json` | `squad_intelligence.py` | Includes manager comparison and live enrichment |
| Market watch | `data/market.json` | `market_watch.py` | Price movement/timing, not guaranteed future changes |
| Schedule load | `data/schedule_load.json` | `schedule_load.py` | Mixes FPL and third-party match/minute evidence |
| Player pool | `data/player_pool.json` | `player_pool.py` | Six-GW ranked evidence; inputs must be versioned |
| Fixture calendar | `data/fixture_calendar_intelligence.json` | `fixture_calendar_intelligence.py` | Must separate confirmed from potential blanks/doubles |
| Rules audit | `data/rules_edge_audit.json` | `rules_edge_audit.py` | Coverage evidence, not runtime rule implementation itself |
| Current outcomes | `data/current_player_outcomes.json` | `current_player_outcomes.py` | Event/player observation for review |

### Research and supporting evidence

| Contract | Current file | Producer | Notes |
|---|---|---|---|
| Scout consensus | `data/scout_consensus.json` | `scout_consensus.py` | Optional supporting evidence |
| Press conference watch | `data/press_conference_watch.json` | `press_conference_watch.py` | Optional and time-sensitive |
| Strategy watch | `data/strategy.json` | `strategy_watch.py` | Mix of official chip context and editorial research |
| Post-window review | `data/post_window_review.json` | `post_window_review.py` | Historical comparison across player-pool snapshots |
| Elite benchmark | `data/elite_benchmark.json` | `elite_benchmark.py` | Cohort definition and sample size must remain visible |

### Model and recommendation outputs

| Contract | Current file | Producer | Authority |
|---|---|---|---|
| Route simulation | `data/simulation.json` | `simulation_engine_v2.py` | Model candidate evidence |
| Multi-GW path simulation | `data/path_simulation.json` | `path_simulation_v3.py` | Model candidate evidence |
| Adaptive rival simulation | `data/adaptive_rival_simulation.json` | `adaptive_rival_simulation_v2.py` | Challenger/model evidence |
| Chip path simulation | `data/chip_path_simulation.json` | `chip_path_simulation_v2.py` | Model evidence |
| Full-squad chip optimiser | `data/full_squad_chip_optimizer.json` | `full_squad_chip_optimizer_v2.py` | Model evidence, legality must be independently validated |
| Authoritative synthesis | `data/decision_synthesis.json` | `decision_synthesis.py` | Promoted recommendation gate |
| Decision Twin | `data/decision_twin.json` | `decision_twin.py` | Explain/challenge package; does not override synthesis |
| Stability review | `data/simulation_stability.json` | `simulation_stability.py` | Confidence/support evidence |
| Captaincy review | `data/captaincy_review.json` | `captaincy_review.py` | Specialist recommendation |
| Chip activation gate | `data/chip_activation_gate.json` | `chip_activation_gate.py` | Specialist hard/soft gate |
| Triple-captain review | `data/triple_captain_review.json` | `triple_captain_review.py` | Specialist recommendation |
| Calendar challenger | `data/chip_calendar_challenger.json` | `chip_calendar_challenger.py` | Explicit challenger only |
| Medium-term unlock | `data/path_simulation_unlock.json` | `path_simulation_v4.py` | Explicit challenger only |

### History and learning

| Contract | Current file/path | Producer | Immutability expectation |
|---|---|---|---|
| Recommendation history | `data/recommendation_history.json` | `recommendation_history.py` | Append/supersede, do not rewrite decision-time evidence |
| Decision history | `data/decision_history.json` | `decision_journal.py` | Durable audit record |
| Signal history | `data/decision_signal_history.json` | `decision_signal_history.py` | Append snapshots with version |
| Gameweek archive | `data/history/gw*/` | `archive_week.py` | Frozen after correction window; corrections are traceable |
| Backtest summary | `data/backtest_summary.json` | `backtest_engine.py` | Derived from frozen histories |
| Elite history | `data/elite_history.json` | `elite_benchmark.py` | Append snapshots |

## Current pipeline risks to preserve in architecture decisions

1. `latest.json` is mutated sequentially by multiple scripts, so its schema ownership
   is distributed.
2. Independent workflows commit generated runtime data into Git branches, creating
   concurrent-writer and freshness complexity.
3. Optional external research can fail or change structure; it must never block
   official/live truth.
4. The browser reads live data from `live-data` with `main` fallback. GW/applicability
   checks are mandatory before merging the fallback.
5. Current contracts use inconsistent timestamps and truth-state labels.

## Target source policy

- Official FPL data is the only source for game rules, scoring facts and official
  entry state.
- External sources enrich availability, workload and research but cannot silently
  mutate official values.
- Every model output names its input versions, horizon and authority level.
- Every UI consumer reads from a canonical contract or selector, never from several
  files with competing calculations.
- A contract remains usable without optional enrichment and explicitly lists which
  evidence is unavailable.
