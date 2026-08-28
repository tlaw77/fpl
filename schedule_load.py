import json, re, unicodedata, urllib.parse, urllib.request
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path

FPL='https://fantasy.premierleague.com/api'
FOTMOB='https://www.fotmob.com/api/data'
OUT=Path('data/schedule_load.json')
PRIMARY_COMPETITIONS={42:'Champions League',73:'Europa League',10216:'Conference League',132:'FA Cup',133:'League Cup'}
ALIASES={'manchester united':'man utd','manchester city':'man city','tottenham hotspur':'spurs','tottenham':'spurs','wolverhampton wanderers':'wolves','brighton hove albion':'brighton','brighton and hove albion':'brighton','newcastle united':'newcastle','west ham united':'west ham','leeds united':'leeds','nottingham forest':"nott'm forest",'afc bournemouth':'bournemouth','burnley fc':'burnley'}

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Accept':'application/json,text/plain,*/*','Accept-Language':'en-GB,en;q=0.9','Referer':'https://www.fotmob.com/'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower().replace('&','and');s=re.sub(r'\b(fc|afc)\b','',s);s=re.sub(r'[^a-z0-9]+',' ',s).strip();return ALIASES.get(s,s)

def person_norm(s):
    s=unicodedata.normalize('NFKD',str(s or '')).encode('ascii','ignore').decode().lower();return re.sub(r'[^a-z0-9]+',' ',s).strip()

def iso_dt(s):
    if not s:return None
    try:return datetime.fromisoformat(str(s).replace('Z','+00:00'))
    except:return None

def event_dt(m):
    st=m.get('status') or {}
    for raw in (st.get('utcTime'),m.get('utcTime'),m.get('matchTimeUTCDate'),m.get('date')):
        d=iso_dt(raw)
        if d:return d
    for raw in (m.get('timeTS'),st.get('timeTS')):
        try:return datetime.fromtimestamp(float(raw),timezone.utc)
        except:pass
    return None

def event_finished(m):
    st=m.get('status') or {};d=event_dt(m)
    return bool(st.get('finished') or (st.get('started') and d and d<datetime.now(timezone.utc)-timedelta(hours=2)))

def player_index(boot,teams):
    by_club={name:{} for name in teams.values()}
    for p in boot.get('elements',[]):
        club=teams.get(p.get('team'))
        if not club:continue
        names={person_norm(p.get('web_name')),person_norm(p.get('second_name')),person_norm(f"{p.get('first_name','')} {p.get('second_name','')}")};names.discard('')
        for name in names:by_club.setdefault(club,{}).setdefault(name,[]).append(p['id'])
    return by_club

def match_player(raw_name,club,index):
    key=person_norm(raw_name);candidates=(index.get(club) or {}).get(key,[])
    if len(candidates)==1:return candidates[0]
    parts=key.split()
    if parts:
        surname=parts[-1];ids=set()
        for n,vals in (index.get(club) or {}).items():
            if n.split() and n.split()[-1]==surname:ids.update(vals)
        if len(ids)==1:return next(iter(ids))
    return None

def collect_matches(payload):
    out={}
    def walk(x):
        if isinstance(x,dict):
            if x.get('id') is not None and isinstance(x.get('home'),dict) and isinstance(x.get('away'),dict):
                try:out[int(x['id'])]=x
                except:pass
            for v in x.values():walk(v)
        elif isinstance(x,list):
            for v in x:walk(v)
    walk(payload);return list(out.values())

def find_minutes(obj):
    if isinstance(obj,dict):
        for k,v in obj.items():
            if 'minute' in str(k).lower() and isinstance(v,(int,float)) and 0<=float(v)<=130:return float(v)
        for v in obj.values():
            m=find_minutes(v)
            if m is not None:return m
    elif isinstance(obj,list):
        for v in obj:
            m=find_minutes(v)
            if m is not None:return m
    return None

def extract_lineup(detail,club,index):
    lineup=((detail.get('content') or {}).get('lineup') or {}).get('lineups') or [];rows=[]
    for team in lineup:
        team_name=team.get('teamName') or (team.get('team') or {}).get('name') or ''
        if norm(team_name)!=norm(club):continue
        for p in team.get('players') or []:
            name=p.get('name') or (p.get('player') or {}).get('name') or (p.get('player') or {}).get('displayName') or '';pid=match_player(name,club,index)
            if not pid:continue
            mins=find_minutes(p);started=p.get('isStarter') if 'isStarter' in p else p.get('starter')
            if started is None:started=bool(p.get('positionId') or p.get('positionString')) and not bool(p.get('isSubstitute'))
            rows.append({'player_id':pid,'name':name,'minutes':mins,'started':bool(started)})
    return rows

def filter_unresolved_draw_rows(rows):
    # FotMob can expose all possible league-phase pairings with one placeholder draw date.
    # A club cannot play multiple opponents in the same competition on the same day,
    # so suppress those rows until the feed resolves them to real dates.
    europe={'Champions League','Europa League','Conference League'}
    counts=Counter((r['club'],r['competition'],str(r['date'])[:10]) for r in rows if r['competition'] in europe)
    return [r for r in rows if r['competition'] not in europe or counts[(r['club'],r['competition'],str(r['date'])[:10])]<=1]

def main():
    boot=get(f'{FPL}/bootstrap-static/');fpl_fx=get(f'{FPL}/fixtures/');teams={t['id']:t['name'] for t in boot['teams']};team_by_norm={norm(name):name for name in teams.values()};pindex=player_index(boot,teams)
    events=boot.get('events',[]);current=next((e for e in events if e.get('is_current')),None);nxt=next((e for e in events if e.get('is_next')),None);current_gw=int((current or {}).get('id') or max([e['id'] for e in events if e.get('finished')],default=1));next_gw=int((nxt or {}).get('id') or current_gw+1)
    horizon=[f for f in fpl_fx if f.get('event') and next_gw<=int(f['event'])<next_gw+6 and f.get('kickoff_time')];dates=[iso_dt(f['kickoff_time']) for f in horizon if iso_dt(f['kickoff_time'])];now=datetime.now(timezone.utc);start=min([now-timedelta(days=8),*(dates or [now])]);end=max(dates or [now+timedelta(days=45)])+timedelta(days=3)
    failures=[];rows=[];player_rows={};seen=set()
    for cid,label in PRIMARY_COMPETITIONS.items():
        try:payload=get(f'{FOTMOB}/leagues?{urllib.parse.urlencode({"id":cid,"ccode3":"GBR"})}')
        except Exception as exc:failures.append({'competition':label,'id':cid,'error':str(exc)[:180]});continue
        for m in collect_matches(payload):
            md=event_dt(m)
            if not md or md<start or md>end:continue
            home=m.get('home') or {};away=m.get('away') or {};mapped=[]
            for side,t in [('home',home),('away',away)]:
                nn=norm(t.get('name') or t.get('longName') or '')
                if nn in team_by_norm:mapped.append((team_by_norm[nn],side))
            if not mapped:continue
            mid=int(m['id'])
            for club,side in mapped:
                key=(mid,club)
                if key in seen:continue
                seen.add(key);rows.append({'club':club,'date':md.isoformat(),'competition':label,'competition_id':cid,'event_id':mid,'name':f"{home.get('name','')} vs {away.get('name','')}",'home_away':side})
            if md<=now and md>=now-timedelta(days=8) and event_finished(m):
                try:detail=get(f'{FOTMOB}/matchDetails?{urllib.parse.urlencode({"matchId":mid})}')
                except Exception as exc:failures.append({'competition':label,'event_id':mid,'type':'matchDetails','error':str(exc)[:180]});continue
                for club,side in mapped:
                    for a in extract_lineup(detail,club,pindex):player_rows.setdefault(str(a['player_id']),[]).append({'date':md.isoformat(),'competition':label,'competition_id':cid,'event_id':mid,'name':f"{home.get('name','')} vs {away.get('name','')}",'home_away':side,'minutes':a.get('minutes'),'started':a.get('started'),'source_name':a.get('name')})
    for v in player_rows.values():v.sort(key=lambda x:x['date'])
    raw_count=len(rows);rows=filter_unresolved_draw_rows(rows);filtered_count=raw_count-len(rows)
    rows.sort(key=lambda x:(x['club'],x['date']));by_club={name:[] for name in teams.values()}
    for r in rows:by_club.setdefault(r['club'],[]).append({k:v for k,v in r.items() if k!='club'})
    OUT.write_text(json.dumps({'status':'SUCCESS','generated_at_utc':now.isoformat(),'current_gw':current_gw,'next_gw':next_gw,'source':'FotMob public data API','coverage':list(PRIMARY_COMPETITIONS.values()),'competition_ids':PRIMARY_COMPETITIONS,'range_start':start.isoformat(),'range_end':end.isoformat(),'clubs':by_club,'players':player_rows,'player_minutes_lookback_days':8,'unresolved_draw_rows_filtered':filtered_count,'failures':failures},indent=2,ensure_ascii=False)+'\n')
    print(f'Wrote {OUT} with {len(rows)} club-fixture rows and {len(player_rows)} player workload records; filtered={filtered_count} failures={len(failures)}')
if __name__=='__main__':main()
