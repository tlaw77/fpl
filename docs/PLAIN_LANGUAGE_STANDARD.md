# FPL Decision Centre — plain-language UI standard

Updated: 2026-08-29

## Principle

The interface is a decision tool, not a model diagnostics console.

Every user-facing section should answer in this order:

1. **What should I do?**
2. **Why?**
3. **How sure are we?**
4. **Technical detail**, only when it helps interpretation.

Internal model terminology can remain in JSON, logs and engineering documentation. It should not be the primary wording in the app.

## Preferred language

| Internal / technical wording | User-facing wording |
| --- | --- |
| action gate | recommendation threshold / worth acting on |
| measured leader | best alternative |
| model support | model agreement |
| persisted | stayed the same |
| plan stability | has the advice changed? |
| model robustness | how strong is the advice? |
| forward path | what could happen next? |
| provisional branch | possible future move |
| raw uplift | projected improvement |
| simulation points / sim pts | modelled points |
| proxy budget / bank | estimated budget / money left |
| structural weak asset | clear squad problem |
| activation signal | reason to use it now |
| preservation signal | reason to save it |
| season maturity | season data strength |
| deep model | full simulation |
| CV | forecast risk |
| score gap | gap to the best option |
| XI score | team-selection rating |

## Examples

Instead of:

> Immediate action persisted 100%. The measured transfer leader persisted 100%, but cleared the action gate in 0%.

Use:

> **The advice has stayed the same: HOLD.** The best alternative transfer keeps appearing, but it has not looked worth making.

Supporting detail can then say:

> Same advice in 3/3 meaningful checks. Best alternative was strong enough to act on in 0% of checks.

Instead of:

> No extra move clears the gate.

Use:

> **No extra transfer looks worth making.**

Instead of:

> Raw uplift +15.6 sim pts.

Use:

> **Projected improvement: +15.6 modelled points.**

## Implementation

`docs/production-copy-cleanup-stage28.js` is the final presentation guard. It:

- removes legacy stage/debug wording;
- translates known model jargon into plain English;
- applies to all dashboard views;
- re-runs after dynamic DOM updates so older stage scripts cannot easily reintroduce technical copy;
- preserves underlying numbers and calculations.

This guard is transitional protection. New components should follow this standard directly at source rather than relying on post-render translation.

## Scope

Applies to:

- League Intel
- Transfer
- Pick Team / This GW
- Pick Team / Outlook
- Squad Shape
- Player Pool
- captaincy and Triple Captain decisions
- Wildcard / Free Hit / Bench Boost presentation

Technical terminology remains appropriate in backend files, model notes, logs, validation output and engineering documentation.