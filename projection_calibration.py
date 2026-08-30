import json
import math
from pathlib import Path

MARKET_STRENGTH = Path('data/market_strength.json')


def n(v, d=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else d
    except Exception:
        return d


def norm(s):
    return str(s or '').strip().lower()


def fixture(player, gw):
    return next((f for f in (player.get('fixtures') or []) if int(f.get('gw') or -1) == int(gw)), None)


def season_maturity(current_gw):
    """0..1 evidence weight. Intentionally conservative in the opening weeks."""
    gw = max(0, int(current_gw or 0))
    return max(0.18, min(0.90, gw / (gw + 6.0)))


def market_strength_map():
    """Optional independent fixture-strength signal.

    Missing/stale/unmatched market data must never break the projection stack.
    """
    try:
        data = json.loads(MARKET_STRENGTH.read_text())
    except Exception:
        return {}
    out = {}
    for row in data.get('fixtures') or []:
        home, away = norm(row.get('home_team')), norm(row.get('away_team'))
        if not home or not away:
            continue
        out[(home, away)] = {
            'home': max(.90, min(1.10, n(row.get('home_market_strength_modifier'), 1.0))),
            'away': max(.90, min(1.10, n(row.get('away_market_strength_modifier'), 1.0))),
            'home_win_prob': n(row.get('home_win_prob'), .0),
            'draw_prob': n(row.get('draw_prob'), .0),
            'away_win_prob': n(row.get('away_win_prob'), .0),
            'over_2_5_prob': n(row.get('over_2_5_prob'), .5),
        }
    return out


_MARKET_STRENGTH_MAP = market_strength_map()


def fixture_market_signal(player, f, maturity):
    club = norm(player.get('club'))
    opponent = norm(f.get('opponent'))
    venue = str(f.get('venue') or '').upper()
    if not club or not opponent or venue not in ('H', 'A'):
        return 1.0, None
    key = (club, opponent) if venue == 'H' else (opponent, club)
    row = _MARKET_STRENGTH_MAP.get(key)
    if not row:
        return 1.0, None
    raw = row['home'] if venue == 'H' else row['away']
    # The external market is an independent calibration check, not ground truth.
    # Even late season only 55% of its already-bounded 0.90..1.10 move is admitted.
    evidence = max(.20, min(.55, .28 + maturity * .27))
    factor = 1.0 + (raw - 1.0) * evidence
    return max(.94, min(1.06, factor)), row


def expected_gw(player, gw, model_lo, model_hi, scout_maps, market_maps, current_gw=2):
    f = fixture(player, gw)
    if not f:
        return 0.0, 0.0

    pos = player.get('position')
    pos_base = {'GKP': 3.1, 'DEF': 3.3, 'MID': 3.7, 'FWD': 3.9}.get(pos, 3.5)
    maturity = season_maturity(current_gw)
    source_rel = max(.08, min(.70, n(player.get('sample_reliability'), .30)))

    observed_weight = min(.62, source_rel * (.35 + .65 * maturity))
    ppg = max(0.0, min(10.0, n(player.get('points_per_game'), pos_base)))
    base = pos_base * (1.0 - observed_weight) + ppg * observed_weight

    model = n(player.get('six_gw_score'), model_lo)
    model_pct = .5 if model_hi <= model_lo else max(0.0, min(1.0, (model - model_lo) / (model_hi - model_lo)))
    raw_model_factor = .88 + model_pct * .24
    model_evidence = max(.12, min(.75, maturity * (.55 + .45 * source_rel)))
    model_factor = 1.0 + (raw_model_factor - 1.0) * model_evidence

    diff = n(f.get('difficulty'), 3)
    fixture_factor = max(.72, min(1.30, 1 + (3 - diff) * .105 + (.04 if f.get('venue') == 'H' else 0)))
    avail = max(0.0, min(1.0, n(player.get('adjusted_availability', player.get('availability')), 1)))
    sched = max(.78, min(1.04, n(player.get('schedule_modifier'), 1)))

    xmins = max(8.0, min(90.0, n(player.get('expected_minutes'), 68.0)))
    minutes_factor = max(.58, min(1.08, xmins / 72.0))
    minutes_evidence = max(.20, min(.78, source_rel * (.70 + .30 * maturity)))
    minutes_factor = 1.0 + (minutes_factor - 1.0) * minutes_evidence

    xgi90 = max(0.0, min(1.8, n(player.get('expected_goal_involvements_per_90'), 0.0)))
    xgi_prior = {'GKP': .01, 'DEF': .10, 'MID': .30, 'FWD': .42}.get(pos, .25)
    xgi_delta = max(-.25, min(.50, xgi90 - xgi_prior))
    underlying_raw = 1.0 + xgi_delta * .20
    underlying_evidence = max(.10, min(.70, maturity * (.45 + .55 * source_rel)))
    underlying_factor = 1.0 + (underlying_raw - 1.0) * underlying_evidence

    sid, sname = scout_maps
    scout = sid.get(int(player.get('player_id') or 0)) or sname.get(norm(player.get('player'))) or {}
    merit = norm(scout.get('merit'))
    scout_factor = 1.0
    if any(x in merit for x in ('strong', 'reinforces')):
        scout_factor += .025
    elif 'worth investigating' in merit:
        scout_factor += .012
    if any(x in merit for x in ('avoid', 'concern', 'sell')):
        scout_factor -= .045

    independent_factor, independent = fixture_market_signal(player, f, maturity)
    mean = base * model_factor * fixture_factor * avail * sched * minutes_factor * underlying_factor * scout_factor * independent_factor

    cv = .86 - maturity * .13 - source_rel * .10
    if xmins < 55:
        cv += .10
    elif xmins < 68:
        cv += .045
    elif xmins >= 80:
        cv -= .02
    risk = norm(player.get('schedule_risk'))
    if risk == 'high':
        cv += .12
    elif risk == 'medium':
        cv += .05
    if not player.get('player_workload_observed', False):
        cv += .04
    mid, mname = market_maps
    market = mid.get(int(player.get('player_id') or 0)) or mname.get(norm(player.get('player'))) or {}
    if 'strong_' in norm(market.get('market_status')):
        cv += .02

    # Disagreement between FPL fixture difficulty and the independent market is itself uncertainty.
    if independent:
        fpl_direction = 3.0 - diff + (.35 if f.get('venue') == 'H' else 0)
        market_direction = independent_factor - 1.0
        if (fpl_direction > .35 and market_direction < -.012) or (fpl_direction < -.35 and market_direction > .012):
            cv += .035

    return max(0.0, mean), max(.42, min(1.15, cv))
