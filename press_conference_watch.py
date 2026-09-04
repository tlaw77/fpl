import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
OUT = Path('data/press_conference_watch.json')

SOURCE_WEIGHT = {
    'Official club': 1.00,
    'Premier League': 0.98,
    'BBC Sport': 0.92,
    'Sky Sports': 0.86,
    'Fantasy Football Scout': 0.84,
    'The Guardian': 0.78,
    'Other': 0.58,
}

TEAM_NEWS_PATTERNS = [
    ('OUT', r'ruled out|will miss|not available|unavailable|out of the game|out for'),
    ('DOUBT', r'doubt|late test|assess|assessment|touch and go|wait and see|question mark'),
    ('FIT', r'fit|available|back in training|trained|ready|fine|okay|ok to play'),
    ('MINUTES', r'minutes|start|starting|rotation|rest|manage|managed|bench|substitute'),
]


def get_text(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 fpl-press-watch/1.0'})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode('utf-8', errors='ignore')


def strip_tags(s):
    return html.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', s or ''))).strip()


def source_bucket(name, url=''):
    text = f'{name} {url}'.lower()
    if any(x in text for x in ('arsenal.com','avfc.co.uk','afcb.co.uk','brentfordfc.com','brightonandhovealbion.com','chelseafc.com','cpfc.co.uk','evertonfc.com','fulhamfc.com','leedsunited.com','liverpoolfc.com','mancity.com','manutd.com','newcastleunited.com','nottinghamforest.co.uk','safc.com','tottenhamhotspur.com','whufc.com','wolves.co.uk')):
        return 'Official club'
    if 'premierleague.com' in text or 'premier league' in text:
        return 'Premier League'
    if 'bbc' in text:
        return 'BBC Sport'
    if 'skysports' in text or 'sky sports' in text:
        return 'Sky Sports'
    if 'fantasyfootballscout' in text or 'fantasy football scout' in text:
        return 'Fantasy Football Scout'
    if 'guardian' in text:
        return 'The Guardian'
    return 'Other'


def google_news(query):
    url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': query, 'hl': 'en-GB', 'gl': 'GB', 'ceid': 'GB:en'})
    cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    rows = []
    try:
        root = ET.fromstring(get_text(url))
    except Exception:
        return rows
    for item in root.findall('.//item'):
        title = strip_tags(item.findtext('title'))
        desc = strip_tags(item.findtext('description'))
        link = item.findtext('link') or ''
        src_node = item.find('source')
        src = strip_tags(src_node.text if src_node is not None else '')
        try:
            published = parsedate_to_datetime(item.findtext('pubDate')).astimezone(timezone.utc)
        except Exception:
            published = None
        if published and published < cutoff:
            continue
        rows.append({
            'title': title,
            'summary': desc[:900],
            'url': link,
            'source': source_bucket(src, link),
            'published': published.isoformat() if published else None,
        })
    return rows


def player_aliases(rows):
    out = {}
    for p in rows:
        names = {str(p.get('player') or '').strip()}
        for n in list(names):
            if len(n) >= 4:
                out.setdefault(int(p.get('player_id') or 0), set()).add(n)
    return {k:v for k,v in out.items() if k}


def match_players(text, aliases):
    low = f' {text.lower()} '
    hits = []
    for pid,names in aliases.items():
        if any(re.search(r'(?<!\w)' + re.escape(n.lower()) + r'(?!\w)', low) for n in names):
            hits.append(pid)
    return hits


def classify(text):
    low = text.lower()
    labels = []
    for label,pat in TEAM_NEWS_PATTERNS:
        if re.search(pat, low, re.I):
            labels.append(label)
    return labels


def recency_weight(published):
    if not published:
        return .70
    try:
        age_h = max(0.0, (datetime.now(timezone.utc) - datetime.fromisoformat(published.replace('Z','+00:00'))).total_seconds()/3600)
    except Exception:
        return .70
    if age_h <= 3: return 1.00
    if age_h <= 8: return .92
    if age_h <= 18: return .80
    if age_h <= 36: return .65
    return .45


def main():
    latest = json.loads(LATEST.read_text())
    pool = json.loads(POOL.read_text()) if POOL.exists() else {'players': []}
    next_gw = int(latest.get('next_gw') or 1)
    deadline = ((latest.get('deadline_context') or {}).get('deadline_utc') or latest.get('next_deadline_utc'))
    now = datetime.now(timezone.utc)
    try:
        deadline_dt = datetime.fromisoformat(str(deadline).replace('Z','+00:00')) if deadline else None
    except Exception:
        deadline_dt = None
    hours_to_deadline = ((deadline_dt-now).total_seconds()/3600) if deadline_dt else None
    friday_window = now.weekday() == 4 and (hours_to_deadline is None or -2 <= hours_to_deadline <= 48)

    squad = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    squad_ids = {int(x.get('player_id') or 0) for x in squad}
    pool_rows = pool.get('players') or []
    relevant = [p for p in pool_rows if int(p.get('player_id') or 0) in squad_ids]
    aliases = player_aliases(relevant)
    clubs = sorted({p.get('club') for p in relevant if p.get('club')})

    queries = []
    for club in clubs:
        queries += [
            f'"{club}" press conference team news injury manager Friday Premier League',
            f'"{club}" manager says fitness injury team news weekend',
        ]
    queries += [
        f'Premier League Gameweek {next_gw} press conference team news injuries',
        f'FPL Gameweek {next_gw} press conference injury news predicted lineups',
    ]

    raw = []
    for q in queries:
        raw.extend(google_news(q))
    seen, dedup = set(), []
    for x in raw:
        key = (re.sub(r'\W+',' ',x['title'].lower()).strip(), x['source'])
        if key in seen: continue
        seen.add(key); dedup.append(x)

    by_player = defaultdict(list)
    for item in dedup:
        text = f"{item['title']} {item.get('summary') or ''}"
        labels = classify(text)
        if not labels: continue
        for pid in match_players(text, aliases):
            row = dict(item)
            row['signals'] = labels
            row['weight'] = round(SOURCE_WEIGHT.get(item['source'], .58) * recency_weight(item.get('published')), 3)
            by_player[pid].append(row)

    players = []
    pool_by_id = {int(p.get('player_id') or 0):p for p in pool_rows}
    for pid, arts in by_player.items():
        p = pool_by_id.get(pid,{})
        arts.sort(key=lambda a:a.get('published') or '', reverse=True)
        signal_counts = defaultdict(float)
        for a in arts:
            for sig in a['signals']:
                signal_counts[sig] += a['weight']
        strongest = max(signal_counts.items(), key=lambda kv: kv[1], default=('INFO',0))[0]
        confidence = min(100, round(sum(a['weight'] for a in arts[:5]) * 28))
        players.append({
            'player_id': pid,
            'player': p.get('player'),
            'club': p.get('club'),
            'strongest_signal': strongest,
            'confidence': confidence,
            'signal_weights': {k:round(v,2) for k,v in signal_counts.items()},
            'source_count': len({a['source'] for a in arts}),
            'latest_published': arts[0].get('published') if arts else None,
            'articles': arts[:6],
        })
    players.sort(key=lambda x:(x['confidence'],x['source_count']), reverse=True)

    out = {
        'status':'SUCCESS',
        'generated_at_utc': now.isoformat(),
        'next_gw': next_gw,
        'hours_to_deadline': round(hours_to_deadline,1) if hours_to_deadline is not None else None,
        'friday_press_window': friday_window,
        'query_count': len(queries),
        'article_count': len(dedup),
        'players': players,
        'method_note':'Dedicated pre-deadline press-conference watch for current-squad players. Manager/team-news language is classified from public titles/search summaries and weighted by source + recency. It is evidence for availability/minutes review, not an automatic bench/transfer instruction.'
    }
    OUT.write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':'SUCCESS','friday_window':friday_window,'articles':len(dedup),'players':len(players)}))

if __name__=='__main__':
    main()
