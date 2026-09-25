# Product Vision

## Product statement

The FPL Decision Centre is Terry's personal decision-support and live-monitoring
application for Fantasy Premier League. It combines official FPL data, mini-league
context, modelled outcomes, research signals and Terry's confirmed actions into one
coherent operational view.

It should answer three questions without requiring Terry to reconcile separate
screens manually:

1. **What should I do next, and why?**
2. **What is happening to my team and mini-league now?**
3. **What changed, what requires attention, and what can wait?**

## Primary user

The primary user is a single engaged FPL manager using the application frequently
on an iPhone and secondarily on desktop. The product is optimised for decision
quality and rapid comprehension rather than generic multi-tenant configuration.

## Core operating cycle

The application follows a repeating gameweek lifecycle:

1. **Between gameweeks** — reconcile the last outcome, monitor minutes, injuries,
   price pressure and research, and identify decisions that may become actionable.
2. **Approaching deadline** — compare transfer routes, choose hold/roll or one or
   more transfers, select the XI, captain, vice-captain and bench order.
3. **Locked / awaiting reveal** — preserve the submitted plan while clearly
   distinguishing it from verified official picks.
4. **Live gameweek** — track provisional points, players in progress, completed
   players, threats, leverage, autosub implications and mini-league movement.
5. **Completed / awaiting official processing** — project valid autosubs and
   captaincy changes without presenting them as official prematurely.
6. **Finalised** — reconcile projections with official outcomes, archive the week
   and carry learning into the next decision cycle.

## Product principles

### One coherent answer

Each important concept has one canonical calculation and semantic meaning across
KPIs, player views, manager matrix and charts. A screen may present the value
differently, but it must not independently recalculate it.

### Truth states are explicit

The product distinguishes:

- official FPL data;
- locally calculated live data;
- projected eventual outcomes;
- model forecasts;
- user-declared actions awaiting official API confirmation.

These states must be named in contracts and visible when ambiguity would affect a
decision.

### Current action overrides stale recommendation context

Once Terry records that a transfer has been executed, the effective squad and all
dependent views use that declared action immediately. The former recommendation
remains historical evidence, not the active instruction.

### Phase-aware, not page-static

Priority and wording adapt to the gameweek phase. During live play, current points,
remaining players and rank movement take priority. Between gameweeks, monitoring,
freshness and upcoming decisions take priority.

### Dense but calm

The interface should expose deep evidence progressively. The first viewport should
answer the immediate question; detailed evidence remains available without making
the main view noisy or repetitive.

### Mobile stability is a product requirement

iPhone Safari first paint, bounded DOM growth and reliable navigation are part of
correctness. A feature that destabilises the mobile experience is incomplete.

### Freshness is visible

Users can tell when data was generated, what it covers, whether it is stale and
whether a failed job has left the application using the last successful snapshot.

## Primary product areas

| Area | Primary answer |
|---|---|
| League Intel | Where do I stand, who matters and what will move the contest? |
| Transfer | Should I hold, roll or transfer, which route is best, and why? |
| Pick Team | What is the legal, effective XI, captaincy and bench order? |
| Squad Strategy | What structural strengths, risks and future fixture pressures exist? |
| Player Pool | Which alternatives are credible under model, fixture, minutes and value evidence? |
| Live Gameweek | What is happening now, including provisional and projected consequences? |
| Between-Games Watch | What changed since the last deadline and what needs monitoring? |
| Operations/Freshness | Can I trust the displayed data and scheduled analysis? |

## In scope

- Official squad, picks, fixtures, standings, player and price data.
- User-declared transfers pending official confirmation.
- Transfer route comparison, hold/roll and multi-transfer planning.
- Legal XI, formation, captain, vice-captain and bench order.
- Mini-league standings, ownership, threats, shields and leverage.
- Live and projected scoring, including legal autosub and captaincy effects.
- Multi-gameweek planning, chips, fixture calendars and scenario modelling.
- Research, press conference, workload, availability and market signals.
- Historical snapshots, decision journal, recommendation history and review.
- Scheduled generation, freshness monitoring and recoverable failure states.

## Non-goals for the rebuild

- Reproducing every historical JavaScript stage file or implementation mechanism.
- Treating a recommendation as an autonomous transfer executor.
- Hiding uncertainty behind a single unexplained score.
- Rendering the entire player/manager/history universe eagerly on mobile.
- Using conversation history as a runtime dependency.

## Rebuild success criteria

A clean-room implementation is successful when:

1. Golden datasets produce the expected official, calculated and projected totals.
2. Every accepted feature maps to a page/component and an acceptance test.
3. The effective squad is consistent across all views after a declared action.
4. Live, completed, upcoming and projected states are visually unambiguous.
5. A stale or failed data source is visible and does not corrupt the last valid view.
6. The critical mobile workflows operate reliably on iPhone Safari.
7. A new LLM can implement or change one feature using only the relevant spec slice,
   contracts and tests without reconstructing product intent from old code.
