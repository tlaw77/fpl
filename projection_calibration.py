import math


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
    # GW2 ~= 0.25, GW5 ~= 0.45, GW8 ~= 0.62, GW12 ~= 0.76.
    return max(0.18, min(0.90, gw / (gw + 6.0)))


def expected_gw(player, gw, model_lo, model_hi, scout_maps, market_maps, current_gw=2):
    f = fixture(player, gw)
    if not f:
        return 0.0, 0.0

    pos_base = {'GKP': 3.1, 'DEF': 3.3, 'MID': 3.7, 'FWD': 3.9}.get(player.get('position'), 3.5)
    maturity = season_maturity(current_gw)
    source_rel = max(.08, min(.70, n(player.get('sample_reliability'), .30)))

    # Observed PPG is useful, but in the opening weeks it must not swamp the prior.
    observed_weight = min(.62, source_rel * (.35 + .65 * maturity))
    ppg = max(0.0, min(10.0, n(player.get('points_per_game'), pos_base)))
    base = pos_base * (1.0 - observed_weight) + ppg * observed_weight

    # six_gw_score contributes rank information, but its extremity is shrunk by maturity.
    model = n(player.get('six_gw_score'), model_lo)
    model_pct = .5 if model_hi <= model_lo else max(0.0, min(1.0, (model - model_lo) / (model_hi - model_lo)))
    raw_model_factor = .88 + model_pct * .24  # unshrunk range 0.88..1.12
    model_evidence = max(.12, min(.75, maturity * (.55 + .45 * source_rel)))
    model_factor = 1.0 + (raw_model_factor - 1.0) * model_evidence

    diff = n(f.get('difficulty'), 3)
    fixture_factor = max(.72, min(1.30, 1 + (3 - diff) * .105 + (.04 if f.get('venue') == 'H' else 0)))
    avail = max(0.0, min(1.0, n(player.get('adjusted_availability', player.get('availability')), 1)))
    sched = max(.78, min(1.04, n(player.get('schedule_modifier'), 1)))

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

    mean = base * model_factor * fixture_factor * avail * sched * scout_factor

    # Opening-week uncertainty remains wide even though the mean is shrunk.
    cv = .86 - maturity * .13 - source_rel * .10
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

    return max(0.0, mean), max(.42, min(1.15, cv))
