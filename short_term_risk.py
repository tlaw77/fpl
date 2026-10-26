"""Dated, sourced near-term minutes scenarios; assumptions are not medical facts."""
import json
from datetime import datetime, timezone
from pathlib import Path

EVIDENCE = Path('data/team_news_reviews.json')
OUT = Path('data/short_term_risk.json')


def stamp(value):
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except (ValueError, TypeError):
        return None


def availability(player, gw):
    baseline = float(player.get('adjusted_availability', player.get('availability', 1)))
    review = player.get('short_term_review') or {}
    expiry = stamp(review.get('valid_until_utc'))
    if review and (not expiry or datetime.now(timezone.utc) >= expiry):
        return max(0, min(1, baseline))
    cap = (player.get('availability_by_gw') or {}).get(str(gw))
    return max(0, min(1, baseline, float(cap) if cap is not None else 1))


def build(latest, pool, reviews, now=None):
    now = now or datetime.now(timezone.utc)
    gw = int(latest['next_gw'])
    held = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    held_ids = {int(x['player_id']) for x in held}
    active, expired = {}, []
    for review in reviews.get('players', []):
        checked, until = stamp(review.get('checked_at_utc')), stamp(review.get('valid_until_utc'))
        valid = (checked and until and checked <= now < until and
                 (now - checked).total_seconds() <= 48 * 3600 and
                 int(review.get('next_gw', 0)) == gw and review.get('sources'))
        if valid:
            active[int(review['player_id'])] = review
        elif int(review.get('player_id', 0)) in held_ids:
            expired.append(review.get('player', str(review['player_id'])))
    risks = []
    for player in pool.get('players', []):
        pid = int(player['player_id'])
        # Always rebuild from the upstream pool; never compound prior scenario caps.
        player.pop('availability_by_gw', None)
        player.pop('short_term_review', None)
        review = active.get(pid)
        if review:
            player['availability_by_gw'] = review.get('availability_caps_by_gw', {})
            player['short_term_review'] = review
        if pid in held_ids and (review or float(player.get('availability', 1)) < 1):
            risks.append({'player_id': pid, 'player': player['player'],
                          'kind': review.get('kind') if review else 'official_fpl_flag',
                          'summary': review.get('summary') if review else player.get('news', ''),
                          'assumption': review.get('assumption') if review else 'Official FPL availability',
                          'availability_by_gw': player.get('availability_by_gw', {}),
                          'official_availability': player.get('availability', 1),
                          'sources': review.get('sources', []) if review else [],
                          'unresolved': bool(review.get('unresolved', True)) if review else True})
    return {'status': 'SUCCESS', 'generated_at_utc': now.isoformat(), 'next_gw': gw,
            'risks': risks, 'expired_reviews': expired,
            'squad_players_checked': len(held_ids),
            'reviewed_players': len(active),
            'execution_ready': not expired and not any(x['unresolved'] for x in risks),
            'method_note': 'Official FPL availability plus dated, sourced analyst minutes scenarios. Caps are assumptions, not injury probabilities. Minimum of official availability and scenario cap avoids double counting. Missing review is not evidence of fitness.'}


def readiness(report, next_gw, now=None):
    now = now or datetime.now(timezone.utc)
    generated = stamp(report.get('generated_at_utc'))
    if (not generated or generated > now or (now-generated).total_seconds() > 6*3600
            or int(report.get('next_gw', 0)) != int(next_gw)):
        return False, 'Team-news checks are missing or stale; refresh before executing.'
    if report.get('news_feed_healthy') is False:
        return False, 'Team-news feed was incomplete; retry before executing.'
    names = [x['player'] for x in report.get('risks', []) if x.get('unresolved')]
    names += report.get('expired_reviews', [])
    return (False, 'Wait for updated team news: ' + ', '.join(dict.fromkeys(names))) if names else (True, 'Current team-news checks completed; recheck before the deadline.')


def main():
    latest = json.loads(Path('data/latest.json').read_text())
    pool = json.loads(Path('data/player_pool.json').read_text())
    reviews = json.loads(EVIDENCE.read_text()) if EVIDENCE.exists() else {}
    report = build(latest, pool, reviews)
    Path('data/player_pool.json').write_text(json.dumps(pool, indent=2, ensure_ascii=False)+'\n')
    watch_path = Path('data/press_conference_watch.json')
    watch = json.loads(watch_path.read_text()) if watch_path.exists() else {}
    report['news_feed_healthy'] = bool(watch.get('query_count') and len(watch.get('failed_queries', [])) < watch['query_count'])
    report['news_checked_at_utc'] = watch.get('generated_at_utc')
    report['news_players_checked'] = len(watch.get('players_checked', []))
    report['news_query_failures'] = len(watch.get('failed_queries', []))
    reviewed_ids = {x['player_id'] for x in report['risks']}
    for alert in watch.get('players', []):
        if alert.get('player_id') in reviewed_ids or alert.get('strongest_signal') not in ('OUT', 'DOUBT', 'MINUTES'):
            continue
        if alert.get('confidence', 0) < 40:
            continue
        report['risks'].append({'player_id': alert['player_id'], 'player': alert.get('player'), 'kind': 'headline_review_required', 'summary': 'Fresh news alert needs player-specific verification.', 'assumption': 'No automatic projection penalty from headline keywords; execution waits for review.', 'sources': alert.get('articles', []), 'unresolved': True})
    report['execution_ready'] = report['execution_ready'] and report['news_feed_healthy'] and not any(x.get('unresolved') for x in report['risks'])
    OUT.write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
