import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

BASE = 'https://fantasy.premierleague.com/api'
LATEST = Path('data/latest.json')
OUT = Path('data/current_player_outcomes.json')
FIELDS = (
    'minutes','goals_scored','assists','clean_sheets','goals_conceded','own_goals',
    'penalties_saved','penalties_missed','yellow_cards','red_cards','saves','bonus','bps'
)

def get_json(url):
    req = Request(url, headers={'User-Agent':'fpl-current-outcomes/1.0'})
    with urlopen(req, timeout=30) as r:
        return json.load(r)

def main():
    latest = json.loads(LATEST.read_text(encoding='utf-8'))
    gw = int(latest.get('current_gw') or 0)
    if not gw:
        raise RuntimeError('latest.json has no current_gw')
    raw = get_json(f'{BASE}/event/{gw}/live/')
    rows = []
    for item in raw.get('elements', []):
        pid = int(item.get('id') or 0)
        if not pid:
            continue
        stats = item.get('stats') or {}
        row = {'player_id': pid, 'total_points': int(stats.get('total_points') or 0)}
        for key in FIELDS:
            row[key] = int(stats.get(key) or 0)
        rows.append(row)
    rows.sort(key=lambda x: x['player_id'])
    payload = {
        'version': 1,
        'gw': gw,
        'captured_at_utc': datetime.now(timezone.utc).isoformat(),
        'player_count': len(rows),
        'players': rows,
        'source': 'official_fpl_event_live',
        'method_note': 'Current all-player event outcome snapshot for completed-live monitoring before durable GW archival.'
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(f'Wrote {OUT} for GW{gw} with {len(rows)} players')

if __name__ == '__main__':
    main()
