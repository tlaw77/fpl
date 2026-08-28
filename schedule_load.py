import json, re, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

FPL='https://fantasy.premierleague.com/api'
ESPN='https://site.api.espn.com/apis/site/v2/sports/soccer'
OUT=Path('data/schedule_load.json')
LEAGUES={
    'uefa.champions':'Champions League',
    'uefa.champions_qual':'Champions League qualifying',
    'uefa.europa':'Europa League',
    'uefa.europa_qual':'Europa League qualifying',
    'uefa.europa.conf':'Conference League',
    'uefa.europa.conf_qual':'Conference League qualifying',
    'eng.fa':'FA Cup',
    'eng.league_cup':'League Cup',
}
ALIASES={
    'manchester united':'man utd','manchester city':'man city','tottenham hotspur':'tottenham',
    'wolverhampton wanderers':'wolves','brighton hove albion':'brighton','brighton and hove albion':'brighton',
    'newcastle united':'newcastle','west ham united':'west ham','leeds united':'leeds',
    'nottingham forest':'nottm forest','afc bournemouth':'bournemouth','burnley fc':'burnley',
    'chelsea fc':'chelsea','arsenal fc':'arsenal','liverpool fc':'liverpool','everton fc':'everton',
    'fulham fc':'fulham','brentford fc':'brentford','crystal palace':'crystal palace',
}

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'fpl-schedule-load/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def norm(s):
    s=str(s or '').lower().replace('&','and')
    s=re.sub(r'\b(fc|afc)\b','',s)
    s=re.sub(r'[^a-z0-9]+',' ',s).strip()
    return ALIASES.get(s,s)

def iso_dt(s):
    if not s:return None
    return datetime.fromisoformat(s.replace('Z','+00:00'))

def main():
    boot=get(f'{FPL}/bootstrap-static/')
    fpl_fx=get(f'{FPL}/fixtures/')
    teams={t['id']:t['name'] for t in boot['teams']}
    team_by_norm={norm(name):name for name in teams.values()}
    events=boot.get('events',[])
    current=next((e for e in events if e.get('is_current')),None)
    nxt=next((e for e in events if e.get('is_next')),None)
    current_gw=int((current or {}).get('id') or max([e['id'] for e in events if e.get('finished')],default=1))
    next_gw=int((nxt or {}).get('id') or current_gw+1)
    horizon=[f for f in fpl_fx if f.get('event') and next_gw<=int(f['event'])<next_gw+6 and f.get('kickoff_time')]
    dates=[iso_dt(f['kickoff_time']) for f in horizon if iso_dt(f['kickoff_time'])]
    now=datetime.now(timezone.utc)
    start=min([now-timedelta(days=7),*(dates or [now])])
    end=max(dates or [now+timedelta(days=45)])+timedelta(days=3)
    dr=f"{start:%Y%m%d}-{end:%Y%m%d}"
    rows=[]
    seen=set()
    failures=[]
    for slug,label in LEAGUES.items():
        try:data=get(f'{ESPN}/{slug}/scoreboard?{urllib.parse.urlencode({"dates":dr,"limit":500})}')
        except Exception as exc:
            failures.append({'league':slug,'error':str(exc)[:180]});continue
        for ev in data.get('events',[]):
            dt=iso_dt(ev.get('date'))
            comp=(ev.get('competitions') or [{}])[0]
            comps=comp.get('competitors') or []
            names=[]
            for c in comps:
                team=c.get('team') or {}
                raw=team.get('displayName') or team.get('shortDisplayName') or team.get('name') or ''
                nn=norm(raw)
                if nn in team_by_norm:names.append(team_by_norm[nn])
            if not names or not dt:continue
            key=(ev.get('id'),slug)
            if key in seen:continue
            seen.add(key)
            for club in names:
                rows.append({'club':club,'date':dt.isoformat(),'competition':label,'competition_slug':slug,'event_id':ev.get('id'),'name':ev.get('name') or ev.get('shortName') or ''})
    rows.sort(key=lambda x:(x['club'],x['date']))
    by_club={name:[] for name in teams.values()}
    for r in rows:by_club.setdefault(r['club'],[]).append({k:v for k,v in r.items() if k!='club'})
    OUT.write_text(json.dumps({
        'status':'SUCCESS','generated_at_utc':now.isoformat(),'current_gw':current_gw,'next_gw':next_gw,
        'source':'ESPN public scoreboard','coverage':list(LEAGUES.values()),'range_start':start.isoformat(),'range_end':end.isoformat(),
        'clubs':by_club,'failures':failures
    },indent=2,ensure_ascii=False)+'\n')
    print(f'Wrote {OUT} with {len(rows)} club-fixture rows; failures={len(failures)}')

if __name__=='__main__':main()
