# Requirements Traceability Matrix

This baseline maps accepted capability groups to their controlling specification,
target contract/component and verification. Detailed code paths are added as rebuild
slices land.

| Feature IDs | Controlling spec | Target contract/selector | Page/component | Verification |
|---|---|---|---|---|
| SHELL-001–006 | lifecycle, page contracts, design system | `fpl.lifecycle`, shell selectors | header, nav, KPI, freshness | ACC-SHELL-001–004, GOLD-PHASE/UI |
| TRN-001–006 | product vision, truth taxonomy, page contracts | recommendation, route and effective-squad selectors | decision hero, route comparison | ACC-TRN-001, 005–006 |
| TRN-007–010 | truth taxonomy, contract index | `fpl.action-ledger`, `fpl.effective-squad` | action control, current action state | ACC-TRN-002–004, GOLD-TX-002–004 |
| TEAM-001–006 | page contracts, effective-squad contract | effective squad, team selector | pitch, bench, captaincy | ACC-TEAM-001–002 |
| SQD-001–006 | page contracts, source register | squad intelligence, fixture/calendar and chip contracts | strategy summary/timeline | Feature-specific tests to add in chip/strategy slices |
| PLY-001–005 | page contracts, source register | player evidence selector | player list, filters, factors | ACC-PLY-001, mobile checks |
| PLY-006–007 | source register, component catalogue | workload/research evidence | workload and research components | ACC-PLY-001–002 |
| LG-001–006 | live scoring, page contracts | manager/exposure selectors | league summary, target rival, trends | ACC-LIVE-007–009, ACC-BTW-001 |
| LG-007 | live scoring | projected-rule manager selector | KPI and manager matrix | ACC-LIVE-003, 008 |
| LIVE-001–005 | lifecycle, live scoring, runbook | `fpl.live-gameweek` | scoreboard, player strip, ledger | ACC-LIVE-001, 007–010 |
| LIVE-006–008 | live scoring | autosub/captain selector | picks, KPI, matrix | ACC-LIVE-002–006, golden live dataset |
| LIVE-009–011 | design system, lifecycle | state/freshness selectors | all live components | ACC-LIVE-009–010, visual regression |
| BTW-001–005 | page contracts, source register | change/watch selectors | Between-Games composition | ACC-BTW-001–002, ACC-PLY-002 |
| OPS-001–009 | target architecture, runbook | manifests and validation | freshness/health | ACC-OPS-001–003 |

## Existing baseline evidence

| Area | Current evidence | Migration use |
|---|---|---|
| Autosubs/live points | `live_gameweek.py`, `tests/test_live_gameweek.py` | Oracle until canonical rule engine passes golden cases |
| Free transfers/hits | `fpl_etl.py`, `declared_transfer_overlay.py`, free-transfer tests | Oracle plus reconciliation fixture |
| Multi-transfer planning | path/synthesis modules and tests | Model behaviour reference |
| Chip rules | chip modules and rule-edge tests | Rule fixture source |
| Final visible UI | `docs/index.html` ordered assets and browser screenshots | Visual/behaviour evidence only, not target structure |
| Historical product decisions | `REQUIREMENTS_RECONCILIATION.md` | Evidence where not superseded by `/spec` |

## Update rule

Every implementation PR/slice must add:

- target code module(s);
- automated test name(s);
- schema/contract version if changed;
- visual reference ID when applicable;
- decision-register ID for intentional behaviour changes.
