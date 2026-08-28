import json, re, unicodedata, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

FPL='https://fantasy.premierleague.com/api'
ESPN='https://site.api.espn.com/apis/site/v2/sports/soccer'
OUT=Path('data/schedule_load.json')
LEAGUES={
    'uefa.champions':'Champions League','uefa.champions_qual':'Champions League qualifying',
    'uefa.europa':'Europa League','uefa.europa_qual':'Europa League qualifying',
    'uefa.europa.conf':'Conference League','uefa.europa.conf_qual':'Conference League qualifying',
    'eng.fa':'FA Cup','eng.league_cup':'League Cup',
}
ALIASES={'manchester united':'man utd','manchester city':'man city','tottenham hotspur':'spurs','tottenham':'spurs','wolverhampton wanderers':'wolves','brighton hove albion':'brighton','brighton and hove albion':'brighton','newcastle united':'newcastle','west ham united':'west ham','leeds united':'leeds','nottingham forest':"nott'm forest",'afc bournemouth':'bournemouth','burnley fc':'burnley','chelsea fc':'chelsea','arsenal fc':'arsenal','liverpool fc':'liverpool','everton fc':'everton','fulham fc':'fulham','brentford fc':'brentford','crystal palace':'crystal palace'}

def get(url):
    headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/150 Safari/537.36','Accept':'application/json,text/plain,*/*','Accept-Language':'en-GB,en;q=0.9','Referer':'https://www.espn.com/','Origin':'https://www.espn.com'}
    req=urllib.request.Request(url,headers=headers)
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def norm(s):
    s=str(s or '').lower().replace('&','and');s=re.sub(r'\b(fc|afc)\b','',s);s=re.sub(r'[^a-z0-9]+',' ',s).strip();return ALIASES.get(s,s)

def person_norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower();return re.sub(r'[^a-z0-9]+',' ',s).strip()

def iso_dt(s): return datetime.fromisoformat(s.replace('Z','+00:00')) if s else None

def minute_value(v):
    if v is None:return None
    m=re.search(r'\d+(?:\.\d+)?',str(v));return float(m.group()) if m else None

def player_index(boot,teams):
    by_club={name:{} for name in teams.values()}
    for p in boot.get('elements',[]):
        club=teams.get(p.get('team'))
        if not club:continue
        names={person_norm(p.get('web_name')),person_norm(p.get('second_name')),person_norm(f"{p.get('first_name','')} {p.get('second_name','')}")};names.discard('')
        for name in names:by_club.setdefault(club,{}).setdefault(name,[]).append(p['id'])
    return by_club

def match_player(raw_name,club,index):
    key=person_norm(raw_name); candidates=(index.get(club) or {}).get(key,[])
    if len(candidates)==1:return candidates[0]
    parts=key.split()
    if parts:
        surname=parts[-1];ids=set()
        for n,vals in (index.get(club) or {}).items():
            if n.split() and n.split()[-1]==surname:ids.update(vals)
        if len(ids)==1:return next(iter(ids))
    return None

def extract_player_minutes(summary,club,index):
    out=[]
    for team_block in (summary.get('boxscore') or {}).get('players',[]) or []:
        raw_team=(team_block.get('team') or {}).get('displayName') or (team_block.get('team') or {}).get('name') or ''
        if norm(raw_team)!=norm(club):continue
        for stat_block in team_block.get('statistics',[]) or []:
            labels=[str(x).lower() for x in (stat_block.get('labels') or stat_block.get('names') or [])]
            min_idx=next((i for i,x in enumerate(labels) if x in {'min','mins','minutes'} or 'minute' in x),None)
            for a in stat_block.get('athletes',[]) or []:
                athlete=a.get('athlete') or {};name=athlete.get('displayName') or athlete.get('shortName') or athlete.get('fullName') or '';pid=match_player(name,club,index)
                if not pid:continue
                stats=a.get('stats') or [];mins=minute_value(stats[min_idx]) if min_idx is not None and min_idx<len(stats) else minute_value(a.get('minutes'))
                if mins is None: mins=90.0 if a.get('starter') is True else (0.0 if a.get('didNotPlay') else None)
                out.append({'player_id':pid,'name':name,'minutes':mins,'started':bool(a.get('starter'))})
    best={}
    for row in out:
        old=best.get(row['player_id'])
        if old is None or (row.get('minutes') is not None and old.get('minutes') is None):best[row['player_id']]=row
    return list(best.values())

def main():
    boot=get(f'{FPL}/bootstrap-static/');fpl_fx=get(f'{FPL}/fixtures/');teams={t['id']:t['name'] for t in boot['teams']};team_by_norm={norm(name):name for name in teams.values()};pindex=player_index(boot,teams)
    events=boot.get('events',[]);current=next((e for e in events if e.get('is_current')),None);nxt=next((e for e in events if e.get('is_next')),None);current_gw=int((current or {}).get('id') or max([e['id'] for e in events if e.get('finished')],default=1));next_gw=int((nxt or {}).get('id') or current_gw+1)
    horizon=[f for f in fpl_fx if f.get('event') and next_gw<=int(f['event'])<next_gw+6 and f.get('kickoff_time')];dates=[iso_dt(f['kickoff_time']) for f in horizon if iso_dt(f['kickoff_time'])];now=datetime.now(timezone.utc);start=min([now-timedelta(days=8),*(dates or [now])]);end=max(dates or [now+timedelta(days=45)])+timedelta(days=3);dr=f"{start:%Y%m%d}-{end:%Y%m%d}"
    rows=[];seen=set();failures=[];event_meta={}
    for slug,label in LEAGUES.items():
        try:data=get(f'{ESPN}/{slug}/scoreboard?{urllib.parse.urlencode({"dates":dr,"limit":500})}')
        except Exception as exc:failures.append({'league':slug,'error':str(exc)[:180]});continue
        for ev in data.get('events',[]):
            dt=iso_dt(ev.get('date'));comp=(ev.get('competitions') or [{}])[0];mapped=[]
            for c in comp.get('competitors') or []:
                team=c.get('team') or {};raw=team.get('displayName') or team.get('shortDisplayName') or team.get('name') or '';nn=norm(raw)
                if nn in team_by_norm:mapped.append((team_by_norm[nn],c.get('homeAway')))
            if not mapped or not dt:continue
            key=(ev.get('id'),slug)
            if key in seen:continue
            seen.add(key);event_meta[key]={'date':dt,'slug':slug,'label':label,'event':ev,'clubs':mapped}
            for club,home_away in mapped:rows.append({'club':club,'date':dt.isoformat(),'competition':label,'competition_slug':slug,'event_id':ev.get('id'),'name':ev.get('name') or ev.get('shortName') or '','home_away':home_away})
    player_rows={};recent_cutoff=now-timedelta(days=8)
    for (event_id,slug),meta in event_meta.items():
        if not event_id or meta['date']>now or meta['date']<recent_cutoff:continue
        try:summary=get(f'{ESPN}/{slug}/summary?event={event_id}')
        except Exception as exc:failures.append({'league':slug,'event_id':event_id,'type':'summary','error':str(exc)[:180]});continue
        for club,home_away in meta['clubs']:
            for a in extract_player_minutes(summary,club,pindex):player_rows.setdefault(str(a['player_id']),[]).append({'date':meta['date'].isoformat(),'competition':meta['label'],'competition_slug':slug,'event_id':event_id,'name':meta['event'].get('name') or meta['event'].get('shortName') or '','home_away':home_away,'minutes':a.get('minutes'),'started':a.get('started'),'source_name':a.get('name')})
    for v in player_rows.values():v.sort(key=lambda x:x['date'])
    rows.sort(key=lambda x:(x['club'],x['date']));by_club={name:[] for name in teams.values()}
    for r in rows:by_club.setdefault(r['club'],[]).append({k:v for k,v in r.items() if k!='club'})
    OUT.write_text(json.dumps({'status':'SUCCESS','generated_at_utc':now.isoformat(),'current_gw':current_gw,'next_gw':next_gw,'source':'ESPN public scoreboard + match summaries','coverage':list(LEAGUES.values()),'range_start':start.isoformat(),'range_end':end.isoformat(),'clubs':by_club,'players':player_rows,'player_minutes_lookback_days':8,'failures':failures},indent=2,ensure_ascii=False)+'\n')
    print(f'Wrote {OUT} with {len(rows)} club-fixture rows and {len(player_rows)} player workload records; failures={len(failures)}')
if __name__=='__main__':main()
