import json
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE = 'https://fantasy.premierleague.com/api'
LATEST = Path('data/latest.json')
SCHEDULE = Path('data/schedule_load.json')
HISTORY_INDEX = Path('data/history/index.json')
OUT = Path('data/fixture_calendar_intelligence.json')
HORIZON = 12


def get(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'fpl-calendar-intelligence/1.0'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def dt(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except Exception:
        return None


def comp_type(name):
    x = str(name or '').lower()
    if any(k in x for k in ('champions league', 'europa league', 'conference league', 'uefa')):
        return 'Europe'
    if any(k in x for k in ('fa cup', 'efl cup', 'league cup', 'carabao')):
        return 'Domestic cup'
    return 'Other non-PL'


def historical_dgw_samples():
    idx = load(HISTORY_INDEX, {})
    samples = []
    for row in idx.get('finalized_gameweeks') or []:
        gw = int(row.get('gw') or 0)
        pool_path = Path(f'data/history/gw{gw}/player_pool.json')
        if not pool_path.exists():
            continue
        pool = load(pool_path, {})
        seen = set()
        for p in pool.get('players') or []:
            club = p.get('club')
            if not club or club in seen:
                continue
            count = sum(1 for f in p.get('fixtures') or [] if int(f.get('gw') or -1) == gw)
            if count >= 2:
                seen.add(club)
                samples.append({'gw': gw, 'club': club, 'fixture_count': count})
    return samples


def main():
    latest = load(LATEST, {})
    schedule = load(SCHEDULE, {'clubs': {}})
    bootstrap = get(f'{BASE}/bootstrap-static/')
    fixtures = get(f'{BASE}/fixtures/')
    teams = {int(t['id']): t['name'] for t in bootstrap.get('teams') or []}
    events = {int(e['id']): e for e in bootstrap.get('events') or []}
    next_gw = int(latest.get('next_gw') or 1)
    gws = [gw for gw in range(next_gw, min(39, next_gw + HORIZON)) if gw in events]

    by_club_gw = defaultdict(list)
    unscheduled = []
    for f in fixtures:
        event = f.get('event')
        if event is None:
            if not f.get('finished'):
                unscheduled.append({
                    'fixture_id': f.get('id'),
                    'home': teams.get(int(f.get('team_h') or 0), ''),
                    'away': teams.get(int(f.get('team_a') or 0), ''),
                    'kickoff_time': f.get('kickoff_time'),
                    'reason': 'Official FPL fixture currently has no Gameweek assignment',
                })
            continue
        event = int(event)
        if event not in gws:
            continue
        by_club_gw[(int(f['team_h']), event)].append(f)
        by_club_gw[(int(f['team_a']), event)].append(f)

    confirmed_doubles = []
    confirmed_blanks = []
    team_ids = sorted(teams)
    for gw in gws:
        if not any((f.get('event') == gw) for f in fixtures):
            continue
        for tid in team_ids:
            rows = by_club_gw.get((tid, gw), [])
            if len(rows) >= 2:
                confirmed_doubles.append({
                    'gw': gw,
                    'club': teams[tid],
                    'fixture_count': len(rows),
                    'status': 'CONFIRMED',
                    'fixtures': [
                        {
                            'opponent': teams.get(int(r['team_a'] if r['team_h'] == tid else r['team_h']), ''),
                            'venue': 'H' if r['team_h'] == tid else 'A',
                            'kickoff_time': r.get('kickoff_time'),
                        } for r in rows
                    ],
                })
            elif len(rows) == 0:
                confirmed_blanks.append({'gw': gw, 'club': teams[tid], 'status': 'CONFIRMED'})

    # Non-PL calendar load by club, split into Europe/domestic-cup/other. This is used
    # as a rotation/congestion signal and to reduce confidence in speculative windows.
    non_pl = []
    now = datetime.now(timezone.utc)
    for club, rows in (schedule.get('clubs') or {}).items():
        future = []
        for e in rows or []:
            when = dt(e.get('date'))
            if not when or when < now:
                continue
            future.append({
                'date': e.get('date'),
                'competition': e.get('competition') or 'Non-PL',
                'type': comp_type(e.get('competition')),
                'home_away': e.get('home_away'),
                'opponent': e.get('opponent'),
            })
        if future:
            europe = sum(1 for x in future if x['type'] == 'Europe')
            cups = sum(1 for x in future if x['type'] == 'Domestic cup')
            non_pl.append({'club': club, 'future_non_pl': len(future), 'europe': europe, 'domestic_cup': cups, 'fixtures': future[:10]})
    load_map = {x['club']: x for x in non_pl}

    # A postponed/unassigned fixture creates DGW pressure but not a guaranteed target GW.
    # Candidate windows are deliberately low-confidence and capped below 60% until FPL
    # actually assigns the fixture. We reward structural availability and penalise known
    # Europe/cup load around the horizon rather than pretending we know the reschedule date.
    potential_windows = []
    for back in unscheduled:
        clubs = [back['home'], back['away']]
        club_ids = [next((tid for tid, name in teams.items() if name == c), 0) for c in clubs]
        for gw in gws:
            counts = [len(by_club_gw.get((tid, gw), [])) for tid in club_ids]
            if not all(c == 1 for c in counts):
                continue
            deadline = dt((events.get(gw) or {}).get('deadline_time'))
            if not deadline or deadline <= now:
                continue
            days = max(1.0, (deadline - now).total_seconds() / 86400)
            load = sum((load_map.get(c) or {}).get('europe', 0) + (load_map.get(c) or {}).get('domestic_cup', 0) for c in clubs)
            probability = .24
            probability += .08 if days >= 14 else 0
            probability += .05 if days >= 28 else 0
            probability -= min(.12, load * .015)
            probability = max(.12, min(.49, probability))
            potential_windows.append({
                'gw': gw,
                'fixture': f"{back['home']} v {back['away']}",
                'clubs': clubs,
                'planning_probability': round(probability, 3),
                'status': 'POSSIBLE',
                'reason': 'Unassigned PL fixture plus one scheduled league match for each club in this GW; exact reschedule timing is unknown.',
            })
    potential_windows.sort(key=lambda x: (-x['planning_probability'], x['gw'], x['fixture']))

    samples = historical_dgw_samples()
    backlog_count = len(unscheduled)
    confirmed_future = len(confirmed_doubles)
    strongest_possible = max((x['planning_probability'] for x in potential_windows), default=0)
    # Option-value score is intentionally modest early: it can encourage patience but
    # must not outweigh an exceptional confirmed chip opportunity by itself.
    preservation = min(100, round(confirmed_future * 22 + backlog_count * 12 + strongest_possible * 45))
    if confirmed_doubles:
        preservation = min(100, preservation + 10)

    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 1,
        'next_gw': next_gw,
        'horizon_gws': gws,
        'confirmed_doubles': confirmed_doubles,
        'confirmed_blanks': confirmed_blanks,
        'unassigned_fixture_backlog': unscheduled,
        'potential_dgw_windows': potential_windows[:40],
        'non_pl_calendar': non_pl,
        'chip_preservation_score': preservation,
        'historical_prior': {
            'source': 'frozen in-repo gameweek archives',
            'observed_dgw_team_samples': len(samples),
            'samples': samples[-20:],
            'status': 'BUILDING' if len(samples) < 8 else 'USABLE',
            'note': 'Past-season DGW outcome priors are not yet imported; current-season frozen outcomes accumulate automatically.'
        },
        'method_note': 'Confirmed doubles/blanks come directly from the official FPL fixture event assignments. Unassigned fixtures create rescheduling pressure. Possible DGW windows are low-confidence planning probabilities only and never add expected points until officially assigned. Europe/domestic-cup fixtures are used as congestion and rotation context.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'confirmed_dgw': len(confirmed_doubles), 'backlog': backlog_count, 'possible_windows': len(potential_windows), 'preservation_score': preservation}))


if __name__ == '__main__':
    main()
