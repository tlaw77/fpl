import json
from datetime import datetime, timezone
from pathlib import Path

LATEST = Path('data/latest.json')
OUT = Path('data/recommendation_history.json')


def player_name(x):
    return (x or {}).get('player')


def simplify_move(m, kind):
    inc_key = 'safe_in' if kind == 'lower_variance' else 'aggressive_in'
    gain_key = 'safe_gain' if kind == 'lower_variance' else 'aggressive_gain'
    incoming = m.get(inc_key) or m.get('in') or {}
    outgoing = m.get('out') or {}
    fixtures = incoming.get('fixtures') or []
    next3 = [
        {'gw': f.get('gw'), 'opponent': f.get('opponent'), 'venue': f.get('venue'), 'fdr': f.get('difficulty')}
        for f in fixtures[:3]
    ]
    target_own = incoming.get('target_rival_ownership_pct')
    rationale = []
    if next3:
        rationale.append('Next-3 fixtures: ' + ', '.join(f"{f['opponent']} {f['venue']} FDR {f['fdr']}" for f in next3))
    if target_own is not None:
        if kind == 'lower_variance':
            rationale.append(f"Nearest-rival ownership {target_own:.0f}%: more protective if the football case is strong.")
        else:
            rationale.append(f"Nearest-rival ownership {target_own:.0f}%: lower ownership offers more leverage if the football case is strong.")
    rationale.append(f"Model uplift {float(m.get(gain_key) or m.get('score_improvement') or 0):.1f} versus the outgoing player on the dashboard heuristic.")
    return {
        'type': kind,
        'out_player_id': outgoing.get('player_id'),
        'out': player_name(outgoing),
        'in_player_id': incoming.get('player_id'),
        'in': player_name(incoming),
        'in_club': incoming.get('club'),
        'in_price': incoming.get('price'),
        'gain': m.get(gain_key) if m.get(gain_key) is not None else m.get('score_improvement'),
        'target_rival_ownership_pct': target_own,
        'next3': next3,
        'rationale': rationale,
    }


def main():
    data = json.loads(LATEST.read_text())
    decisions = data.get('next_gw_decisions') or {}
    safe = [simplify_move(m, 'lower_variance') for m in (decisions.get('safe_moves') or [])[:5]]
    chase = [simplify_move(m, 'variety') for m in (decisions.get('aggressive_moves') or [])[:5]]
    snapshot = {
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'source_generated_at_utc': data.get('generated_at_utc'),
        'current_gw': data.get('current_gw'),
        'next_gw': data.get('next_gw'),
        'team_rank': data.get('me', {}).get('rank'),
        'bank': data.get('me', {}).get('bank'),
        'strategy': 'Balanced+ / controlled leverage',
        'lower_variance': safe,
        'variety': chase,
    }
    history = json.loads(OUT.read_text()) if OUT.exists() else {'version': 1, 'snapshots': []}
    fingerprint = json.dumps({
        'gw': snapshot['current_gw'],
        'safe': [(x['out'], x['in']) for x in safe],
        'chase': [(x['out'], x['in']) for x in chase],
    }, sort_keys=True)
    if not history['snapshots'] or history['snapshots'][-1].get('fingerprint') != fingerprint:
        snapshot['fingerprint'] = fingerprint
        history['snapshots'].append(snapshot)
    OUT.write_text(json.dumps(history, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status':'SUCCESS','snapshots':len(history['snapshots'])}))


if __name__ == '__main__':
    main()
