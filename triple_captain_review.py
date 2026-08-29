import json
from datetime import datetime, timezone
from pathlib import Path

import simulation_engine as sim
from projection_calibration import expected_gw as calibrated_expected_gw, season_maturity

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
CHIP_WINDOW = Path('data/chip_window.json')
OUT = Path('data/triple_captain_review.json')

# Season-specific promoted clubs. Keep this explicit/auditable rather than
# inferring promotion status from weak early-season results.
PROMOTED_2627 = {'Coventry City', 'Coventry', 'Hull City', 'Hull', 'Ipswich Town', 'Ipswich'}
HORIZON = 6


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def pid(row):
    return int(row.get('player_id') or row.get('id') or row.get('element') or 0)


def fixture_for(player, gw):
    for f in player.get('fixtures') or []:
        if int(f.get('gw') or 0) == int(gw):
            return f
    return None


def latest_points_map(latest):
    return {pid(x): n(x.get('live_points')) for x in latest.get('squad') or [] if pid(x)}


def candidate_context(player, gw, mean, cv, latest_points):
    f = fixture_for(player, gw)
    if not f:
        return None
    opponent = str(f.get('opponent') or '')
    venue = str(f.get('venue') or '')
    home = venue.upper().startswith('H')
    promoted = opponent in PROMOTED_2627
    price = n(player.get('price'))
    availability = n(player.get('availability'), 1.0)
    recent = n(latest_points.get(pid(player))) if gw == CURRENT_NEXT_GW else 0.0
    difficulty = int(n(f.get('difficulty'), 3))

    # This is a context/ceiling score, not a projected FPL-point total.
    context = mean
    context += max(0, 3 - difficulty) * 0.45
    context += 0.55 if home else 0.0
    context += 1.05 if home and promoted else (0.45 if promoted else 0.0)
    context += 0.55 if price >= 12 else (0.25 if price >= 9 else 0.0)
    context += min(0.65, recent / 20.0)
    context += max(-0.8, (availability - 0.9) * 3.0)
    context -= max(0, cv - 0.8) * 0.35

    reasons = []
    if home and promoted:
        reasons.append(f'Home fixture against promoted {opponent}.')
    elif promoted:
        reasons.append(f'Fixture against promoted {opponent}.')
    elif home and difficulty <= 2:
        reasons.append('Favourable home fixture.')
    if price >= 12:
        reasons.append('Premium/high-ceiling asset already owned.')
    if recent >= 8:
        reasons.append(f'{recent:.0f} FPL points in the latest completed/live Gameweek.')
    if availability >= 0.95:
        reasons.append('Strong current minutes/availability signal.')

    tier = 'HOLD'
    if home and promoted and price >= 10 and availability >= 0.9:
        tier = 'SERIOUS'
    elif mean >= 5.5 and availability >= 0.9:
        tier = 'WATCH'

    return {
        'gw': int(gw),
        'player_id': pid(player),
        'player': player.get('player'),
        'club': player.get('club'),
        'position': player.get('position'),
        'price': round(price, 1),
        'opponent': opponent,
        'venue': venue,
        'fixture_difficulty': difficulty,
        'promoted_opponent': promoted,
        'home_vs_promoted': bool(home and promoted),
        'availability': round(availability, 3),
        'latest_gw_points': round(recent, 1) if recent else None,
        'expected_extra_tc_points': round(mean, 2),
        'projection_cv': round(cv, 3),
        'context_score': round(context, 3),
        'tier': tier,
        'reasons': reasons[:4],
    }


def main():
    global CURRENT_NEXT_GW
    latest = sim.load_json(LATEST, {})
    pool = sim.load_json(POOL, {})
    scout = sim.load_json(SCOUT, {})
    market = sim.load_json(MARKET, {})
    chip_window = sim.load_json(CHIP_WINDOW, {})
    if latest.get('status') != 'SUCCESS' or pool.get('status') != 'SUCCESS':
        raise RuntimeError('Latest/player-pool data not ready')

    current_gw = int(latest.get('current_gw') or 0)
    CURRENT_NEXT_GW = int(latest.get('next_gw') or current_gw + 1)
    maturity = season_maturity(current_gw)
    gws = list(range(CURRENT_NEXT_GW, CURRENT_NEXT_GW + HORIZON))

    pool_rows = [x for x in pool.get('players') or [] if pid(x)]
    by_id = {pid(x): x for x in pool_rows}
    owned_raw = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    owned = [by_id.get(pid(x), x) for x in owned_raw if pid(x)]
    latest_pts = latest_points_map(latest)

    scout_maps = sim.scout_lookup(scout)
    market_maps = sim.market_lookup(market)
    model_vals = [n(x.get('six_gw_score')) for x in pool_rows]
    lo, hi = sim.percentile(model_vals, .10), sim.percentile(model_vals, .90)

    candidates = []
    for gw in gws:
        for player in owned:
            if player.get('position') == 'GKP':
                continue
            mean, cv = calibrated_expected_gw(
                player, gw, lo, hi, scout_maps, market_maps, current_gw=current_gw
            )
            row = candidate_context(player, gw, n(mean), n(cv, .85), latest_pts)
            if row:
                candidates.append(row)

    candidates.sort(key=lambda x: (x['context_score'], x['expected_extra_tc_points']), reverse=True)
    current = [x for x in candidates if x['gw'] == CURRENT_NEXT_GW]
    future = [x for x in candidates if x['gw'] > CURRENT_NEXT_GW]
    current_best = current[0] if current else None
    future_best = future[0] if future else None
    best_visible = candidates[0] if candidates else None

    pressure = (chip_window.get('portfolio') or {}).get('pressure', 'comfortable')
    expiry = (chip_window.get('portfolio') or {}).get('expires_after_gw', 19 if CURRENT_NEXT_GW <= 19 else 38)
    latest_safe_start = (chip_window.get('portfolio') or {}).get('latest_safe_start_gw')

    status = 'HOLD'
    reasons_for = []
    reasons_wait = []
    if current_best:
        reasons_for.extend(current_best.get('reasons') or [])
        if current_best['tier'] == 'SERIOUS':
            status = 'CONSIDER'
        elif current_best['tier'] == 'WATCH':
            status = 'WATCH'
        if future_best and current_best['context_score'] < future_best['context_score'] * 0.88:
            status = 'WATCH' if status == 'CONSIDER' else status
            reasons_wait.append(f'A stronger visible owned-player TC context currently appears in GW{future_best["gw"]}.')
    if pressure == 'comfortable':
        reasons_wait.append('The first-half chip portfolio still has comfortable calendar slack.')
    reasons_wait.append('The visible horizon cannot yet price future double-Gameweek-quality opportunities with confidence.')
    if maturity < .5:
        reasons_wait.append(f'Season evidence is still only {round(maturity*100)}%, so early projections remain deliberately shrunk.')

    # Surface Haaland specifically when owned, because a premium home fixture
    # versus a promoted club is a legitimate TC archetype even if another model
    # candidate narrowly leads on mean projection.
    haaland = next((x for x in current if str(x.get('player')).lower() == 'haaland'), None)

    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 1,
        'current_gw': current_gw,
        'next_gw': CURRENT_NEXT_GW,
        'season_maturity_weight': round(maturity, 3),
        'decision': {
            'status': status,
            'candidate': current_best,
            'haaland_current_gw': haaland,
            'best_visible': best_visible,
            'best_future': future_best,
            'reasons_for_now': reasons_for[:4],
            'reasons_to_wait': reasons_wait[:4],
            'portfolio_pressure': pressure,
            'expires_after_gw': expiry,
            'latest_safe_start_gw': latest_safe_start,
        },
        'current_gw_shortlist': current[:4],
        'visible_windows': candidates[:12],
        'method_note': 'Owned-squad Triple Captain opportunity scan. It evaluates every owned outfield player across the visible horizon using season-maturity-calibrated expected return plus transparent fixture/ceiling context. expected_extra_tc_points is the extra return from tripling rather than normally captaining that player; context_score is a ranking aid, not an FPL-point forecast. CONSIDER still preserves future-chip option value and is not an automatic activation instruction.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'decision': status, 'candidate': current_best, 'haaland': haaland}))


if __name__ == '__main__':
    main()
