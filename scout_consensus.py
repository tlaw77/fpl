import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict, Counter
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

BASE = 'https://fantasy.premierleague.com/api'
LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
OUT = Path('data/scout_consensus.json')

SOURCE_WEIGHTS = {
    'Premier League': 1.00,
    'Fantasy Football Scout': 0.95,
    'BBC Sport': 0.88,
    'Fantasy Football Hub': 0.82,
    'Fantasy Football Fix': 0.80,
    'The Athletic': 0.78,
    'AllAboutFPL': 0.72,
    'Fantasy Football Community': 0.68,
    'Sky Sports': 0.66,
    'The Guardian': 0.64,
    'Reddit': 0.45,
}

GENERIC_QUERIES = [
    'Fantasy Premier League Gameweek {gw} tips players',
    'FPL Gameweek {gw} scout picks',
    'FPL Gameweek {gw} differentials',
    'FPL Gameweek {gw} captain transfers',
]

# Deliberate source-by-source discovery. These are public search queries rather than assumptions
# that one generic FPL query will surface every useful publisher.
SOURCE_QUERIES = [
    ('Premier League', 'site:premierleague.com FPL Gameweek {gw} Scout players'),
    ('Fantasy Football Scout', 'site:fantasyfootballscout.co.uk FPL Gameweek {gw} players'),
    ('BBC Sport', 'site:bbc.co.uk/sport football Gameweek {gw} FPL players injury team news'),
    ('Fantasy Football Hub', 'site:fantasyfootballhub.co.uk FPL Gameweek {gw} tips players'),
    ('Fantasy Football Fix', 'site:fantasyfootballfix.com FPL Gameweek {gw} players'),
    ('The Athletic', 'site:nytimes.com/athletic fantasy premier league Gameweek {gw}'),
    ('AllAboutFPL', 'site:allaboutfpl.com Gameweek {gw} FPL'),
    ('Fantasy Football Community', 'site:fantasyfootballcommunity.com Gameweek {gw} FPL'),
    ('Sky Sports', 'site:skysports.com fantasy football premier league Gameweek {gw}'),
    ('The Guardian', 'site:theguardian.com fantasy football premier league Gameweek {gw}'),
]

DIRECT = [
    ('Fantasy Football Scout', 'https://www.fantasyfootballscout.co.uk/gameweek-content'),
    ('Premier League', 'https://www.premierleague.com/en/news'),
]


def get_text(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 fpl-scout-consensus/1.3'})
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
    if 'bbc' in text or 'bbc.co.uk/sport' in text:
        return 'BBC Sport'
    if 'fantasy football hub' in text or 'fantasyfootballhub' in text:
        return 'Fantasy Football Hub'
    if 'fantasy football fix' in text or 'fantasyfootballfix' in text:
        return 'Fantasy Football Fix'
    if 'athletic' in text:
        return 'The Athletic'
    if 'allaboutfpl' in text:
        return 'AllAboutFPL'
    if 'fantasy football community' in text or 'fantasyfootballcommunity' in text:
        return 'Fantasy Football Community'
    if 'sky sports' in text or 'skysports' in text:
        return 'Sky Sports'
    if 'guardian' in text:
        return 'The Guardian'
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


def google_news_query(query, forced_source=None):
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=10)
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': query, 'hl': 'en-GB', 'gl': 'GB', 'ceid': 'GB:en'})
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
            source = forced_source or source_bucket(src, link)
            items.append({'title': title, 'summary': desc[:700], 'url': link, 'source': source, 'published': published.isoformat() if published else None})
    except Exception:
        pass
    return items


def google_news(gw):
    items = []
    for q in GENERIC_QUERIES:
        items.extend(google_news_query(q.format(gw=gw)))
    for source, q in SOURCE_QUERIES:
        items.extend(google_news_query(q.format(gw=gw), forced_source=source))
    return items


def reddit_mentions(gw):
    items = []
    queries = [f'GW{gw}', f'Gameweek {gw}', 'How did play', 'RMT', 'captain poll']
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    for q in queries:
        params = urllib.parse.urlencode({'q': q, 'restrict_sr': '1', 'sort': 'new', 't': 'week', 'limit': '40'})
        url = f'https://www.reddit.com/r/FantasyPL/search.json?{params}'
        try:
            data = get_json(url)
            for child in data.get('data', {}).get('children', []):
                d = child.get('data', {})
                created = datetime.fromtimestamp(d.get('created_utc') or 0, tz=timezone.utc)
                if created < cutoff:
                    continue
                title = strip_tags(d.get('title'))
                body = strip_tags(d.get('selftext'))[:700]
                if not title:
                    continue
                items.append({
                    'title': title,
                    'summary': body,
                    'url': 'https://www.reddit.com' + (d.get('permalink') or ''),
                    'source': 'Reddit',
                    'published': created.isoformat(),
                })
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


def article_topics(arts):
    text = ' '.join(f"{a.get('title','')} {a.get('summary','')}" for a in arts).lower()
    topics = []
    tests = [
        ('Scout Picks consideration', r'scout picks|picks team|bus team|top picks'),
        ('buy/hold/sell debate', r'buy|keep or sell|hold|transfer in|transfer out'),
        ('captaincy consideration', r'captain|captaincy|armband'),
        ('differential/value appeal', r'differential|budget|bargain|value'),
        ('fixture-run appeal', r'fixture|fixtures|run of games|schedule'),
        ('team-news/minutes discussion', r'team news|predicted line|minutes|start|rotation|injur|fitness|manager says|press conference'),
        ('form/underlying-performance discussion', r'form|xg|xa|expected|shots|chances|returns'),
    ]
    for label, pattern in tests:
        if re.search(pattern, text, re.I):
            topics.append(label)
    return topics[:4]


def synopsis(arts, sources):
    topics = article_topics(arts)
    src = ', '.join(sources[:4]) if sources else 'scouting sources'
    if not topics:
        return f'Mentioned by {src} in current-Gameweek coverage.'
    if len(topics) == 1:
        return f'{src} coverage centres on {topics[0]}.'
    return f"{src} coverage centres on {', '.join(topics[:-1])} and {topics[-1]}."


def why_it_matters(poolp, rank, owned, source_count):
    bits = []
    if rank is not None:
        if rank <= 10:
            bits.append(f'our 6GW model ranks him #{rank}')
        elif rank <= 25:
            bits.append(f'our 6GW model also rates him strongly at #{rank}')
        elif rank > 50 and source_count >= 2:
            bits.append(f'our 6GW model is much cooler at #{rank}, so this may be hype ahead of evidence')
    fixtures = poolp.get('fixtures') or []
    if fixtures:
        easy = sum(1 for f in fixtures if (f.get('difficulty') or 3) <= 2)
        hard = sum(1 for f in fixtures if (f.get('difficulty') or 3) >= 4)
        if easy >= 3:
            bits.append(f'{easy} of the next {len(fixtures)} fixtures are favourable')
        elif hard >= 3:
            bits.append(f'{hard} of the next {len(fixtures)} fixtures are difficult')
    if owned:
        bits.append('you already own him, so this primarily strengthens or challenges a hold decision')
    elif source_count >= 2:
        bits.append('multiple independent mentions make him worth comparing with your weakest same-position asset')
    if not bits:
        bits.append('the external mention is useful discovery context, but not yet strong enough to override the model')
    return '; '.join(bits) + '.'


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

    raw = google_news(gw) + reddit_mentions(gw) + direct_mentions(gw)
    dedup = []
    seen = set()
    for x in raw:
        key = (re.sub(r'\W+', ' ', x['title'].lower()).strip(), x['source'])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(x)

    source_coverage = Counter(x['source'] for x in dedup)
    mentions = defaultdict(list)
    for item in dedup:
        text = f"{item['title']} {item.get('summary') or ''}"
        for pid in match_players(text, aliases):
            mentions[pid].append(item)

    matched_source_counts = Counter()
    players = []
    for pid, arts in mentions.items():
        p = by_id.get(pid, {})
        sources = sorted({a['source'] for a in arts})
        for s in sources:
            matched_source_counts[s] += 1
        weighted = round(sum(SOURCE_WEIGHTS.get(a['source'], 0.55) for a in arts), 2)
        poolp = pool_by_id.get(pid, {})
        score = poolp.get('six_gw_score')
        rank = pool_rank.get(pid)
        owned = pid in effective_ids
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
            'in_public_squad': owned,
            'merit': merit_label(len(sources), weighted, score, rank, owned),
            'synopsis': synopsis(arts, sources),
            'why_it_matters': why_it_matters(poolp, rank, owned, len(sources)),
            'topics': article_topics(arts),
            'articles': sorted(arts, key=lambda a: a.get('published') or '', reverse=True)[:8],
        })

    players.sort(key=lambda x: (x['source_count'], x['weighted_mentions'], -(x['six_gw_rank'] or 9999)), reverse=True)

    out = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'next_gw': gw,
        'article_count': len(dedup),
        'source_coverage': dict(source_coverage.most_common()),
        'matched_player_sources': dict(matched_source_counts.most_common()),
        'players': players[:80],
        'method_note': 'Public scouting mentions are discovery signals, not recommendations. Source breadth is deliberately collected source-by-source, weighted by source type, then compared with the dashboard six-GW model. Synopses are generated from public titles/search summaries and do not reproduce article text.',
    }
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'gw': gw, 'articles': len(dedup), 'sources': len(source_coverage), 'players': len(players)}))


if __name__ == '__main__':
    main()
