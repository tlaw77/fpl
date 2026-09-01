import json
import math
from datetime import datetime, timezone
from pathlib import Path

POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market_strength.json')
OUT = Path('data/signal_consensus.json')


def load(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if default is None else default


def n(v, d=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else d
    except Exception:
        return d


def norm(s):
    return str(s or '').strip().lower()


def market_map(data):
    out = {}
    for row in data.get('fixtures') or []:
        h, a = norm(row.get('home_team')), norm(row.get('away_team'))
        if not h or not a:
            continue
        out[(h, a)] = row
    return out


def next_market_signal(player, mmap):
    fixtures = player.get('fixtures') or []
    if not fixtures:
        return None
    f = fixtures[0]
    club, opp = norm(player.get('club')), norm(f.get('opponent'))
    venue = str(f.get('venue') or '').upper()
    key = (club, opp) if venue == 'H' else (opp, club)
    row = mmap.get(key)
    if not row:
        return None
    modifier = n(row.get('home_market_strength_modifier' if venue == 'H' else 'away_market_strength_modifier'), 1.0)
    return max(-1.0, min(1.0, (modifier - 1.0) / .08))


def scout_signal(row):
    if not row:
        return None
    merit = norm(row.get('merit'))
    if 'strong shortlist' in merit or 'reinforces hold' in merit:
        return .85
    if 'worth investigating' in merit:
        return .55
    if 'consensus mention' in merit:
        return .30
    if 'model likes more than scouts' in merit:
        return -.15
    if any(x in merit for x in ('avoid', 'concern', 'sell')):
        return -.85
    return .10


def band(value):
    if value >= .42:
        return 'POSITIVE'
    if value <= -.42:
        return 'NEGATIVE'
    return 'NEUTRAL'


def main():
    pool = load(POOL, {'players': []})
    scout = load(SCOUT, {'players': []})
    market = load(MARKET, {'fixtures': []})
    players = pool.get('players') or []
    if not players:
        OUT.write_text(json.dumps({'status': 'NO_PLAYER_POOL', 'players': []}, indent=2) + '\n')
        return

    scores = [n(p.get('six_gw_score')) for p in players]
    lo, hi = min(scores), max(scores)
    scout_by_id = {int(x.get('player_id') or 0): x for x in scout.get('players') or []}
    mmap = market_map(market)
    priors = {'GKP': .01, 'DEF': .10, 'MID': .30, 'FWD': .42}
    rows = []

    for p in players:
        pid = int(p.get('player_id') or 0)
        pos = p.get('position')
        model_pct = .5 if hi <= lo else (n(p.get('six_gw_score')) - lo) / (hi - lo)
        model_signal = max(-1.0, min(1.0, (model_pct - .5) * 2.0))

        xgi90 = n(p.get('expected_goal_involvements_per_90'))
        prior = priors.get(pos, .25)
        underlying_signal = max(-1.0, min(1.0, (xgi90 - prior) / .28))

        pstart = max(0.0, min(1.0, n(p.get('prob_start'), .65)))
        p60 = max(0.0, min(1.0, n(p.get('prob_60_plus'), .55)))
        minutes_signal = max(-1.0, min(1.0, ((pstart * .6 + p60 * .4) - .62) / .32))

        sc = scout_signal(scout_by_id.get(pid))
        mk = next_market_signal(p, mmap)

        components = {
            'model': {'signal': round(model_signal, 3), 'weight': 1.0, 'available': True},
            'underlying': {'signal': round(underlying_signal, 3), 'weight': .85, 'available': True},
            'minutes': {'signal': round(minutes_signal, 3), 'weight': 1.0, 'available': True},
            'scout': {'signal': round(sc, 3) if sc is not None else None, 'weight': .75, 'available': sc is not None},
            'independent_market': {'signal': round(mk, 3) if mk is not None else None, 'weight': .90, 'available': mk is not None},
        }

        available = [v for v in components.values() if v['available']]
        total_weight = sum(v['weight'] for v in available) or 1.0
        signed = sum(v['signal'] * v['weight'] for v in available) / total_weight
        positive = sum(max(0.0, v['signal']) * v['weight'] for v in available)
        negative = sum(max(0.0, -v['signal']) * v['weight'] for v in available)
        directional = positive + negative
        disagreement = 0.0 if directional <= .05 else 2.0 * min(positive, negative) / directional
        strength = min(1.0, directional / max(total_weight * .62, .01))
        coverage = len(available) / len(components)
        confidence = max(0.0, min(1.0, coverage * (.55 + .45 * (1.0 - disagreement)) * (.55 + .45 * strength)))

        if disagreement >= .55:
            agreement_label = 'HIGH_DISAGREEMENT'
        elif disagreement >= .30:
            agreement_label = 'MIXED'
        elif strength >= .45 and abs(signed) >= .22:
            agreement_label = 'STRONG_AGREEMENT'
        else:
            agreement_label = 'LOW_SIGNAL'

        conflicts = []
        pos_names = [k for k, v in components.items() if v['available'] and v['signal'] >= .35]
        neg_names = [k for k, v in components.items() if v['available'] and v['signal'] <= -.35]
        if pos_names and neg_names:
            conflicts.append(f"Positive: {', '.join(pos_names)}; negative: {', '.join(neg_names)}")

        rows.append({
            'player_id': pid,
            'player': p.get('player'),
            'club': p.get('club'),
            'position': pos,
            'overall_signal': round(signed, 3),
            'direction': band(signed),
            'agreement': agreement_label,
            'disagreement_score': round(disagreement, 3),
            'confidence_score': round(confidence, 3),
            'source_coverage': round(coverage, 3),
            'components': components,
            'conflicts': conflicts,
        })

    rows.sort(key=lambda x: (x['confidence_score'], abs(x['overall_signal'])), reverse=True)
    summary = {
        'strong_agreement': sum(1 for x in rows if x['agreement'] == 'STRONG_AGREEMENT'),
        'mixed': sum(1 for x in rows if x['agreement'] == 'MIXED'),
        'high_disagreement': sum(1 for x in rows if x['agreement'] == 'HIGH_DISAGREEMENT'),
        'low_signal': sum(1 for x in rows if x['agreement'] == 'LOW_SIGNAL'),
    }
    out = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 1,
        'method_note': 'Explainable agreement layer across our model, FPL underlying data, probabilistic minutes, public Scout consensus and independent market strength. Disagreement primarily changes confidence/uncertainty; it is not a second opaque player score.',
        'summary': summary,
        'players': rows,
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', **summary}))


if __name__ == '__main__':
    main()
