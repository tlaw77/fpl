import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY = Path('data/history')
OUT = Path('data/backtest_summary.json')


def load(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if default is None else default


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def archived_gws():
    out = []
    for d in HISTORY.glob('gw*'):
        try:
            gw = int(d.name[2:])
        except Exception:
            continue
        if (d / 'manifest.json').exists():
            out.append(gw)
    return sorted(out)


def points_map(snapshot):
    rows = snapshot.get('squad') or []
    return {int(p.get('player_id') or 0): n(p.get('live_points')) for p in rows if p.get('player_id')}


def evaluate_pair(source_gw, target_gw):
    source = HISTORY / f'gw{source_gw}'
    target = HISTORY / f'gw{target_gw}'
    cap_path = source / 'captaincy_review.json'
    tc_path = source / 'triple_captain_review.json'
    outcome_path = target / 'dashboard_snapshot.json'
    if not cap_path.exists() or not outcome_path.exists():
        return None

    cap = load(cap_path)
    outcome = load(outcome_path)
    if int(cap.get('next_gw') or 0) != target_gw:
        return None
    if int(outcome.get('current_gw') or 0) != target_gw:
        return None

    pts = points_map(outcome)
    captain = cap.get('captain') or {}
    shortlist = cap.get('shortlist') or []
    captain_id = int(captain.get('player_id') or 0)
    captain_actual = pts.get(captain_id)
    if captain_actual is None:
        return None

    evaluated = []
    for p in shortlist:
        pid = int(p.get('player_id') or 0)
        if pid not in pts:
            continue
        evaluated.append({
            'player_id': pid,
            'player': p.get('player'),
            'forecast_points': n(p.get('expected_points')),
            'actual_points': pts[pid],
            'forecast_error': round(pts[pid] - n(p.get('expected_points')), 2),
        })
    if not evaluated:
        return None
    best = max(evaluated, key=lambda x: x['actual_points'])
    captain_forecast = n(captain.get('expected_points'))

    tc = load(tc_path, {}) if tc_path.exists() else {}
    tc_decision = tc.get('decision') or {}
    tc_candidate = tc_decision.get('candidate') or {}
    tc_candidate_id = int(tc_candidate.get('player_id') or 0)
    tc_actual = pts.get(tc_candidate_id) if tc_candidate_id else None

    return {
        'decision_archive_gw': source_gw,
        'evaluated_gw': target_gw,
        'captain': captain.get('player'),
        'captain_player_id': captain_id,
        'captain_forecast_points': round(captain_forecast, 2),
        'captain_actual_points': captain_actual,
        'captain_forecast_error': round(captain_actual - captain_forecast, 2),
        'best_shortlisted_player': best['player'],
        'best_shortlisted_actual_points': best['actual_points'],
        'captain_regret_points': round(best['actual_points'] - captain_actual, 2),
        'captain_was_best_shortlisted': captain_id == best['player_id'],
        'shortlist': evaluated,
        'tc_review_status': tc_decision.get('status'),
        'tc_candidate': tc_candidate.get('player'),
        'tc_candidate_actual_points': tc_actual,
        'hypothetical_extra_tc_points': tc_actual,
        'note': 'Hypothetical extra TC points equal the candidate raw return because Triple Captain adds one extra copy of the captain score beyond normal captaincy.' if tc_actual is not None else None,
    }


def summary(rows):
    if not rows:
        return {
            'captain_best_shortlist_rate_pct': None,
            'average_captain_regret_points': None,
            'average_captain_forecast_error': None,
            'message': 'Not enough completed evidence yet. A captaincy review must be archived before a Gameweek and the following Gameweek must then be finalized.'
        }
    count = len(rows)
    return {
        'captain_best_shortlist_rate_pct': round(100 * sum(1 for r in rows if r['captain_was_best_shortlisted']) / count, 1),
        'average_captain_regret_points': round(sum(n(r['captain_regret_points']) for r in rows) / count, 2),
        'average_captain_forecast_error': round(sum(n(r['captain_forecast_error']) for r in rows) / count, 2),
        'message': 'Early backtest only. Treat percentages as descriptive until several completed Gameweeks accumulate.'
    }


def main():
    gws = archived_gws()
    rows = []
    for source_gw in gws:
        target_gw = source_gw + 1
        if target_gw not in gws:
            continue
        row = evaluate_pair(source_gw, target_gw)
        if row:
            rows.append(row)

    output = {
        'status': 'SUCCESS',
        'version': 1,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'finalized_gameweeks': gws,
        'evaluable_gameweeks': len(rows),
        'summary': summary(rows),
        'rows': rows,
        'method_note': 'Pairs a pre-Gameweek archived captaincy/TC review from GW N with the finalized dashboard outcome in GW N+1. This first version evaluates captain selection and TC candidate outcome only; transfer, rank and probability calibration will be added as comparable archived evidence accumulates.'
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'evaluable_gameweeks': len(rows), 'summary': output['summary']}))


if __name__ == '__main__':
    main()
