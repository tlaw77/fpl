import json
from datetime import datetime, timezone
from pathlib import Path

LATEST = Path('data/latest.json')
CHIP_WINDOW = Path('data/chip_window.json')
FULL = Path('data/full_squad_chip_optimizer.json')
SYNTH = Path('data/decision_synthesis.json')
STABILITY = Path('data/simulation_stability.json')
TC_REVIEW = Path('data/triple_captain_review.json')
OUT = Path('data/chip_activation_gate.json')


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def current_ids(latest):
    rows = latest.get('current_squad_next5') or latest.get('squad_next5') or []
    return {int(x.get('player_id') or 0) for x in rows if int(x.get('player_id') or 0)}


def evaluation(chip_window, name):
    return next((x for x in chip_window.get('evaluations', []) if x.get('chip') == name), {})


def gate_wc(latest, chip_window, full, stability):
    wc = full.get('best_wildcard') or {}
    current = current_ids(latest)
    wc_ids = {int(x.get('player_id') or 0) for x in wc.get('squad', [])}
    overlap = len(current & wc_ids) if current and wc_ids else None
    changes = (15 - overlap) if overlap is not None else None
    gain = n(wc.get('incremental_expected_points_vs_current_squad'))
    maturity = n(full.get('season_maturity_weight'))
    budget_conf = full.get('budget_confidence') or 'unknown'
    bank_left = n(wc.get('bank_left'))
    pressure = (chip_window.get('portfolio') or {}).get('pressure', 'comfortable')
    structural = evaluation(chip_window, 'Wildcard')
    weak_assets = n((structural.get('current_window') or {}).get('weak_assets'))
    effective = n((stability.get('summary') or {}).get('effective_evidence_runs'))
    blockers, cautions, positives = [], [], []

    if gain >= 25:
        positives.append(f'Large six-GW model opportunity (+{gain:.1f} modelled points).')
    if changes is not None and changes >= 6:
        positives.append(f'The optimiser would change {changes}/15 players, so this is a genuinely different squad structure.')

    if budget_conf == 'estimated':
        blockers.append('Spendable budget is only estimated from current market values.')
    elif budget_conf == 'reconstructed':
        if bank_left >= 1.0:
            positives.append(f'Selling budget is reconstructed and the squad keeps £{bank_left:.1f}m spare, giving useful protection against small reconstruction error.')
            cautions.append('Selling prices are reconstructed from purchase history rather than exposed directly by FPL.')
        else:
            blockers.append('Selling prices are reconstructed rather than exact and the proposed Wildcard leaves too little budget buffer.')
    elif budget_conf != 'exact':
        blockers.append('Spendable-budget confidence is not yet strong enough for Wildcard activation.')

    if maturity < .45:
        blockers.append(f'Only {maturity*100:.0f}% of full-season evidence weight is available; early roles and form are still noisy.')
    if pressure == 'comfortable':
        blockers.append('There is still plenty of time to use the first-half chips.')
    if weak_assets < 3:
        blockers.append(f'The current squad is not structurally broken ({int(weak_assets)} weak availability/fixture assets in the structural check).')
    if effective < 2:
        blockers.append(f'Only {effective:.2f} effective stability checks are available so far.')

    budget_usable = budget_conf == 'exact' or (budget_conf == 'reconstructed' and bank_left >= 1.0)
    if budget_usable and maturity >= .45 and effective >= 2 and gain >= 25 and (weak_assets >= 3 or pressure in ('tight', 'critical')):
        status = 'CONSIDER'
    elif gain >= 20:
        status = 'WATCH'
    else:
        status = 'HOLD'
    if maturity < .35 and pressure == 'comfortable' and weak_assets < 3:
        status = 'HOLD'

    return {
        'status': status,
        'raw_gain_6gw': round(gain, 2),
        'budget_confidence': budget_conf,
        'budget_buffer': round(bank_left, 2),
        'season_maturity_weight': round(maturity, 3),
        'squad_overlap': overlap,
        'squad_changes': changes,
        'structural_weak_assets': int(weak_assets),
        'effective_stability_evidence': round(effective, 2),
        'portfolio_pressure': pressure,
        'positives': positives,
        'cautions': cautions,
        'blockers': blockers,
        'reason': blockers[0] if blockers else (cautions[0] if cautions else (positives[0] if positives else 'No material Wildcard trigger.')),
    }


def gate_fh(chip_window, full, stability):
    fh = full.get('best_free_hit') or {}
    structural = evaluation(chip_window, 'Free Hit')
    current = structural.get('current_window') or {}
    gain = n(fh.get('incremental_expected_points_vs_current_squad'))
    gw = fh.get('gw')
    blank_count = int(n(current.get('blank_team_count')))
    double_count = int(n(current.get('double_team_count')))
    missing = int(n(current.get('squad_players_without_playable_fixture')))
    st = stability.get('summary') or {}
    effective = n(st.get('effective_evidence_runs'))
    mode_gw = st.get('best_fh_gw_mode')
    mode_weight = n(st.get('best_fh_gw_mode_weight'))
    blockers, positives = [], []
    if gain >= 10:
        positives.append(f'Best visible Free Hit squad is +{gain:.1f} modelled points in GW{gw}.')
    if mode_gw == gw and mode_weight >= 1:
        positives.append(f'GW{gw} has repeatedly appeared as the strongest visible Free Hit window.')
    if blank_count == 0 and double_count == 0 and missing == 0:
        blockers.append('There is no confirmed blank or double-Gameweek disruption that currently justifies spending Free Hit.')
    if effective < 2:
        blockers.append(f'Only {effective:.2f} effective stability checks are available.')
    if (blank_count > 0 or double_count > 0 or missing >= 3) and gain >= 10 and effective >= 2:
        status = 'CONSIDER'
    elif gain >= 10:
        status = 'WATCH'
    else:
        status = 'HOLD'
    return {
        'status': status,
        'best_visible_gw': gw,
        'raw_gain': round(gain, 2),
        'blank_team_count': blank_count,
        'double_team_count': double_count,
        'squad_without_fixture': missing,
        'effective_stability_evidence': round(effective, 2),
        'positives': positives,
        'blockers': blockers,
        'reason': blockers[0] if blockers else (positives[0] if positives else 'No material Free Hit trigger.'),
    }


def gate_tc(chip_window, synth, tc_review):
    dedicated = tc_review.get('decision') or {}
    candidate = dedicated.get('candidate') or {}
    if dedicated.get('status') in ('HOLD', 'WATCH', 'CONSIDER') and candidate:
        reasons_now = dedicated.get('reasons_for_now') or []
        reasons_wait = dedicated.get('reasons_to_wait') or []
        return {
            'status': dedicated.get('status'),
            'best_visible_gw': candidate.get('gw'),
            'candidate': candidate.get('player'),
            'opponent': candidate.get('opponent'),
            'venue': candidate.get('venue'),
            'raw_gain': round(n(candidate.get('expected_extra_tc_points')), 2),
            'tier': candidate.get('tier'),
            'reasons_for_now': reasons_now,
            'reasons_to_wait': reasons_wait,
            'reason': (reasons_now or reasons_wait or ['No standout Triple Captain opportunity.'])[0],
            'source': 'owned_squad_tc_review',
        }

    pressure = (chip_window.get('portfolio') or {}).get('pressure', 'comfortable')
    tc = (synth.get('chips') or {}).get('best_visible_triple_captain') or {}
    gain = n(tc.get('chip_incremental_expected_points'))
    status = 'WATCH' if pressure in ('tight', 'critical') and gain >= 8 else 'HOLD'
    return {
        'status': status,
        'best_visible_gw': tc.get('chip_gw'),
        'candidate': None,
        'raw_gain': round(gain, 2),
        'reason': 'Keep the chip available until an outstanding captain opportunity appears.',
        'source': 'generic_chip_path_fallback',
    }


def main():
    latest = load(LATEST, {})
    chip_window = load(CHIP_WINDOW, {})
    full = load(FULL, {})
    synth = load(SYNTH, {})
    stability = load(STABILITY, {})
    tc_review = load(TC_REVIEW, {})
    wc = gate_wc(latest, chip_window, full, stability)
    fh = gate_fh(chip_window, full, stability)
    tc_gate = gate_tc(chip_window, synth, tc_review)
    bb = (synth.get('chips') or {}).get('best_visible_bench_boost') or {}
    pressure = (chip_window.get('portfolio') or {}).get('pressure', 'comfortable')
    bb_status = 'WATCH' if pressure in ('tight', 'critical') and n(bb.get('chip_incremental_expected_points')) >= 14 else 'HOLD'
    out = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 2,
        'next_gw': latest.get('next_gw'),
        'portfolio_pressure': pressure,
        'latest_safe_start_gw': (chip_window.get('portfolio') or {}).get('latest_safe_start_gw'),
        'wildcard': wc,
        'free_hit': fh,
        'bench_boost': {
            'status': bb_status,
            'best_visible_gw': bb.get('chip_gw'),
            'raw_gain': round(n(bb.get('chip_incremental_expected_points')), 2),
            'reason': 'Keep Bench Boost available while the calendar is comfortable; use it when the full bench has an unusually strong set of fixtures or expiry pressure rises.'
        },
        'triple_captain': tc_gate,
        'method_note': 'Decision gate over chip simulations and dedicated chip reviews. It combines squad structure, calendar pressure, season evidence, budget confidence, stability and visible schedule disruption. WATCH means keep an opportunity under observation; CONSIDER means it deserves an explicit decision now, not that activation is automatic.'
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status':'SUCCESS','WC':wc['status'],'FH':fh['status'],'BB':bb_status,'TC':tc_gate['status']}))


if __name__ == '__main__':
    main()
