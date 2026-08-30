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


def wc_activation_adjustment(raw_gain, maturity, changes, budget_conf, bank_left, stability):
    """Shrink a Wildcard scout uplift into activation evidence.

    The raw optimiser remains untouched. This conservative layer reflects that a
    15-player rebuild compounds player-level uncertainty, especially early in a
    season. Persistence rises only when materially different deep-search inputs
    repeatedly return the same Wildcard squad structure.
    """
    st = stability.get('summary') or {}
    persistence_pct = n(st.get('wc_latest_squad_persistence_pct'))
    effective_runs = n(st.get('effective_evidence_runs'))

    # Early-season full-squad differences compound uncertainty. The factor rises
    # gradually from 0.43 at 0% maturity to 1.0 at full-season maturity.
    maturity_factor = max(.43, min(1.0, .43 + .57 * maturity))

    # Replacing most of a squad means more independent projection assumptions
    # must all be right. Do not punish a genuine 5-7 player structural reset as
    # heavily as an 11-15 player optimiser churn.
    if changes is None:
        turnover_factor = .75
    elif changes <= 5:
        turnover_factor = 1.0
    elif changes <= 7:
        turnover_factor = .90
    elif changes <= 9:
        turnover_factor = .80
    elif changes <= 11:
        turnover_factor = .70
    else:
        turnover_factor = .62

    if budget_conf == 'exact':
        budget_factor = 1.0
    elif budget_conf == 'reconstructed':
        budget_factor = .94 if bank_left >= 1.0 else .82
    else:
        budget_factor = .72

    # Persistence is intentionally conservative at first. We need both weighted
    # history and the same squad recurring before treating the 15-player optimum
    # as stable. Never reduce below 0.55 so the metric remains interpretable.
    if effective_runs < 2 or persistence_pct <= 0:
        persistence_factor = .55
    else:
        persistence_factor = max(.55, min(1.0, .55 + .45 * (persistence_pct / 100)))

    adjusted = max(0.0, raw_gain) * maturity_factor * turnover_factor * budget_factor * persistence_factor
    return {
        'activation_adjusted_gain_6gw': round(adjusted, 2),
        'maturity_factor': round(maturity_factor, 3),
        'turnover_factor': round(turnover_factor, 3),
        'budget_factor': round(budget_factor, 3),
        'persistence_factor': round(persistence_factor, 3),
        'wc_squad_persistence_pct': round(persistence_pct, 1),
        'effective_stability_runs': round(effective_runs, 2),
    }


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
    adjustment = wc_activation_adjustment(gain, maturity, changes, budget_conf, bank_left, stability)
    adjusted_gain = n(adjustment.get('activation_adjusted_gain_6gw'))
    persistence = n(adjustment.get('wc_squad_persistence_pct'))
    deadline = latest.get('deadline_context') or {}
    deadline_phase = deadline.get('phase') or 'unknown'
    blockers, cautions, positives = [], [], []

    if gain >= 25:
        positives.append(f'Raw six-GW Wildcard scout is large (+{gain:.1f} simulation points before activation shrinkage).')
    if adjusted_gain >= 20:
        positives.append(f'Conservative activation-adjusted uplift remains material (+{adjusted_gain:.1f} over six Gameweeks).')
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
        blockers.append(f'Only {maturity*100:.0f}% of full-season evidence weight is available; a 15-player rebuild compounds early role/form uncertainty.')
    if pressure == 'comfortable':
        blockers.append('There is still plenty of time to use the first-half chips.')
    if weak_assets < 3:
        blockers.append(f'The current squad is not structurally broken ({int(weak_assets)} weak availability/fixture assets in the structural check).')
    if effective < 2:
        blockers.append(f'Only {effective:.2f} effective stability checks are available so far.')
    if persistence < 55:
        blockers.append(f'The current Wildcard squad has only {persistence:.0f}% weighted persistence so far; the optimiser structure has not proved stable.')
    elif persistence < 75:
        cautions.append(f'Wildcard squad persistence is {persistence:.0f}%; wait for stronger agreement across changed inputs before activation.')
    if deadline_phase in ('normal', 'approaching'):
        cautions.append('The deadline is not yet close, so late injury/team-news information still has option value.')

    budget_usable = budget_conf == 'exact' or (budget_conf == 'reconstructed' and bank_left >= 1.0)
    robust_wc = persistence >= 75 and effective >= 3
    structural_need = weak_assets >= 3 or pressure in ('tight', 'critical')
    if budget_usable and maturity >= .45 and robust_wc and adjusted_gain >= 20 and structural_need:
        status = 'CONSIDER'
    elif adjusted_gain >= 12 and (maturity >= .35 or structural_need):
        status = 'WATCH'
    else:
        status = 'HOLD'
    if maturity < .35 and pressure == 'comfortable' and weak_assets < 3:
        status = 'HOLD'

    return {
        'status': status,
        'raw_gain_6gw': round(gain, 2),
        'activation_adjusted_gain_6gw': round(adjusted_gain, 2),
        'activation_adjustment': adjustment,
        'budget_confidence': budget_conf,
        'budget_buffer': round(bank_left, 2),
        'season_maturity_weight': round(maturity, 3),
        'squad_overlap': overlap,
        'squad_changes': changes,
        'structural_weak_assets': int(weak_assets),
        'effective_stability_evidence': round(effective, 2),
        'wc_squad_persistence_pct': round(persistence, 1),
        'portfolio_pressure': pressure,
        'deadline_phase': deadline_phase,
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
        'version': 3,
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
        'method_note': 'Decision gate over chip simulations and dedicated chip reviews. Wildcard retains the raw optimiser scout but uses a separately reported activation-adjusted uplift that discounts early-season uncertainty, high squad turnover, imperfect budget confidence and unproven Wildcard-squad persistence. WATCH means observe; CONSIDER means make an explicit chip decision now, not automatic activation.'
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status':'SUCCESS','WC':wc['status'],'WC_raw':wc['raw_gain_6gw'],'WC_adjusted':wc['activation_adjusted_gain_6gw'],'WC_persistence':wc['wc_squad_persistence_pct'],'FH':fh['status'],'BB':bb_status,'TC':tc_gate['status']}))


if __name__ == '__main__':
    main()
