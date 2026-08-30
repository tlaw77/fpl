"""Shared captaincy decision model used by review and simulation layers."""


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(v)))


def pid(p):
    return int((p or {}).get('player_id') or (p or {}).get('id') or 0)


def first_fixture(player, gw):
    for f in (player or {}).get('fixtures') or []:
        if int(f.get('gw') or 0) == int(gw):
            return f
    return ((player or {}).get('fixtures') or [None])[0]


def position_ceiling(pos):
    return {'GKP': .76, 'DEF': .88, 'MID': 1.08, 'FWD': 1.12}.get(pos, 1.0)


def premium_bonus(player):
    price = n((player or {}).get('price'))
    pos = (player or {}).get('position')
    threshold = {'GKP': 5.0, 'DEF': 6.0, 'MID': 8.5, 'FWD': 9.0}.get(pos, 99)
    return .65 if price >= threshold else 0


def captain_score(player, mean, cv, fixture=None):
    venue = str((fixture or {}).get('venue') or '').upper()
    fdr = n((fixture or {}).get('difficulty'), 3)
    form = n((player or {}).get('form'))
    ppg = n((player or {}).get('points_per_game'))
    avail = n((player or {}).get('availability'), 1)
    price = n((player or {}).get('price'))
    score = n(mean) * position_ceiling((player or {}).get('position'))
    score += max(0, 4 - fdr) * .42
    score += .35 if venue == 'H' else 0
    score += min(1.2, form * .08)
    score += min(1.0, ppg * .07)
    score += premium_bonus(player)
    score += min(.45, max(0, price - 10) * .04)
    score += avail * .5
    score -= max(0, n(cv, .8) - .8) * 1.4
    return score


def build_league_context(latest, current_gw):
    """Build a bounded captaincy game-state context from live mini-league data."""
    latest = latest or {}
    stage = clamp(n(current_gw) / 38.0)
    me = latest.get('me') or {}
    rank = int(me.get('rank') or 1)
    my_points = n(me.get('total_points'))
    rivals = latest.get('rivals') or []
    rival_points = [n(x.get('total_points')) for x in rivals]
    leader_points = max([my_points, *rival_points], default=my_points)
    gap = max(0.0, leader_points - my_points)
    remaining = max(1, 38 - int(current_gw or 0))
    chase_rate = gap / remaining

    if rank == 1:
        posture = 'PROTECT_EDGE'
    elif chase_rate >= 2.0:
        posture = 'CHASE'
    elif chase_rate >= .8:
        posture = 'CONTROLLED_CHASE'
    else:
        posture = 'BALANCED'

    exposure = {}
    for row in latest.get('player_exposure') or []:
        player_id = int(row.get('player_id') or 0)
        if player_id:
            exposure[player_id] = {
                'ownership_pct': n(row.get('ownership_pct')),
                'effective_ownership_pct': n(row.get('effective_ownership_pct')),
                'classification': row.get('classification'),
            }

    return {
        'season_stage': round(stage, 3),
        'rank': rank,
        'gap_to_leader': round(gap, 2),
        'required_gain_per_remaining_gw': round(chase_rate, 3),
        'posture': posture,
        'exposure': exposure,
    }


def ranked_candidates(squad, xi_ids, gw, exp_for_gw, league_context=None):
    allowed = {int(x) for x in xi_ids}
    rows = []
    for player in squad:
        player_id = pid(player)
        if not player_id or player_id not in allowed:
            continue
        mean, cv = exp_for_gw.get(player_id, (0.0, 1.0))
        fixture = first_fixture(player, gw)
        rows.append({
            'player': player,
            'player_id': player_id,
            'mean': n(mean),
            'cv': n(cv, 1.0),
            'fixture': fixture,
            'captaincy_score': captain_score(player, mean, cv, fixture),
        })
    rows.sort(key=lambda x: (x['captaincy_score'], x['mean']), reverse=True)
    if league_context and rows:
        add_strategy_scores(rows, league_context)
    return rows


def add_strategy_scores(rows, context):
    """Attach Safe and Chase scores while preserving Best-EV as the baseline.

    Low ownership is never sufficient by itself. A chase candidate receives a
    leverage bonus only when its expected-points gap to the best-EV captain lies
    inside a season-stage-dependent tolerance.
    """
    if not rows:
        return rows
    stage = clamp(n((context or {}).get('season_stage')))
    exposure = (context or {}).get('exposure') or {}
    best_mean = max(n(x.get('mean')) for x in rows)
    ev_tolerance = .30 + 1.35 * stage

    for row in rows:
        ex = exposure.get(int(row.get('player_id') or 0)) or {}
        ownership = clamp(n(ex.get('ownership_pct')) / 100.0)
        eo = clamp(n(ex.get('effective_ownership_pct')) / 100.0)
        shield = max(ownership, min(1.0, eo))
        leverage = 1.0 - ownership
        mean_gap = max(0.0, best_mean - n(row.get('mean')))
        chase_eligible = mean_gap <= ev_tolerance

        # Strategy influence is almost zero early season and intentionally bounded.
        safe_bonus = stage * (.55 * shield - .12 * leverage)
        chase_bonus = stage * (.72 * leverage - .10 * shield) if chase_eligible else -min(1.6, mean_gap * .9)

        row['mini_league_ownership_pct'] = round(ownership * 100, 1)
        row['mini_league_effective_ownership_pct'] = round(eo * 100, 1)
        row['ev_gap_to_best'] = round(mean_gap, 3)
        row['chase_eligible'] = bool(chase_eligible)
        row['safe_score'] = round(n(row.get('captaincy_score')) + safe_bonus, 4)
        row['chase_score'] = round(n(row.get('captaincy_score')) + chase_bonus, 4)
    return rows


def captain_modes(rows, league_context=None):
    if not rows:
        return {'BEST_EV': None, 'SAFE': None, 'CHASE': None, 'recommended_mode': 'BEST_EV', 'recommended': None}
    context = league_context or {}
    if not all('safe_score' in x for x in rows):
        add_strategy_scores(rows, context)
    best_ev = max(rows, key=lambda x: (n(x.get('captaincy_score')), n(x.get('mean'))))
    safe = max(rows, key=lambda x: (n(x.get('safe_score')), n(x.get('mean'))))
    chase_pool = [x for x in rows if x.get('chase_eligible')]
    chase = max(chase_pool or rows, key=lambda x: (n(x.get('chase_score')), n(x.get('mean'))))

    stage = clamp(n(context.get('season_stage')))
    posture = str(context.get('posture') or 'BALANCED')
    recommended_mode = 'BEST_EV'
    if stage >= .35 and posture == 'PROTECT_EDGE':
        recommended_mode = 'SAFE'
    elif stage >= .35 and posture == 'CHASE':
        recommended_mode = 'CHASE'
    elif stage >= .55 and posture == 'CONTROLLED_CHASE':
        recommended_mode = 'CHASE'
    recommended = {'BEST_EV': best_ev, 'SAFE': safe, 'CHASE': chase}[recommended_mode]
    return {
        'BEST_EV': best_ev,
        'SAFE': safe,
        'CHASE': chase,
        'recommended_mode': recommended_mode,
        'recommended': recommended,
    }


def choose_captain(squad, xi_ids, gw, exp_for_gw, league_context=None):
    ranked = ranked_candidates(squad, xi_ids, gw, exp_for_gw, league_context=league_context)
    if not ranked:
        return 0
    if league_context:
        modes = captain_modes(ranked, league_context)
        return int((modes.get('recommended') or ranked[0]).get('player_id') or 0)
    return ranked[0]['player_id']


def lineup_expected(path_module, squad, gw, exp, league_context=None):
    """Legal XI from the existing lineup optimiser + captain from this shared model."""
    means = {k: v[0] for k, v in exp.get(gw, {}).items()}
    xi, _ = path_module.best_xi(squad, means)
    ids = [path_module.pid(p) for p in xi]
    cap_id = choose_captain(squad, ids, gw, exp.get(gw, {}), league_context=league_context)
    score = sum(means.get(x, 0) for x in ids) + means.get(cap_id, 0)
    return score, ids, cap_id
