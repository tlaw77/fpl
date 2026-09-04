# FPL Decision Twin v1 - Build and Operations Runbook

## Outcome

Turn the existing FPL Decision Centre into a self-challenging decision service. The Decision Twin must publish one auditable decision certificate, show structured disagreement between specialist perspectives, identify the evidence that would change the recommendation, and preserve a frozen evaluation contract for later learning.

This version uses the existing repository, public/free data and current Football Scout evidence. It introduces no paid dependency and does not make transfers automatically.

## Completion gauge

| Gate | Weight | Evidence | Status |
| --- | ---: | --- | --- |
| Contract and runbook | 10% | This document defines inputs, outputs, validation and recovery | Complete |
| Decision certificate | 20% | `data/decision_twin.json` contains one authoritative, traceable recommendation | Complete |
| Specialist council | 20% | Quant, rival, scout, risk, chip and chair perspectives are published | Complete |
| Change radar | 15% | Machine-readable breakers and change detection are published | Complete |
| Learning contract | 15% | Decision, XI, captain, alternatives and target GW are frozen for review | Complete |
| Pipeline and mobile UI | 20% | Workflow validation and mobile rendering pass | Complete |

**Decision Twin v1: 100% complete when every acceptance check below passes.**

## Operating model

1. `fpl-etl.yml` refreshes official FPL, squad, market, player, Scout and simulation inputs.
2. `decision_synthesis.py` produces the authoritative engine recommendation.
3. `decision_twin.py` challenges and packages that recommendation; it does not silently override it.
4. The pipeline validates the certificate, council, radar and learning contract before committing data.
5. The browser loads `data/decision_twin.json` and renders the Twin card in the Transfer view.
6. On a later completed Gameweek, the existing archive/backtest path can score the frozen contract.

The core ETL, stability and press-conference workflows share the `fpl-decision-writers` concurrency group. They queue rather than cancel so only one job can update the shared Decision Twin snapshot at a time.

## Inputs

Required inputs:

- `data/latest.json`
- `data/decision_synthesis.json`
- `data/simulation.json`
- `data/path_simulation.json`
- `data/adaptive_rival_simulation.json`
- `data/chip_activation_gate.json`
- `data/captaincy_review.json`

Optional enrichment inputs degrade safely:

- `data/market.json`
- `data/scout_consensus.json`
- `data/press_conference_watch.json`
- `data/simulation_stability.json`
- `data/backtest_summary.json`

## Output contract

`data/decision_twin.json` must contain:

- `decision_certificate`: action, headline, confidence, current benefit, alternative, evidence freshness and rationale.
- `council`: six named perspectives, each with a verdict, confidence and concise argument.
- `council_summary`: agreement, disagreement and the chair's resolved position.
- `change_radar`: whether the decision changed and observable conditions that can trigger review.
- `learning_contract`: frozen target GW, XI, captain, alternative routes and calibration readiness.
- `progress`: a visible 0-100 implementation gauge.
- `what_if_prompts`: scenario questions grounded in available engine capabilities.

## Acceptance checks

Run from the repository root:

```bash
python decision_twin.py
python -m unittest tests/test_decision_twin.py
python -m json.tool data/decision_twin.json >/dev/null
```

The workflow additionally requires:

- status is `SUCCESS` and schema version is at least 1;
- completion is exactly 100%;
- exactly six council members with valid verdicts and bounded confidence;
- a non-empty certificate ID, action, headline, rationale and evidence timestamp;
- at least three decision-breaker conditions;
- an 11-player frozen XI and captain inside that XI;
- no secret, credential or paid-provider requirement;
- Transfer view remains usable at 390 px width;
- browser console has no Decision Twin error.

## Failure handling

- **Required input missing or invalid:** fail generation; preserve the last committed successful artifact.
- **Optional enrichment missing:** publish `unavailable` evidence state and reduce the relevant council confidence.
- **Models disagree:** show `CONTESTED`; the chair keeps the authoritative synthesis and names the disagreement.
- **New evidence changes action/headline:** set `change_radar.decision_changed` and publish before/after values.
- **UI fetch fails:** leave the existing Transfer view intact and show no empty placeholder.
- **Concurrent writer:** jobs queue under the shared concurrency group; do not restore independent writer groups.

## Recovery and rollback

1. Inspect the failing workflow and its validation message.
2. Run `python decision_twin.py` locally against the committed data snapshot.
3. Run the unit and JSON checks above.
4. If generation is faulty, revert only the Decision Twin commit; the existing synthesis remains authoritative.
5. If rendering is faulty, remove the two Decision Twin asset references from `docs/index.html`; backend output can continue safely.

## Ownership and decision rights

- The engine recommends; Terry makes the FPL action.
- `decision_synthesis.py` remains the authoritative action gate.
- The Twin explains, challenges, monitors and learns; it cannot invent an action unsupported by the engine.
- A chip status of `WATCH` or `CONSIDER` is not automatic activation.
- Public news is supporting evidence, never a substitute for official availability data.

## Future maturity gates

The learning layer becomes personalised only after completed evidence exists:

- 0-2 evaluable Gameweeks: collect contracts; do not tune.
- 3-5: show provisional calibration observations.
- 6-9: allow bounded weight suggestions.
- 10+: permit evidence-backed profile adjustments with an audit trail.

This prevents a modern interface from presenting premature learning as intelligence.
