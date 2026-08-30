import json
from datetime import datetime, timezone
from pathlib import Path

import simulation_engine as s
from projection_calibration import expected_gw as calibrated_expected_gw, season_maturity

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
CONSENSUS = Path('data/signal_consensus.json')
OUT = Path('data/projection_snapshot.json')
HISTORY = Path('data/projection_history')


def load(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if default is None else default


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def main():
    latest = load(LATEST)
    pool = load(POOL, {'players': []})
    scout = load(SCOUT, {'players': []})
    market = load(MARKET, {'players': []})
    consensus = load(CONSENSUS, {'players': []})

    if latest.get('status') != 'SUCCESS':
        raise RuntimeError('latest.json is not ready')
    current_gw = int(latest.get('current_gw') or 0)
    target_gw = int(latest.get('next_gw') or current_gw + 1)
    rows = [p for p in pool.get('players') or [] if int(p.get('player_id') or 0)]
    if not rows:
        raise RuntimeError('player_pool.json is empty')

    values = [n(p.get('six_gw_score')) for p in rows]
    lo, hi = s.percentile(values, .10), s.percentile(values, .90)
    scout_maps = s.scout_lookup(scout)
    market_maps = s.market_lookup(market)
    consensus_map = {int(x.get('player_id') or 0): x for x in consensus.get('players') or [] if x.get('player_id')}

    projections = []
    for p in rows:
        pid = int(p.get('player_id') or 0)
        mean, cv = calibrated_expected_gw(p, target_gw, lo, hi, scout_maps, market_maps, current_gw=current_gw)
        c = consensus_map.get(pid) or {}
        projections.append({
            'player_id': pid,
            'player': p.get('player'),
            'club': p.get('club'),
            'position': p.get('position'),
            'price': n(p.get('price')),
            'target_gw': target_gw,
            'expected_points': round(mean, 4),
            'projection_cv': round(cv, 4),
            'projection_sd': round(mean * cv, 4),
            'expected_minutes': n(p.get('expected_minutes')),
            'prob_appearance': n(p.get('prob_appearance')),
            'prob_start': n(p.get('prob_start')),
            'prob_cameo': n(p.get('prob_cameo')),
            'prob_60_plus': n(p.get('prob_60_plus')),
            'prob_80_plus': n(p.get('prob_80_plus')),
            'minutes_band': p.get('minutes_band'),
            'minutes_confidence': p.get('minutes_confidence'),
            'xgi_per_90': n(p.get('expected_goal_involvements_per_90')),
            'signal_agreement': c.get('agreement'),
            'signal_disagreement_score': n(c.get('disagreement_score')),
            'signal_confidence_score': n(c.get('confidence_score')),
            'sample_reliability': n(p.get('sample_reliability')),
            'availability': n(p.get('adjusted_availability', p.get('availability')), 1.0),
        })

    projections.sort(key=lambda x: x['expected_points'], reverse=True)
    output = {
        'status': 'SUCCESS',
        'version': 2,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'decision_gw': current_gw,
        'target_gw': target_gw,
        'season_maturity_weight': round(season_maturity(current_gw), 4),
        'player_count': len(projections),
        'projection_model': 'season-maturity calibrated + probabilistic xMins + signal disagreement + independent market where available',
        'calibration_contract': {
            'hindsight_safe_target_history': True,
            'expected_points_field': 'expected_points',
            'uncertainty_fields': ['projection_cv', 'projection_sd'],
            'minutes_probability_fields': ['prob_appearance', 'prob_start', 'prob_60_plus', 'prob_80_plus'],
            'outcome_source': 'archived FPL all-player event outcomes',
            'freeze_rule': 'projection_history/gwN.json is refreshed only while N is the next future GW. Once current_gw advances to N, subsequent ETL writes target N+1, leaving the final pre-GW N forecast untouched.',
            'note': 'This supports forecast-vs-outcome calibration without hindsight reconstruction.',
        },
        'players': projections,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    HISTORY.mkdir(parents=True, exist_ok=True)
    frozen = HISTORY / f'gw{target_gw}.json'
    frozen.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'target_gw': target_gw, 'players': len(projections), 'history_path': str(frozen)}))


if __name__ == '__main__':
    main()
