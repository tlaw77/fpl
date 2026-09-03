import json
from copy import deepcopy

import path_simulation as p
import path_simulation_v3 as v3


def enhanced_transfer_candidates(state, remaining_gws, pool_rows, exp, limit=10):
    """Keep normal positive-uplift moves plus a small set of budget enablers.

    An enabler may be slightly negative on its own across the immediate horizon,
    but releases enough bank to let the beam discover a stronger premium move in
    a later GW. Final Monte Carlo utility still decides whether the complete path
    is worthwhile, so bank creation alone cannot become a recommendation.
    """
    squad = state['squad']
    owned = {p.pid(x) for x in squad}
    bank = state['bank']
    ranked_by_pos = {}
    for pos in ('GKP', 'DEF', 'MID', 'FWD'):
        rows = [
            x for x in pool_rows
            if x.get('position') == pos
            and p.pid(x) not in owned
            and p.n(x.get('adjusted_availability', x.get('availability')), 1) >= .55
        ]
        rows.sort(
            key=lambda x: sum(exp.get(g, {}).get(p.pid(x), (0, 0))[0] for g in remaining_gws),
            reverse=True,
        )
        # Search deeper down the cheap end as well as the normal top projected players.
        top = rows[:p.INCOMING_PER_POSITION]
        cheap = sorted(rows, key=lambda x: (p.price(x), -p.n(x.get('six_gw_score'))))[:6]
        seen = set()
        ranked_by_pos[pos] = [x for x in top + cheap if not (p.pid(x) in seen or seen.add(p.pid(x)))]

    base = p.horizon_value(squad, remaining_gws, exp)
    normal, enablers = [], []
    for out_p in squad:
        for in_p in ranked_by_pos.get(out_p.get('position'), []):
            if p.price(in_p) > p.price(out_p) + bank + 1e-9:
                continue
            new = p.replace_player(squad, out_p, in_p)
            if not new:
                continue
            val = p.horizon_value(new, remaining_gws, exp)
            uplift = val - base
            bank_released = p.price(out_p) - p.price(in_p)
            row = {
                'out': out_p,
                'in': in_p,
                'squad': new,
                'bank': round(bank + bank_released, 2),
                'uplift': uplift,
                'label': f"{out_p.get('player')} → {in_p.get('player')}",
                'enabler': False,
                'bank_released': round(max(0, bank_released), 2),
            }
            if uplift > .15:
                normal.append(row)
            # Preserve a few structurally plausible downgrades even when their own
            # projection is slightly worse. The later premium upgrade must rescue them.
            elif bank_released >= .8 and uplift >= -2.75:
                row['enabler'] = True
                row['enabler_search_score'] = round(uplift + min(2.8, bank_released * .9), 3)
                enablers.append(row)

    normal.sort(key=lambda x: x['uplift'], reverse=True)
    enablers.sort(key=lambda x: (x.get('enabler_search_score', -99), x['bank_released']), reverse=True)
    enabler_slots = min(3, max(1, limit // 4))
    picked = normal[:max(0, limit - enabler_slots)] + enablers[:enabler_slots]
    # If there are few normal candidates, fill remaining slots with either type.
    if len(picked) < limit:
        used = {(p.pid(x['out']), p.pid(x['in'])) for x in picked}
        rest = [x for x in normal + enablers if (p.pid(x['out']), p.pid(x['in'])) not in used]
        rest.sort(key=lambda x: x['uplift'] + (min(2.0, x['bank_released'] * .6) if x.get('enabler') else 0), reverse=True)
        picked.extend(rest[:limit-len(picked)])
    return picked[:limit]


def enhanced_expand_state(state, gw, gws, pool_rows, exp):
    remaining = [x for x in gws if x >= gw]
    children = []

    roll = deepcopy(state)
    roll['actions'] = state['actions'] + [{'gw': gw, 'action': 'ROLL'}]
    roll['ft'] = min(p.MAX_FT, state['ft'] + 1)
    p.record_snapshot(roll, gw)
    gw_score, _, _ = p.lineup_expected(roll['squad'], gw, exp)
    roll['det_points'] = state['det_points'] + gw_score
    roll['search_score'] = roll['det_points'] + p.horizon_value(roll['squad'], remaining[1:], exp) + .45 * roll['ft']
    children.append(roll)

    for m in enhanced_transfer_candidates(state, remaining, pool_rows, exp):
        child = deepcopy(state)
        child['squad'] = m['squad']
        child['bank'] = m['bank']
        hit = 0 if state['ft'] >= 1 else 4
        ft_after = max(0, state['ft'] - 1)
        child['ft'] = min(p.MAX_FT, ft_after + 1)
        child['actions'] = state['actions'] + [{
            'gw': gw,
            'action': 'TRANSFER',
            'route': m['label'],
            'hit': hit,
            'out_id': p.pid(m['out']),
            'in_id': p.pid(m['in']),
            'enabler': bool(m.get('enabler')),
            'bank_released': m.get('bank_released', 0),
        }]
        p.record_snapshot(child, gw)
        gw_score, _, _ = p.lineup_expected(child['squad'], gw, exp)
        child['det_points'] = state['det_points'] + gw_score - hit
        keep_alive_bonus = min(2.5, p.n(m.get('bank_released')) * .75) if m.get('enabler') else 0
        child['search_score'] = child['det_points'] + p.horizon_value(child['squad'], remaining[1:], exp) + .45 * child['ft'] - hit + keep_alive_bonus
        children.append(child)
    return children


def annotate_output():
    if not p.OUT.exists():
        return
    data = json.loads(p.OUT.read_text())
    data['engine_version'] = max(7, int(data.get('engine_version') or 0))
    data['planner'] = str(data.get('planner') or '') + ' + enabling-downgrade retention'
    data['method_note'] = (
        str(data.get('method_note') or '')
        + ' A bounded set of slightly negative budget-release moves is retained in the beam so a later premium upgrade can be discovered. '
          'Those enablers receive no final-utility reward for bank alone; the complete multi-GW path must outperform on simulated points/rank.'
    )
    for path in data.get('paths') or []:
        actions = path.get('actions') or []
        enabler_idx = next((i for i, a in enumerate(actions) if a.get('enabler')), None)
        if enabler_idx is None:
            path['contains_enabler'] = False
            continue
        later = next((a for a in actions[enabler_idx + 1:] if a.get('action') == 'TRANSFER'), None)
        first = actions[enabler_idx]
        path['contains_enabler'] = True
        path['unlock_sequence'] = {
            'enabler_gw': first.get('gw'),
            'enabler_route': first.get('route'),
            'bank_released': first.get('bank_released', 0),
            'follow_up_gw': later.get('gw') if later else None,
            'follow_up_route': later.get('route') if later else None,
            'completed_unlock': bool(later),
        }
    rec = data.get('recommendation') or {}
    if rec:
        match = next((x for x in data.get('paths', []) if x.get('actions') == rec.get('actions')), None)
        if match:
            rec['contains_enabler'] = match.get('contains_enabler', False)
            rec['unlock_sequence'] = match.get('unlock_sequence')
    p.OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def run():
    p.transfer_candidates = enhanced_transfer_candidates
    p.expand_state = enhanced_expand_state
    v3.run()
    annotate_output()


if __name__ == '__main__':
    run()
