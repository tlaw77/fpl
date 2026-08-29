"""Shared captaincy decision model used by review and simulation layers."""


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


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
    fixture = fixture if fixture is not None else first_fixture(player, 0)
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


def ranked_candidates(squad, xi_ids, gw, exp_for_gw):
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
    return rows


def choose_captain(squad, xi_ids, gw, exp_for_gw):
    ranked = ranked_candidates(squad, xi_ids, gw, exp_for_gw)
    return ranked[0]['player_id'] if ranked else 0
