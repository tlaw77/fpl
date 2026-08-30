import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE = 'https://fantasy.premierleague.com/api'
LATEST = Path('data/latest.json')


def get_json(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'fpl-deadline-context/1.0'})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)


def parse_utc(value):
    if not value:
        return None
    text = str(value).replace('Z', '+00:00')
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def run():
    if not LATEST.exists():
        raise RuntimeError('data/latest.json missing')
    data = json.loads(LATEST.read_text(encoding='utf-8'))
    if data.get('status') != 'SUCCESS':
        raise RuntimeError('latest snapshot not ready')

    bootstrap = get_json(f'{BASE}/bootstrap-static/')
    next_gw = int(data.get('next_gw') or 0)
    event = next((x for x in bootstrap.get('events', []) if int(x.get('id') or 0) == next_gw), None)
    if not event:
        raise RuntimeError(f'FPL event metadata unavailable for GW{next_gw}')

    deadline = parse_utc(event.get('deadline_time'))
    now = datetime.now(timezone.utc)
    hours = None if deadline is None else round((deadline - now).total_seconds() / 3600, 2)
    phase = 'unknown'
    if hours is not None:
        if hours <= 0:
            phase = 'locked'
        elif hours <= 6:
            phase = 'final'
        elif hours <= 24:
            phase = 'deadline_day'
        elif hours <= 72:
            phase = 'approaching'
        else:
            phase = 'normal'

    context = {
        'gw': next_gw,
        'deadline_utc': deadline.isoformat() if deadline else None,
        'hours_to_deadline': hours,
        'phase': phase,
        'source': 'official_fpl_bootstrap',
        'captured_at_utc': now.isoformat(),
    }
    data['next_deadline_utc'] = context['deadline_utc']
    data['hours_to_deadline'] = hours
    data['deadline_context'] = context

    current_gw = int(data.get('current_gw') or 0)
    current_fixtures = []
    if current_gw:
        fixtures = get_json(f'{BASE}/fixtures/?event={current_gw}')
        for f in fixtures if isinstance(fixtures, list) else []:
            current_fixtures.append({
                'id': f.get('id'),
                'event': f.get('event'),
                'team_h': f.get('team_h'),
                'team_a': f.get('team_a'),
                'kickoff_time': f.get('kickoff_time'),
                'started': bool(f.get('started')),
                'finished': bool(f.get('finished')),
                'finished_provisional': bool(f.get('finished_provisional')),
                'minutes': f.get('minutes'),
            })
    data['current_gw_fixtures'] = current_fixtures
    data['current_gw_fixture_status'] = {
        'gw': current_gw,
        'source': 'official_fpl_fixtures',
        'captured_at_utc': now.isoformat(),
        'fixture_count': len(current_fixtures),
    }

    payload = json.dumps(data, indent=2, ensure_ascii=False) + '\n'
    LATEST.write_text(payload, encoding='utf-8')
    if current_gw:
        Path(f'data/gw{current_gw}.json').write_text(payload, encoding='utf-8')

    print(json.dumps({'status': 'SUCCESS', **context, 'current_gw_fixture_count': len(current_fixtures)}))


if __name__ == '__main__':
    run()
