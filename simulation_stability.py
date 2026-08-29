import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

LATEST = Path('data/latest.json')
SYNTH = Path('data/decision_synthesis.json')
SIM = Path('data/simulation.json')
PATH_SIM = Path('data/path_simulation.json')
ADAPT = Path('data/adaptive_rival_simulation.json')
CHIP_PATH = Path('data/chip_path_simulation.json')
FULL_CHIP = Path('data/full_squad_chip_optimizer.json')
OUT = Path('data/simulation_stability.json')
MAX_SNAPSHOTS = 192
WINDOW = 12


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


def first_route(obj):
    rec = obj.get('recommendation') or {}
    acts = rec.get('actions') or []
    if acts:
        return acts[0].get('route') or acts[0].get('action')
    return rec.get('route') or rec.get('label')


def snapshot():
    latest = load(LATEST, {})
    synth = load(SYNTH, {})
    sim = load(SIM, {})
    path = load(PATH_SIM, {})
    adapt = load(ADAPT, {})
    chip = load(CHIP_PATH, {})
    full = load(FULL_CHIP, {})
    action = synth.get('current_action') or {}
    robust = synth.get('robustness') or {}
    chips = synth.get('chips') or {}
    fh = full.get('best_free_hit') or {}
    wc = full.get('best_wildcard') or {}
    completed = action.get('completed_transfer') or {}
    return {
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'current_gw': latest.get('current_gw'),
        'next_gw': latest.get('next_gw'),
        'action': action.get('action'),
        'headline': action.get('headline'),
        'confidence': action.get('confidence'),
        'completed_transfer': completed.get('route'),
        'free_transfers_remaining': action.get('free_transfers_remaining'),
        'next_transfer_hit_cost': action.get('next_transfer_hit_cost'),
        'single_step_leader': robust.get('single_step_leader'),
        'single_step_edge_over_hold_6gw': robust.get('single_step_edge_over_hold_6gw'),
        'measured_leader_support_models': robust.get('measured_leader_support_models'),
        'transfer_clears_gate': robust.get('transfer_clears_gate'),
        'multi_gw_first_route': first_route(path),
        'adaptive_first_route': first_route(adapt),
        'best_tc_gw': (chips.get('best_visible_triple_captain') or {}).get('chip_gw'),
        'best_tc_gain': (chips.get('best_visible_triple_captain') or {}).get('chip_incremental_expected_points'),
        'best_bb_gw': (chips.get('best_visible_bench_boost') or {}).get('chip_gw'),
        'best_bb_gain': (chips.get('best_visible_bench_boost') or {}).get('chip_incremental_expected_points'),
        'best_fh_gw': fh.get('gw'),
        'best_fh_gain': fh.get('incremental_expected_points_vs_current_squad'),
        'wc_gain': wc.get('incremental_expected_points_vs_current_squad'),
        'wc_budget_confidence': full.get('budget_confidence'),
        'season_maturity_weight': robust.get('season_maturity_weight', full.get('season_maturity_weight')),
        'deep_sim_generated_at_utc': full.get('generated_at_utc'),
        'deep_sim_input_signature': full.get('input_signature'),
    }


def pct(num, den):
    return round(100 * num / den, 1) if den else 0.0


def summarize(snaps):
    if not snaps:
        return {}
    recent = snaps[-WINDOW:]
    total = len(recent)
    latest = recent[-1]
    action_counts = Counter(x.get('action') for x in recent if x.get('action'))
    leader_counts = Counter(x.get('single_step_leader') for x in recent if x.get('single_step_leader'))
    path_counts = Counter(x.get('multi_gw_first_route') for x in recent if x.get('multi_gw_first_route'))
    fh_counts = Counter(x.get('best_fh_gw') for x in recent if x.get('best_fh_gw') is not None)
    same_action = sum(1 for x in recent if x.get('action') == latest.get('action'))
    same_leader = sum(1 for x in recent if x.get('single_step_leader') == latest.get('single_step_leader'))
    clears = sum(1 for x in recent if x.get('transfer_clears_gate') is True)
    confidence_vals = [n(x.get('confidence')) for x in recent if x.get('confidence') is not None]
    edge_vals = [n(x.get('single_step_edge_over_hold_6gw')) for x in recent if x.get('single_step_edge_over_hold_6gw') is not None]
    wc_vals = [n(x.get('wc_gain')) for x in recent if x.get('wc_gain') is not None]
    return {
        'window_runs': total,
        'action': latest.get('action'),
        'action_persistence_pct': pct(same_action, total),
        'action_counts': dict(action_counts),
        'leader': latest.get('single_step_leader'),
        'leader_persistence_pct': pct(same_leader, total),
        'most_common_leader': leader_counts.most_common(1)[0][0] if leader_counts else None,
        'most_common_forward_route': path_counts.most_common(1)[0][0] if path_counts else None,
        'most_common_forward_route_runs': path_counts.most_common(1)[0][1] if path_counts else 0,
        'transfer_gate_clear_pct': pct(clears, total),
        'average_confidence': round(sum(confidence_vals) / len(confidence_vals), 1) if confidence_vals else None,
        'average_edge_over_hold_6gw': round(sum(edge_vals) / len(edge_vals), 2) if edge_vals else None,
        'best_fh_gw_mode': fh_counts.most_common(1)[0][0] if fh_counts else None,
        'best_fh_gw_mode_runs': fh_counts.most_common(1)[0][1] if fh_counts else 0,
        'average_wc_raw_gain': round(sum(wc_vals) / len(wc_vals), 2) if wc_vals else None,
        'latest_deep_sim_generated_at_utc': latest.get('deep_sim_generated_at_utc'),
        'latest_deep_sim_input_signature': latest.get('deep_sim_input_signature'),
        'note': 'Persistence describes recent model runs, not independent evidence. Repeated runs with unchanged inputs increase stability confidence less than materially different snapshots.'
    }


def materially_duplicate(a, b):
    if not a or not b:
        return False
    keys = [
        'next_gw','action','confidence','single_step_leader','transfer_clears_gate',
        'multi_gw_first_route','adaptive_first_route','best_tc_gw','best_bb_gw',
        'best_fh_gw','deep_sim_input_signature','completed_transfer'
    ]
    same = all(a.get(k) == b.get(k) for k in keys)
    if not same:
        return False
    try:
        prev = datetime.fromisoformat(str(a.get('captured_at_utc')).replace('Z', '+00:00'))
        now = datetime.fromisoformat(str(b.get('captured_at_utc')).replace('Z', '+00:00'))
        return (now - prev).total_seconds() < 20 * 60
    except Exception:
        return False


def main():
    old = load(OUT, {'version': 1, 'snapshots': []})
    snaps = old.get('snapshots') or []
    cur = snapshot()
    if not snaps or not materially_duplicate(snaps[-1], cur):
        snaps.append(cur)
    snaps = snaps[-MAX_SNAPSHOTS:]
    out = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 1,
        'window_size': WINDOW,
        'snapshot_count': len(snaps),
        'summary': summarize(snaps),
        'snapshots': snaps,
        'method_note': 'Bounded rolling history of simulation summaries. Materially identical snapshots inside 20 minutes are deduplicated. Intended to reveal persistence and model flips without treating repeated unchanged runs as independent evidence.'
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'snapshots': len(snaps), 'summary': out['summary']}))


if __name__ == '__main__':
    main()
