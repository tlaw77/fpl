import json
from datetime import datetime, timezone
from pathlib import Path

LATEST = Path('data/latest.json')
CHIP_WINDOW = Path('data/chip_window.json')
FULL = Path('data/full_squad_chip_optimizer.json')
SYNTH = Path('data/decision_synthesis.json')
STABILITY = Path('data/simulation_stability.json')
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
    blockers = []
    positives = []
    if gain >= 25: positives.append(f'Large raw six-GW opportunity (+{gain:.1f} simulation points).')
    if changes is not None and changes >= 6: positives.append(f'Optimiser would change {changes}/15 players, signalling a materially different structure.')
    if budget_conf != 'exact': blockers.append('Spendable budget is estimated because public FPL picks do not expose exact selling prices.')
    if maturity < .45: blockers.append(f'Season evidence is only {maturity*100:.0f}%; early roles/form remain noisy.')
    if pressure == 'comfortable': blockers.append('First-half chip portfolio still has comfortable calendar slack.')
    if weak_assets < 3: blockers.append(f'Current squad is not structurally broken ({int(weak_assets)} weak availability/fixture assets in the structural check).')
    if effective < 2: blockers.append(f'Only {effective:.2f} effective stability evidence runs are available so far.')
    if budget_conf == 'exact' and maturity >= .45 and effective >= 2 and gain >= 25 and (weak_assets >= 3 or pressure in ('tight','critical')):
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
        'proxy_bank_left': round(bank_left, 2),
        'season_maturity_weight': round(maturity, 3),
        'squad_overlap': overlap,
        'squad_changes': changes,
        'structural_weak_assets': int(weak_assets),
        'effective_stability_evidence': round(effective, 2),
        'portfolio_pressure': pressure,
        'positives': positives,
        'blockers': blockers,
        'reason': blockers[0] if blockers else (positives[0] if positives else 'No material Wildcard trigger.'),
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
    blockers = []
    positives = []
    if gain >= 10: positives.append(f'Best visible FH squad is +{gain:.1f} simulation points in GW{gw}.')
    if mode_gw == gw and mode_weight >= 1: positives.append(f'GW{gw} is the recurring FH scout window in stability history.')
    if blank_count == 0 and double_count == 0 and missing == 0:
        blockers.append('No confirmed blank/double disruption currently justifies spending Free Hit.')
    if effective < 2:
        blockers.append(f'Only {effective:.2f} effective stability evidence runs are available.')
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


def main():
    latest = load(LATEST, {})
    chip_window = load(CHIP_WINDOW, {})
    full = load(FULL, {})
    synth = load(SYNTH, {})
    stability = load(STABILITY, {})
    wc = gate_wc(latest, chip_window, full, stability)
    fh = gate_fh(chip_window, full, stability)
    chips = synth.get('chips') or {}
    tc = chips.get('best_visible_triple_captain') or {}
    bb = chips.get('best_visible_bench_boost') or {}
    pressure = (chip_window.get('portfolio') or {}).get('pressure', 'comfortable')
    tc_status = 'WATCH' if pressure in ('tight','critical') and n(tc.get('chip_incremental_expected_points')) >= 8 else 'HOLD'
    bb_status = 'WATCH' if pressure in ('tight','critical') and n(bb.get('chip_incremental_expected_points')) >= 14 else 'HOLD'
    out = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 1,
        'next_gw': latest.get('next_gw'),
        'portfolio_pressure': pressure,
        'latest_safe_start_gw': (chip_window.get('portfolio') or {}).get('latest_safe_start_gw'),
        'wildcard': wc,
        'free_hit': fh,
        'bench_boost': {
            'status': bb_status,
            'best_visible_gw': bb.get('chip_gw'),
            'raw_gain': round(n(bb.get('chip_incremental_expected_points')), 2),
            'reason': 'Preserve while portfolio pressure is comfortable; require an unusually strong bench window or expiry pressure.'
        },
        'triple_captain': {
            'status': tc_status,
            'best_visible_gw': tc.get('chip_gw'),
            'raw_gain': round(n(tc.get('chip_incremental_expected_points')), 2),
            'reason': 'Preserve while portfolio pressure is comfortable; prefer an elite captain spike or double-gameweek-quality opportunity.'
        },
        'method_note': 'Safety gate over raw chip simulations. It combines current squad structure, calendar pressure, season maturity, budget confidence, stability evidence and visible blank/double disruption. WATCH is an opportunity scout, not an activation recommendation.'
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status':'SUCCESS','WC':wc['status'],'FH':fh['status'],'BB':bb_status,'TC':tc_status}))


if __name__ == '__main__':
    main()
