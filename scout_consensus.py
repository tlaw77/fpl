import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

BASE = 'https://fantasy.premierleague.com/api'
LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
OUT = Path('data/scout_consensus.json')

# Source weights are credibility/context weights, not truth scores.
SOURCE_WEIGHTS = {
    'Premier League': 1.00,
    'Fantasy Football Scout': 0.95,
    'Fantasy Football Hub': 0.80,
    'Fantasy Football Fix': 0.78,
    'The Athletic': 0.78,
    'Reddit': 0.45,
}

NEWS_QUERIES = [
    'Fantasy Premier League Gameweek {gw} tips players',
    'FPL Gameweek {gw} scout picks',
    'FPL Gameweek {gw} differentials',
    'FPL Gameweek {gw} captain transfers',
]

DIRECT = [
    ('Fantasy Football Scout', 'https://www.fantasyfootballscout.co.uk/gameweek-content'),
    ('Premier League', 'https://www.premierleague.com/en/news'),
]


def get_text(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 fpl-scout-consensus/1.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode('utf-8', errors='ignore')


def get_json(url):
    return json.loads(get_text(url))


def strip_tags(s):
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def source_bucket(name, url=''):
    text = f'{name} {url}'.lower()
    if 'premier league' in text or 'premierleague.com' in text:
        return 'Premier League'
    if 'fantasy football scout' in text or 'fantasyfootballscout' in text:
        return 'Fantasy Football Scout'
    if 'fantasy football hub' in text or 'fantasyfootballhub' in text:
        return 'Fantasy Football Hub'
    if 'fantasy football fix' in text or 'fantasyfootballfix' in text:
        return 'Fantasy Football Fix'
    if 'athletic' in text:
        return 'The Athletic'
    if 'reddit' in text:
        return 'Reddit'
    return name or 'Other'


def player_aliases(elements):
    aliases = defaultdict(set)
    for p in elements:
        names = {p.get('web_name') or '', p.get('first_name') or '', p.get('second_name') or ''}
        full = f"{p.get('first_name') or ''} {p.get('second_name') or ''}".strip()
        if full:
            names.add(full)
        # Avoid ambiguous one/two-letter aliases and common first names.
        for n in names:
            n = n.strip()
            if len(n) >= 4:
                aliases[p['id']].add(n)
    return aliases


def match_players(text, aliases):
    low = f' {text.lower()} '
    hits = []
    for pid, names in aliases.items():
        best = None
        for n in names:
            if re.search(r'(?<!\w)' + re.escape(n.lower()) + r'(?!\w)', low):
                if best is None or len(n) > len(best):
                    best = n
        if best:
            hits.append(pid)
    return hits


def google_news(gw):
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=10)
    for q in NEWS_QUERIES:
        url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': q.format(gw=gw), 'hl': 'en-GB', 'gl': 'GB', 'ceid': 'GB:en'})
        try:
            root = ET.fromstring(get_text(url))
            for item in root.findall('.//item'):
                title = strip_tags(item.findtext('title'))
                desc = strip_tags(item.findtext('description'))
                link = item.findtext('link') or ''
                src_node = item.find('source')
                src = strip_tags(src_node.text if src_node is not None else '')
                published = None
                try:
                    published = parsedate_to_datetime(item.findtext('pubDate')).astimezone(timezone.utc)
                except Exception:
                    pass
                if published and published < cutoff:
                    continue
                items.append({'title': title, 'summary': desc[:500], 'url': link, 'source': source_bucket(src, link), 'published': published.isoformat() if published else None})
        except Exception:
            continue
    return items


def direct_mentions(gw):
    items = []
    for source, url in DIRECT:
        try:
            text = get_text(url)
        except Exception:
            continue
        # Keep only anchors that look FPL/GW relevant. This is intentionally shallow; news RSS carries the breadth.
        for href, raw_title in re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', text, re.I | re.S):
            title = strip_tags(raw_title)
            if len(title) < 12:
                continue
            if not re.search(rf'FPL|Fantasy|Gameweek\s*{gw}|GW\s*{gw}|Scout Picks|differential|captain', title, re.I):
                continue
            if href.startswith('/'):
                base = urllib.parse.urlsplit(url)
                href = f'{base.scheme}://{base.netloc}{href}'
            if not href.startswith('http'):
                continue
            items.append({'title': title[:240], 'summary': '', 'url': href, 'source': source, 'published': None})
    return items


def merit_label(source_count, weighted_mentions, model_score, pool_rank, owned):
    if owned and source_count >= 2:
        return 'Reinforces hold'
    if source_count >= 3 and weighted_mentions >= 2.2 and (pool_rank is None or pool_rank <= 25):
        return 'Strong shortlist'
    if source_count >= 2 and (pool_rank is None or pool_rank <= 40):
        return 'Worth investigating'
    if source_count >= 2:
        return 'Consensus mention'
    if model_score is not None and pool_rank is not None and pool_rank <= 15:
        return 'Model likes more than scouts'
    return 'Monitor'


def main():
    latest = json.loads(LATEST.read_text())
    pool = json.loads(POOL.read_text()) if POOL.exists() else {'players': []}
    gw = int(latest.get('next_gw') or 2)
    bootstrap = get_json(f'{BASE}/bootstrap-static/')
    elements = bootstrap.get('elements', [])
    teams = {t['id']: t['name'] for t in bootstrap.get('teams', [])}
    by_id = {p['id']: p for p in elements}
    aliases = player_aliases(elements)
    pool_by_id = {p['player_id']: p for p in pool.get('players', [])}
    pool_rank = {p['player_id']: i + 1 for i, p in enumerate(pool.get('players', []))}
    effective_ids = {p.get('player_id') for p in (latest.get('current_squad_next5') or latest.get('squad_next5') or [])}

    raw = google_news(gw) + direct_mentions(gw)
    # de-dupe by normalized title + source
    dedup = []
    seen = set()
    for x in raw:
        key = (re.sub(r'\W+', ' ', x['title'].lower()).strip(), x['source'])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(x)

    mentions = defaultdict(list)
    for item in dedup:
        text = f"{item['title']} {item.get('summary') or ''}"
        for pid in match_players(text, aliases):
            mentions[pid].append(item)

    players = []
    for pid, arts in mentions.items():
        p = by_id.get(pid, {})
        sources = sorted({a['source'] for a in arts})
        weighted = round(sum(SOURCE_WEIGHTS.get(a['source'], 0.55) for a in arts), 2)
        poolp = pool_by_id.get(pid, {})
        score = poolp.get('six_gw_score')
        rank = pool_rank.get(pid)
        players.append({
            'player_id': pid,
            'player': p.get('web_name'),
            'club': teams.get(p.get('team')),
            'position': poolp.get('position'),
            'price': poolp.get('price'),
            'source_count': len(sources),
            'mention_count': len(arts),
            'weighted_mentions': weighted,
            'sources': sources,
            'six_gw_score': score,
            'six_gw_rank': rank,
            'in_public_squad': pid in effective_ids,
            'merit': merit_label(len(sources), weighted, score, rank, pid in effective_ids),
            'articles': sorted(arts, key=lambda a: a.get('published') or '', reverse=True)[:6],
        })

    players.sort(key=lambda x: (x['source_count'], x['weighted_mentions'], -(x['six_gw_rank'] or 9999)), reverse=True)

    out = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'next_gw': gw,
        'article_count': len(dedup),
        'players': players[:60],
        'method_note': 'Public scouting mentions are discovery signals, not recommendations. Source breadth is weighted by source type, then compared with the dashboard six-GW model. Article text is not reproduced.',
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'gw': gw, 'articles': len(dedup), 'players': len(players)}))


if __name__ == '__main__':
    main()
