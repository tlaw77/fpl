"""Observed PL participation, separate from fitness and non-PL workload.

PPG already contains playing-time effects on appearances. Compare recent minutes
per scheduled match with minutes per *appearance*, rather than multiplying PPG
by minutes/90 again. Estimates are shrunk heuristics, not calibrated probabilities.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed


def profile(history):
    rows = sorted(history, key=lambda x: x['gw'])[-6:]
    if len(rows) < 3:
        return {'status': 'insufficient', 'sample_matches': len(rows), 'factor': 1.0}
    played = [x for x in rows if x['minutes'] > 0]
    baseline = sum(x['minutes'] for x in played) / len(played) if played else 75.0
    recent = rows[-3:]
    # Two prior match-equivalents prevent one benching from becoming a verdict.
    expected = (sum(x['minutes'] for x in recent) + 2 * baseline) / (len(recent) + 2)
    factor = min(1.0, max(.20, expected / max(1, baseline)))
    p_start = (sum(x['starts'] for x in recent) + 2 * .85) / (len(recent) + 2)
    p_cameo = (sum(0 < x['minutes'] < 60 for x in recent) + 2 * .10) / (len(recent) + 2)
    p_sub = (sum(x['starts'] == 0 and x['minutes'] > 0 for x in recent) + 2 * .10) / (len(recent) + 2)
    p_early = (sum(x['starts'] == 1 and 0 < x['minutes'] < 60 for x in recent) + 2 * .15) / (len(recent) + 2)
    p_zero = (sum(x['minutes'] == 0 for x in recent) + 2 * .05) / (len(recent) + 2)
    risk = 'High' if factor < .65 else 'Medium' if factor < .85 else 'Low'
    return {'version': 1, 'status': 'observed', 'source': 'official_fpl_completed_event_live',
            'assessed_through_gw': rows[-1]['gw'], 'sample_matches': len(rows),
            'recent_minutes': [x['minutes'] for x in recent], 'history': rows,
            'baseline_minutes_per_appearance': round(baseline, 1),
            'expected_minutes': round(expected, 1), 'start_estimate': round(p_start, 3),
            'substitute_estimate': round(p_sub, 3), 'early_sub_estimate': round(p_early, 3),
            'short_appearance_estimate': round(p_cameo, 3), 'no_appearance_estimate': round(p_zero, 3),
            'factor': round(factor, 3), 'risk': risk,
            'method': 'Last three completed single-fixture PL matches, shrunk by two prior matches; relative to per-appearance minutes. Starts and short appearances overlap; estimates are not calibrated probabilities.'}


def collect(bootstrap, get, current_gw):
    events = [int(e['id']) for e in bootstrap.get('events', [])
              if e.get('finished') and int(e['id']) <= current_gw][-6:]
    histories, failures = {}, []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(get, f'https://fantasy.premierleague.com/api/event/{gw}/live/'): gw for gw in events}
        for future in as_completed(futures):
            gw = futures[future]
            try:
                payload = future.result()
                if not payload.get('elements'):
                    raise ValueError('empty event feed')
                for item in payload['elements']:
                    stats = item.get('stats') or {}
                    # No fixture is a blank, not a non-appearance. Exclude aggregate
                    # DGW minutes rather than pretending 180 mins is one start.
                    if len(item.get('explain') or []) != 1 or 'starts' not in stats or 'minutes' not in stats:
                        continue
                    minutes = float(stats['minutes'])
                    if not 0 <= minutes <= 90:
                        continue
                    histories.setdefault(int(item['id']), []).append({'gw': gw, 'minutes': minutes, 'starts': int(stats['starts'])})
            except Exception as exc:
                failures.append({'gw': gw, 'error': str(exc)})
    profiles = {pid: profile(rows) for pid, rows in histories.items()}
    # Never apply an old role estimate after a newer completed event failed.
    if failures:
        for row in profiles.values():
            row.update(status='incomplete', factor=1.0, risk='Unknown')
    return profiles, {'completed_events': events, 'failures': failures,
                      'observed_players': sum(p['status'] == 'observed' for p in profiles.values())}


def participation(player, availability):
    """Use the strongest playing-time constraint, not three stacked haircuts.

    adjusted_availability already embeds schedule_modifier. Recover the fitness/
    scenario bound separately and apply workload once alongside observed minutes.
    """
    role = player.get('minutes_review') or {}
    if role.get('status') != 'observed':
        return availability, 1.0
    fitness = max(0.0, min(1.0, float(player.get('availability', 1))))
    schedule = max(.78, min(1.04, float(player.get('schedule_modifier', 1))))
    adjusted = float(player.get('adjusted_availability', fitness))
    # Restore only the known upstream workload discount; leave scenario caps intact.
    bound = fitness if abs(availability - adjusted) < 1e-8 else availability
    role_bound = fitness * float(role.get('factor', 1))
    return min(bound, role_bound, fitness * schedule), schedule
