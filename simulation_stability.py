import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

LATEST = Path('data/latest.json')
SYNTH = Path('data/decision_synthesis.json')
PATH_SIM = Path('data/path_simulation.json')
ADAPT = Path('data/adaptive_rival_simulation.json')
FULL_CHIP = Path('data/full_squad_chip_optimizer.json')
OUT = Path('data/simulation_stability.json')
MAX_SNAPSHOTS = 192
WINDOW = 12
UNCHANGED_WEIGHT = 0.25


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
    path = load(PATH_SIM, {})
    adapt = load(ADAPT, {})
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


def materially_duplicate(a, b):
    if not a or not b:
        return False
    keys = [
        'next_gw','action','confidence','single_step_leader','transfer_clears_gate',
        'multi_gw_first_route','adaptive_first_route','best_tc_gw','best_bb_gw',
        'best_fh_gw','deep_sim_input_signature','completed_transfer'
    ]
    if not all(a.get(k) == b.get(k) for k in keys):
        return False
    try:
        prev = datetime.fromisoformat(str(a.get('captured_at_utc')).replace('Z', '+00:00'))
        now = datetime.fromisoformat(str(b.get('captured_at_utc')).replace('Z', '+00:00'))
        return (now - prev).total_seconds() < 20 * 60
    except Exception:
        return False


def evidence_weight(prev, cur):
    if not prev:
        return 1.0, 'initial'
    material_keys = [
        'next_gw','completed_transfer','action','single_step_leader','transfer_clears_gate',
        'multi_gw_first_route','adaptive_first_route','best_tc_gw','best_bb_gw','best_fh_gw'
    ]
    if prev.get('deep_sim_input_signature') != cur.get('deep_sim_input_signature'):
        return 1.0, 'deep-input-change'
    if any(prev.get(k) != cur.get(k) for k in material_keys):
        return 1.0, 'decision-state-change'
    return UNCHANGED_WEIGHT, 'unchanged-input-refresh'


def weighted_pct(rows, predicate):
    den = sum(n(x.get('evidence_weight'), 1.0) for x in rows)
    num = sum(n(x.get('evidence_weight'), 1.0) for x in rows if predicate(x))
    return round(100 * num / den, 1) if den else 0.0


def weighted_avg(rows, field):
    vals = [(n(x.get(field)), n(x.get('evidence_weight'), 1.0)) for x in rows if x.get(field) is not None]
    den = sum(w for _, w in vals)
    return round(sum(v * w for v, w in vals) / den, 2) if den else None


def weighted_mode(rows, field):
    scores = {}
    counts = Counter()
    for x in rows:
        value = x.get(field)
        if value is None:
            continue
        scores[value] = scores.get(value, 0.0) + n(x.get('evidence_weight'), 1.0)
        counts[value] += 1
    if not scores:
        return None, 0, 0.0
    value = max(scores, key=scores.get)
    return value, counts[value], round(scores[value], 2)


def summarize(snaps):
    if not snaps:
        return {}
    recent = snaps[-WINDOW:]
    latest = recent[-1]
    total = len(recent)
    total_weight = round(sum(n(x.get('evidence_weight'), 1.0) for x in recent), 2)
    route, route_runs, route_weight = weighted_mode(recent, 'multi_gw_first_route')
    fh_gw, fh_runs, fh_weight = weighted_mode(recent, 'best_fh_gw')
    leader_mode, _, _ = weighted_mode(recent, 'single_step_leader')
    return {
        'window_runs': total,
        'effective_evidence_runs': total_weight,
        'action': latest.get('action'),
        'action_persistence_pct': weighted_pct(recent, lambda x: x.get('action') == latest.get('action')),
        'leader': latest.get('single_step_leader'),
        'leader_persistence_pct': weighted_pct(recent, lambda x: x.get('single_step_leader') == latest.get('single_step_leader')),
        'most_common_leader': leader_mode,
        'most_common_forward_route': route,
        'most_common_forward_route_runs': route_runs,
        'most_common_forward_route_weight': route_weight,
        'transfer_gate_clear_pct': weighted_pct(recent, lambda x: x.get('transfer_clears_gate') is True),
        'average_confidence': weighted_avg(recent, 'confidence'),
        'average_edge_over_hold_6gw': weighted_avg(recent, 'single_step_edge_over_hold_6gw'),
        'best_fh_gw_mode': fh_gw,
        'best_fh_gw_mode_runs': fh_runs,
        'best_fh_gw_mode_weight': fh_weight,
        'average_wc_raw_gain': weighted_avg(recent, 'wc_gain'),
        'latest_deep_sim_generated_at_utc': latest.get('deep_sim_generated_at_utc'),
        'latest_deep_sim_input_signature': latest.get('deep_sim_input_signature'),
        'latest_evidence_reason': latest.get('evidence_reason'),
        'note': 'Persistence is weighted. A changed deep-input signature or changed decision state counts as 1.0 evidence; an unchanged-input refresh counts as 0.25. This reduces false confidence from repeated cached runs.'
    }


def main():
    old = load(OUT, {'version': 2, 'snapshots': []})
    snaps = old.get('snapshots') or []
    for x in snaps:
        x.setdefault('evidence_weight', 1.0)
        x.setdefault('evidence_reason', 'legacy')
    cur = snapshot()
    if not snaps or not materially_duplicate(snaps[-1], cur):
        weight, reason = evidence_weight(snaps[-1] if snaps else None, cur)
        cur['evidence_weight'] = weight
        cur['evidence_reason'] = reason
        snaps.append(cur)
    snaps = snaps[-MAX_SNAPSHOTS:]
    out = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 2,
        'window_size': WINDOW,
        'snapshot_count': len(snaps),
        'summary': summarize(snaps),
        'snapshots': snaps,
        'method_note': 'Bounded rolling history of simulation summaries with input-aware evidence weighting and 20-minute deduplication.'
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'snapshots': len(snaps), 'summary': out['summary']}))


if __name__ == '__main__':
    main()
