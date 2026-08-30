# FPL Decision Centre — Plain-language copy rule

All user-facing wording must be understandable to a normal FPL manager without knowledge of the model implementation.

## Core rule

**Layman first, technical detail second.** Backend/data field names may stay technical. UI labels, explanations, tooltips and recommendation text must translate them into everyday FPL language.

Every important decision phrase should answer, in this order:
1. **What should I do?**
2. **Why?**
3. **How strong is the evidence?**
4. **What would make the answer change?**

Keep the first sentence short enough to scan on a phone.

## Preferred wording

| Avoid in UI | Prefer |
| --- | --- |
| activation-adjusted uplift / activation evidence | realistic current estimate / current evidence |
| raw scout / raw optimiser | best-case model view |
| counterfactual | what-if view |
| robustness hurdle | minimum edge needed |
| portfolio inflection | latest safe chip start |
| portfolio pressure | chip timing pressure |
| adaptive scenario/model | scenario allowing for rival moves / rival-move model |
| rank drag from rival reactions | effect of rivals making good moves |
| league leverage | mini-league context |
| season maturity | amount of season evidence available |
| squad churn | number of player changes |
| budget confidence | budget certainty |
| Wildcard squad persistence | how often the same Wildcard squad stays best |
| simulation points / sim pts | modelled points |
| gain-place chance | chance of moving up |
| expected league position | average projected league position |

## Numbers

Always say what a number represents. Do not display a model number as if it were guaranteed FPL points.

Examples:
- `+4.5 modelled points over six GWs`, not `+4.5 points`.
- `75% chance of moving up at least one league place`, not `75% gain-place chance`.
- `Average projected position: 6.1`, not `expected rank 6.1`.

## FPL abbreviations

GW is acceptable throughout. FT, WC, FH, BB and TC may be used in compact areas, but the nearby section should make the meaning obvious. Prefer full wording when space allows.

## Recommendation hierarchy

The UI should not make users decode competing model layers. The authoritative recommendation is stated once. Supporting model outputs are evidence and must be phrased as evidence, not as separate instructions.

When technical diagnostics are useful, keep them in data/debug output or place them after the plain-language explanation rather than leading with them.
