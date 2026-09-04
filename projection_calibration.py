import math


def n(v, d=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else d
    except Exception:
        return d


def norm(s):
    return str(s or '').strip().lower()


def fixtures_for_gw(player, gw):
    """Return every scheduled fixture for the player in a Gameweek.

    FPL can assign more than one Premier League fixture to the same event during a
    Double Gameweek. Older callers used only the first match, which understated a
    confirmed DGW. Keep the list ordered by kickoff where the feed provides it.
    """
    rows = [f for f in (player.get('fixtures') or []) if int(f.get('gw') or -1) == int(gw)]
    return sorted(rows, key=lambda f: str(f.get('kickoff_time') or ''))


def fixture(player, gw):
    """Backward-compatible first-fixture helper for display-only callers."""
    rows = fixtures_for_gw(player, gw)
    return rows[0] if rows else None


def season_maturity(current_gw):
    """0..1 evidence weight. Intentionally conservative in the opening weeks."""
    gw = max(0, int(current_gw or 0))
    # GW2 ~= 0.25, GW5 ~= 0.45, GW8 ~= 0.62, GW12 ~= 0.76.
    return max(0.18, min(0.90, gw / (gw + 6.0)))


def expected_gw(player, gw, model_lo, model_hi, scout_maps, market_maps, current_gw=2):
    fixtures = fixtures_for_gw(player, gw)
    if not fixtures:
        return 0.0, 0.0

    pos_base = {'GKP': 3.1, 'DEF': 3.3, 'MID': 3.7, 'FWD': 3.9}.get(player.get('position'), 3.5)
    maturity = season_maturity(current_gw)
    source_rel = max(.08, min(.70, n(player.get('sample_reliability'), .30)))

    # Observed PPG is useful, but in the opening weeks it must not swamp the prior.
    observed_weight = min(.62, source_rel * (.35 + .65 * maturity))
    ppg = max(0.0, min(10.0, n(player.get('points_per_game'), pos_base)))
    base = pos_base * (1.0 - observed_weight) + ppg * observed_weight

    # Defensive contribution is already partly embedded in PPG. Only the player's
    # edge versus their positional peers is added, heavily shrunk early in season.
    dc_edge = max(-.65, min(.65, n(player.get('defcon_edge_per_90'), 0.0)))
    dc_evidence = source_rel * (.30 + .70 * maturity)
    dc_adjustment = max(-.45, min(.45, dc_edge * dc_evidence))
    base += dc_adjustment

    # six_gw_score contributes rank information, but its extremity is shrunk by maturity.
    model = n(player.get('six_gw_score'), model_lo)
    model_pct = .5 if model_hi <= model_lo else max(0.0, min(1.0, (model - model_lo) / (model_hi - model_lo)))
    raw_model_factor = .88 + model_pct * .24
    model_evidence = max(.12, min(.75, maturity * (.55 + .45 * source_rel)))
    model_factor = 1.0 + (raw_model_factor - 1.0) * model_evidence

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

    # Score each confirmed PL fixture independently. For a DGW we conservatively
    # haircut later fixtures for rotation/minutes risk rather than assuming two full
    # 90-minute appearances. This preserves almost identical SGW behaviour while
    # making confirmed doubles visible to transfers, captaincy and chip optimisation.
    risk = norm(player.get('schedule_risk'))
    later_fixture_factor = .92
    if risk == 'medium':
        later_fixture_factor = .86
    elif risk == 'high':
        later_fixture_factor = .76
    if avail < .85:
        later_fixture_factor *= max(.72, avail / .85)

    fixture_means = []
    for idx, f in enumerate(fixtures):
        diff = n(f.get('difficulty'), 3)
        ff = max(.72, min(1.30, 1 + (3 - diff) * .105 + (.04 if f.get('venue') == 'H' else 0)))
        minutes_factor = 1.0 if idx == 0 else later_fixture_factor
        fixture_means.append(base * model_factor * ff * avail * sched * scout_factor * minutes_factor)
    mean = sum(fixture_means)

    # Reliable DC floor slightly reduces volatility for outfield players who project
    # materially above their positional peers, without changing their ceiling directly.
    cv = .86 - maturity * .13 - source_rel * .10
    if dc_edge > .18:
        cv -= min(.055, dc_edge * dc_evidence * .08)
    elif dc_edge < -.18:
        cv += min(.035, abs(dc_edge) * dc_evidence * .05)
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

    # Multiple scoring opportunities reduce pure match-result variance, but rotation
    # correlation means the reduction should be much smaller than sqrt(n).
    if len(fixtures) >= 2:
        cv *= .90 if risk == 'high' else (.86 if risk == 'medium' else .82)

    return max(0.0, mean), max(.38 if len(fixtures) >= 2 else .42, min(1.15, cv))
