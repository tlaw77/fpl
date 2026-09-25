# Design System

## Intent

The Decision Centre is a dense, dark operational interface. Colour communicates
state and consequence; it is not decoration. The design must remain readable at a
390px viewport and usable in a live, frequently refreshed context.

## Semantic state palette

The semantic role is accepted. Exact reference values below reflect the current
baseline and can be adjusted only after contrast and visual verification.

| Token | Reference | Meaning | Required treatment |
|---|---:|---|---|
| `state.live.fg` | `#22d3ee` | Fixture/player currently live | Cyan border/accent; optional restrained pulse on a small indicator only |
| `state.live.bg` | `#102c42` | Live surface | Dark cyan background; never use amber for live |
| `state.complete.fg` | `#94a3b8` | Fixture/player complete | Distinct slate; solid, static treatment |
| `state.complete.bg` | `#182334` | Completed surface | Filled surface, no glow or pulse |
| `state.upcoming.fg` | `#a78bfa` | Future/pending fixture | Outline or restrained purple accent |
| `state.upcoming.bg` | `#201f46` | Upcoming context | Do not visually fill progress as though complete |
| `state.unknown.fg` | `#64748b` | State unavailable | Neutral and explicitly unknown when material |
| `role.captain` | `#f59e0b` | Captaincy marker | Small orange `C`; does not replace fixture-state colour |
| `impact.favourable` | `#34d399` | Positive consequence/performance | Green; never used solely to mean complete |
| `impact.risk` | `#fb7185` | Negative consequence/risk | Rose/red |
| `impact.mixed` | `#f59e0b` | Mixed/watch | Amber |
| `impact.neutral` | `#94a3b8` | Neutral/context | Slate |

### State versus performance

Fixture state and performance are separate dimensions. A completed player who
scored poorly remains **complete slate** at the state boundary; a score cell may
also carry a low-performance treatment inside it. A live player remains **live
cyan** regardless of whether their current points are good or bad.

### Progress pills

- live: cyan filled/accented, with a restrained active indicator;
- complete: solid slate fill;
- upcoming/remaining: transparent or dark fill with purple/neutral outline;
- unknown: neutral outline with no implication of progress.

The same mapping applies in the personal score strip, manager matrix, fixture
labels, graphs and progress indicators.

## Surfaces and hierarchy

| Level | Use |
|---|---|
| Page canvas | Darkest background; no state meaning |
| Primary card | Major decision/score area |
| Secondary card | Supporting evidence or comparison |
| Selected card | Explicit border and label such as `Your choice`; selection is not inferred from colour alone |
| Warning card | Amber/red semantic border plus text label |
| Live card | Cyan semantic border/background, never a generic selection colour |

## Typography

- Use a compact system sans-serif stack for fast rendering.
- Page title: one concise operational statement.
- Eyebrow: uppercase category label; never the only accessible heading.
- KPI value: largest item inside a KPI, tabular numerals preferred.
- Supporting copy: plain language and shorter than the evidence it introduces.
- Avoid text smaller than the verified mobile readability floor. The current app
  contains 6–8px labels; the rebuild must validate or increase them rather than
  copying them automatically.

## Density and progressive disclosure

1. First viewport answers the phase's immediate question.
2. Comparison and evidence follow.
3. Methodology and model detail are collapsed or secondary.
4. Repeated panels with the same answer are consolidated.
5. Horizontal scrolling is permitted inside bounded matrices only, never at page
   level.

## Motion

- Motion indicates active live state or a recent score change.
- Pulse only a small state dot/border, not entire cards or rows.
- Respect `prefers-reduced-motion` by removing pulses and animated transitions.
- Refresh must not reorder content unexpectedly while the user is interacting.

## Accessibility

- Never communicate live/complete, good/bad or selected/unselected by colour alone.
- Provide text, icon, border/fill and accessible labels.
- Interactive targets should be at least 44px on touch devices even when visual
  controls appear compact.
- Preserve keyboard focus and expanded states after background refresh.
- Manager matrices require accessible cell labels naming manager, player, state,
  raw points, counted points and captain/bench status.
- Contrast must meet WCAG AA for normal text and meaningful graphical boundaries.

## Responsive rules

### Mobile, up to 560px

- One-column cards except deliberately paired compact summaries.
- KPI row may use two or four compact columns only if labels remain readable.
- Player strips may scroll horizontally inside their own region.
- Manager names and player names truncate with an accessible full label.
- Details expand vertically; page-level horizontal overflow is prohibited.

### Tablet, 561–900px

- Two-column evidence panels when content density allows.
- Maintain touch-sized controls.

### Desktop, above 900px

- Use two-column comparison and wider matrices.
- Do not increase information repetition merely because space is available.

## Design acceptance checks

- Screenshot comparison at 390px, 768px and 1440px.
- No page-level horizontal overflow at 390px.
- State legend agrees with actual component tokens.
- Live and complete remain distinguishable in grayscale and common colour-vision
  simulations through fill/border/text differences.
- Reduced-motion mode contains no pulsing indicators.
