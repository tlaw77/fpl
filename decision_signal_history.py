import json
from datetime import datetime, timezone
from pathlib import Path

SYNTHESIS = Path('data/decision_synthesis.json')
OUT = Path('data/decision_signal_history.json')
MAX_SNAPSHOTS = 240


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def n(v, default=0.0):
    try:
        return float(v)
    except Exception:
        return default


def signal_score(edge, threshold, support, required_support, clears):
    if clears:
        return 100.0
    edge_ratio = max(0.0, min(1.0, edge / threshold)) if threshold > 0 else 0.0
    support_ratio = max(0.0, min(1.0, support / required_support)) if required_support > 0 else 0.0
    # Magnitude leads; agreement is the second gate. Score is descriptive, not a new decision rule.
    return round(min(99.0, edge_ratio * 72.0 + support_ratio * 28.0), 1)


def band(score, clears):
    if clears or score >= 90:
        return 'ACT'
    if score >= 65:
        return 'WATCH'
    return 'STABLE'


def run():
    syn = load(SYNTHESIS, {})
    if syn.get('status') != 'SUCCESS':
        raise RuntimeError('decision_synthesis.json is not successful')

    action = syn.get('current_action') or {}
    robust = syn.get('robustness') or {}
    edge = n(robust.get('single_step_edge_over_hold_6gw'))
    threshold = n(robust.get('required_edge'))
    support = int(robust.get('measured_leader_support_models') or 0)
    required_support = int(robust.get('required_consensus_models') or 0)
    clears = bool(robust.get('transfer_clears_gate'))
    score = signal_score(edge, threshold, support, required_support, clears)

    snapshot = {
        'captured_at_utc': syn.get('generated_at_utc') or datetime.now(timezone.utc).isoformat(),
        'current_gw': syn.get('current_gw'),
        'next_gw': syn.get('next_gw'),
        'action': action.get('action'),
        'headline': action.get('headline'),
        'leader': robust.get('single_step_leader'),
        'edge_over_hold_6gw': round(edge, 2),
        'required_edge': round(threshold, 2),
        'leader_support_models': support,
        'required_support_models': required_support,
        'transfer_clears_gate': clears,
        'signal_score': score,
        'signal_band': band(score, clears),
        'completed_transfer_route': (action.get('completed_transfer') or {}).get('route'),
        'next_transfer_hit_cost': action.get('next_transfer_hit_cost'),
    }

    history = load(OUT, {'version': 1, 'snapshots': []})
    snapshots = history.get('snapshots') or []

    def fingerprint(x):
        return (
            x.get('next_gw'), x.get('action'), x.get('leader'),
            x.get('edge_over_hold_6gw'), x.get('required_edge'),
            x.get('leader_support_models'), x.get('required_support_models'),
            x.get('transfer_clears_gate'), x.get('signal_band'),
            x.get('completed_transfer_route'), x.get('next_transfer_hit_cost')
        )

    if not snapshots or fingerprint(snapshots[-1]) != fingerprint(snapshot):
        snapshots.append(snapshot)
    elif snapshots:
        # Keep the latest timestamp for an unchanged state without creating noise.
        snapshots[-1]['captured_at_utc'] = snapshot['captured_at_utc']

    history = {
        'version': 1,
        'updated_at_utc': datetime.now(timezone.utc).isoformat(),
        'snapshots': snapshots[-MAX_SNAPSHOTS:],
    }
    OUT.write_text(json.dumps(history, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'signal_band': snapshot['signal_band'], 'signal_score': score, 'snapshots': len(history['snapshots'])}))


if __name__ == '__main__':
    run()
