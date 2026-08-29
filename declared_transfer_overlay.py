import json
from datetime import datetime, timezone
from pathlib import Path

import current_squad as cs

LATEST = Path('data/latest.json')
DECLARED = Path('data/declared_transfers.json')


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def tx_key(t):
    return (int(t.get('event') or 0), int(t.get('element_out') or 0), int(t.get('element_in') or 0))


def set_transfer_state(data, transfers, starting_ft=1):
    used = len([t for t in transfers if int(t.get('event') or 0) == int(data.get('next_gw') or 0)])
    remaining = max(0, int(starting_ft) - used)
    excess = max(0, used - int(starting_ft))
    data['free_transfers_available_before_moves'] = int(starting_ft)
    data['free_transfers_used_next_gw'] = min(used, int(starting_ft))
    data['free_transfers_remaining_next_gw'] = remaining
    data['transfer_hits_already_incurred_next_gw'] = excess * 4
    data['next_transfer_hit_cost'] = 0 if remaining > 0 else 4


def main():
    data = load(LATEST, {})
    declared = load(DECLARED, {'transfers': []})
    next_gw = int(data.get('next_gw') or 0)
    if not next_gw:
        print(json.dumps({'status': 'SKIP', 'reason': 'no next_gw'}))
        return

    official = data.get('current_squad_transfers') or []
    official_keys = {tx_key(t) for t in official}
    pending = [t for t in (declared.get('transfers') or []) if int(t.get('event') or 0) == next_gw and tx_key(t) not in official_keys]

    if not pending:
        all_current = [t for t in official if int(t.get('event') or 0) == next_gw]
        set_transfer_state(data, all_current, starting_ft=1)
        data['declared_transfer_overlay_status'] = 'resolved_official' if any(int(t.get('event') or 0) == next_gw for t in (declared.get('transfers') or [])) else 'none'
        data['declared_transfer_overlay_generated_at_utc'] = datetime.now(timezone.utc).isoformat()
        LATEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
        print(json.dumps({'status': 'SUCCESS', 'pending_applied': 0, 'overlay_status': data['declared_transfer_overlay_status'], 'remaining_ft': data['free_transfers_remaining_next_gw']}))
        return

    bootstrap = cs.get_json(f'{cs.BASE}/bootstrap-static/')
    fixtures = cs.get_json(f'{cs.BASE}/fixtures/')
    raw_players = {p['id']: p for p in bootstrap['elements']}
    teams = {t['id']: t['name'] for t in bootstrap['teams']}
    positions = {p['id']: p['singular_name_short'] for p in bootstrap['element_types']}
    fixture_map = cs.fixtures_by_team(fixtures, teams, next_gw, 5)
    expo, target_own, target_cap, target_n = cs.exposure_maps(data)

    base = [dict(p) for p in (data.get('current_squad_next5') or data.get('squad_next5') or [])]
    by_id = {int(p['player_id']): p for p in base if p.get('player_id')}
    bank = float(data.get('current_bank', data.get('me', {}).get('bank', 0)) or 0)
    applied = []

    for t in sorted(pending, key=lambda x: x.get('declared_at_utc') or ''):
        out_id = int(t.get('element_out') or 0)
        in_id = int(t.get('element_in') or 0)
        out = by_id.pop(out_id, None)
        if out is None or in_id not in raw_players:
            continue
        incoming = cs.enriched_player(in_id, raw_players, teams, positions, fixture_map, expo, target_own, target_cap, target_n)
        incoming.update({
            'slot': out.get('slot'),
            'multiplier': 0,
            'captain': False,
            'vice_captain': False,
            'starter': False,
            'live_points': 0,
            'effective_points': 0,
            'transfer_in_for_event': next_gw,
            'transfer_source': 'user_declared_pending_api',
        })
        by_id[in_id] = incoming
        out_cost = t.get('element_out_cost')
        in_cost = t.get('element_in_cost')
        if out_cost is None:
            out_cost = int(round(float(out.get('price') or 0) * 10))
        if in_cost is None:
            in_cost = int(round(float(incoming.get('price') or 0) * 10))
        bank += (float(out_cost) - float(in_cost)) / 10
        applied.append({**t, 'source': 'user_declared_pending_api'})

    current = list(by_id.values())
    current.sort(key=lambda x: x.get('slot') or 99)
    if len(current) != 15:
        raise RuntimeError(f'declared transfer overlay produced {len(current)} players, expected 15')

    decisions = cs.current_moves(data, current, raw_players, teams, positions, fixture_map, expo, target_own, target_cap, target_n, bank)
    all_current = official + applied
    data['current_squad_source'] = 'declared_transfer_overlay'
    data['current_squad_transfers'] = all_current
    data['current_squad_next5'] = current
    data['current_bank'] = round(bank, 1)
    data['current_next_gw_decisions'] = decisions
    set_transfer_state(data, all_current, starting_ft=1)
    data['declared_transfer_overlay_status'] = 'pending_official_api'
    data['declared_transfer_overlay_applied'] = applied
    data['declared_transfer_overlay_generated_at_utc'] = datetime.now(timezone.utc).isoformat()
    LATEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'pending_applied': len(applied), 'current_bank': round(bank, 1), 'remaining_ft': data['free_transfers_remaining_next_gw'], 'next_hit_cost': data['next_transfer_hit_cost'], 'squad_source': data['current_squad_source']}))


if __name__ == '__main__':
    main()
