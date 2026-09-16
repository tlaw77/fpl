import html, json, re, unicodedata, urllib.parse, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
from pathlib import Path

FPL='https://fantasy.premierleague.com/api'
FOTMOB='https://www.fotmob.com/api/data'
OUT=Path('data/schedule_load.json')
PRIMARY_COMPETITIONS={42:'Champions League',73:'Europa League',10216:'Conference League',132:'FA Cup',133:'League Cup'}
INTERNATIONAL_COMPETITIONS={
    114:'International Friendly',9806:'UEFA Nations League A',9807:'UEFA Nations League B',
    9808:'UEFA Nations League C',9809:'UEFA Nations League D',10195:'World Cup Qualification UEFA',
    10196:'World Cup Qualification CAF',10197:'World Cup Qualification AFC',
    10198:'World Cup Qualification CONCACAF',10199:'World Cup Qualification CONMEBOL',
    10200:'World Cup Qualification OFC',10201:'World Cup Qualification Inter-confederation',
}
ALIASES={'manchester united':'man utd','manchester city':'man city','tottenham hotspur':'spurs','tottenham':'spurs','wolverhampton wanderers':'wolves','brighton hove albion':'brighton','brighton and hove albion':'brighton','newcastle united':'newcastle','west ham united':'west ham','leeds united':'leeds','nottingham forest':"nott'm forest",'afc bournemouth':'bournemouth','burnley fc':'burnley'}
HEADERS={'User-Agent':'Mozilla/5.0','Accept-Language':'en-GB,en;q=0.9','Referer':'https://www.fotmob.com/'}

def get(url):
    req=urllib.request.Request(url,headers={**HEADERS,'Accept':'application/json,text/plain,*/*'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def match_page(match_id):
    req=urllib.request.Request(f'https://www.fotmob.com/match/{match_id}',headers={**HEADERS,'Accept':'text/html,application/xhtml+xml'})
    with urllib.request.urlopen(req,timeout=30) as r:body=r.read().decode('utf-8','replace')
    m=re.search(r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',body,re.S|re.I)
    if not m:return None
    try:data=json.loads(html.unescape(m.group(1)))
    except Exception:return None
    pp=((data.get('props') or {}).get('pageProps') or {})
    return pp.get('data') if isinstance(pp.get('data'),dict) and pp.get('data',{}).get('content') else pp

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

def player_index(boot,teams):
    by_club={name:{} for name in teams.values()};by_club['__all__']={}
    for p in boot.get('elements',[]):
        club=teams.get(p.get('team'))
        if not club:continue
        names={person_norm(p.get('web_name')),person_norm(p.get('second_name')),person_norm(f"{p.get('first_name','')} {p.get('second_name','')}")};names.discard('')
        for name in names:
            by_club.setdefault(club,{}).setdefault(name,[]).append(p['id'])
            by_club['__all__'].setdefault(name,[]).append(p['id'])
    return by_club

def match_player(raw_name,club,index):
    key=person_norm(raw_name);bucket=index.get(club) if club else index.get('__all__');candidates=(bucket or {}).get(key,[])
    if len(candidates)==1:return candidates[0]
    parts=key.split()
    if parts:
        surname=parts[-1];ids=set()
        for n,vals in (bucket or {}).items():
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

def numeric(v):
    if isinstance(v,(int,float)) and 0<=float(v)<=130:return float(v)
    if isinstance(v,str):
        m=re.search(r'\d+(?:\.\d+)?',v)
        if m and 0<=float(m.group())<=130:return float(m.group())
    if isinstance(v,dict):
        for k in ('value','stat','num','minutesPlayed','minsPlayed'):
            if k in v:
                n=numeric(v[k])
                if n is not None:return n
    return None

def find_minutes(obj):
    if isinstance(obj,dict):
        for k,v in obj.items():
            lk=str(k).lower().replace('_',' ')
            if lk in {'minutesplayed','minutes played','minsplayed','mins played'} or ('minute' in lk and 'subbed' not in lk):
                n=numeric(v)
                if n is not None:return n
        for v in obj.values():
            m=find_minutes(v)
            if m is not None:return m
    elif isinstance(obj,list):
        for v in obj:
            m=find_minutes(v)
            if m is not None:return m
    return None

def pname(p):
    for k in ('name','shortName','fullName'):
        v=p.get(k)
        if isinstance(v,str) and v:return v
        if isinstance(v,dict):
            for kk in ('fullName','name','displayName','lastName'):
                if isinstance(v.get(kk),str) and v.get(kk):return v[kk]
    return ''

def flatten_players(x):
    out=[]
    if isinstance(x,dict):
        if pname(x) and any(k in x for k in ('id','playerId','positionId','minutesPlayed','stats','rating','timeSubbedOn','timeSubbedOff')):out.append(x)
        else:
            for v in x.values():out.extend(flatten_players(v))
    elif isinstance(x,list):
        for v in x:out.extend(flatten_players(v))
    return out

def derive_minutes(p,started,duration=90):
    direct=find_minutes(p)
    if direct is not None:return max(0,min(float(duration),direct)),'reported'
    on=numeric(p.get('timeSubbedOn'));off=numeric(p.get('timeSubbedOff'))
    # Some payloads expose substitution timing inside an events/sub object.
    sub=(p.get('events') or {}).get('sub') if isinstance(p.get('events'),dict) else None
    if isinstance(sub,dict):
        on=on if on is not None else numeric(sub.get('subbedIn') or sub.get('timeSubbedOn'))
        off=off if off is not None else numeric(sub.get('subbedOut') or sub.get('timeSubbedOff'))
    if started:
        if off is not None:return max(0,min(float(duration),off)),'derived_substitution'
        return float(duration),'derived_full_match'
    if on is not None:return max(0,float(duration)-min(float(duration),on)),'derived_substitution'
    return 0.0,'derived_unused_bench'

def player_stat(detail,fotmob_id,key):
    stats=((detail.get('content') or {}).get('playerStats') or {}).get(str(fotmob_id),{}).get('stats') or []
    for group in stats:
        for item in (group.get('stats') or {}).values():
            if item.get('key')==key:
                value=(item.get('stat') or {}).get('value')
                if isinstance(value,(int,float)):return value
    return None

def extract_lineup(detail,club,index,side):
    content=detail.get('content') or {};line=content.get('lineup') or {};blocks=[]
    side_key='homeTeam' if side=='home' else 'awayTeam'
    if isinstance(line.get(side_key),dict):
        b=line[side_key];blocks.append((b.get('starters') or [],True));blocks.append((b.get('subs') or b.get('bench') or [],False))
    old=line.get('lineups') or line.get('lineup') or []
    if isinstance(old,list):
        for team in old:
            if not isinstance(team,dict):continue
            team_name=team.get('teamName') or (team.get('team') or {}).get('name') or ''
            if team_name and norm(team_name)!=norm(club):continue
            blocks.append((team.get('players') or [],True));blocks.append((team.get('bench') or team.get('subs') or [],False))
    rows=[];seen=set()
    for raw_players,default_started in blocks:
        for p in flatten_players(raw_players):
            name=pname(p);pid=match_player(name,club,index)
            if not pid or pid in seen:continue
            seen.add(pid);started=p.get('isStarter') if 'isStarter' in p else p.get('starter')
            if started is None:started=default_started and not bool(p.get('isSubstitute'))
            mins,source=derive_minutes(p,bool(started),90)
            reported=player_stat(detail,p.get('id'),'minutes_played')
            if reported is not None:mins,source=float(reported),'reported'
            rows.append({'player_id':pid,'name':name,'minutes':mins,'minutes_source':source,'started':bool(started),
                         'rating':player_stat(detail,p.get('id'),'rating_title'),
                         'goals':int(player_stat(detail,p.get('id'),'goals') or 0),
                         'assists':int(player_stat(detail,p.get('id'),'assists') or 0)})
    return rows

def filter_unresolved_draw_rows(rows):
    europe={'Champions League','Europa League','Conference League'}
    counts=Counter((r['club'],r['competition'],str(r['date'])[:10]) for r in rows if r['competition'] in europe)
    return [r for r in rows if r['competition'] not in europe or counts[(r['club'],r['competition'],str(r['date'])[:10])]<=1]

def main():
    boot=get(f'{FPL}/bootstrap-static/');fpl_fx=get(f'{FPL}/fixtures/');teams={t['id']:t['name'] for t in boot['teams']};team_by_norm={norm(name):name for name in teams.values()};pindex=player_index(boot,teams)
    events=boot.get('events',[]);current=next((e for e in events if e.get('is_current')),None);nxt=next((e for e in events if e.get('is_next')),None);current_gw=int((current or {}).get('id') or max([e['id'] for e in events if e.get('finished')],default=1));next_gw=int((nxt or {}).get('id') or current_gw+1)
    horizon=[f for f in fpl_fx if f.get('event') and next_gw<=int(f['event'])<next_gw+6 and f.get('kickoff_time')];dates=[iso_dt(f['kickoff_time']) for f in horizon if iso_dt(f['kickoff_time'])];now=datetime.now(timezone.utc);start=min([now-timedelta(days=8),*(dates or [now])]);end=max(dates or [now+timedelta(days=45)])+timedelta(days=3)
    failures=[];rows=[];player_rows={};seen=set();recent_matches={}
    competition_map={**PRIMARY_COMPETITIONS,**INTERNATIONAL_COMPETITIONS}
    def competition_payload(item):
        cid,label=item
        return cid,label,get(f'{FOTMOB}/leagues?{urllib.parse.urlencode({"id":cid,"ccode3":"GBR"})}')
    payloads=[]
    with ThreadPoolExecutor(max_workers=6) as executor:
        future_map={executor.submit(competition_payload,item):item for item in competition_map.items()}
        for future in as_completed(future_map):
            cid,label=future_map[future]
            try:payloads.append(future.result())
            except Exception as exc:failures.append({'competition':label,'id':cid,'error':str(exc)[:180]})
    for cid,label,payload in payloads:
        for m in collect_matches(payload):
            md=event_dt(m)
            if not md or md<start or md>end:continue
            home=m.get('home') or {};away=m.get('away') or {};mapped=[]
            for side,t in [('home',home),('away',away)]:
                nn=norm(t.get('name') or t.get('longName') or '')
                if nn in team_by_norm:mapped.append((team_by_norm[nn],side))
            is_international=cid in INTERNATIONAL_COMPETITIONS
            if not mapped and not is_international:continue
            mid=int(m['id'])
            for club,side in mapped:
                key=(mid,club)
                if key in seen:continue
                seen.add(key);rows.append({'club':club,'date':md.isoformat(),'competition':label,'competition_id':cid,'event_id':mid,'name':f"{home.get('name','')} vs {away.get('name','')}",'home_away':side})
            if md<=now-timedelta(hours=2) and md>=now-timedelta(days=8):recent_matches[mid]=(md,label,home,away,mapped,is_international)
    details={}
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_map={executor.submit(match_page,mid):(mid,row) for mid,row in recent_matches.items()}
        for future in as_completed(future_map):
            mid,row=future_map[future]
            try:details[mid]=future.result()
            except Exception as exc:failures.append({'competition':row[1],'event_id':mid,'type':'match_page','error':str(exc)[:180]})
    for mid,(md,label,home,away,mapped,is_international) in recent_matches.items():
        detail=details.get(mid)
        if not detail or not detail.get('content'):
            failures.append({'competition':label,'event_id':mid,'type':'match_page','error':'no pre-rendered match content'});continue
        for club,side in mapped:
            for a in extract_lineup(detail,club,pindex,side):player_rows.setdefault(str(a['player_id']),[]).append({'date':md.isoformat(),'competition':label,'competition_id':next((r['competition_id'] for r in rows if r['event_id']==mid),None),'event_id':mid,'name':f"{home.get('name','')} vs {away.get('name','')}",'home_away':side,'minutes':a.get('minutes'),'minutes_source':a.get('minutes_source'),'started':a.get('started'),'rating':a.get('rating'),'goals':a.get('goals',0),'assists':a.get('assists',0),'source_name':a.get('name')})
        if is_international:
            for side in ('home','away'):
                for a in extract_lineup(detail,None,pindex,side):
                    row={'date':md.isoformat(),'competition':label,'competition_id':next((k for k,v in INTERNATIONAL_COMPETITIONS.items() if v==label),None),'event_id':mid,'name':f"{home.get('name','')} vs {away.get('name','')}",'home_away':side,'minutes':a.get('minutes'),'minutes_source':a.get('minutes_source'),'started':a.get('started'),'rating':a.get('rating'),'goals':a.get('goals',0),'assists':a.get('assists',0),'source_name':a.get('name'),'international':True}
                    existing=player_rows.setdefault(str(a['player_id']),[])
                    if not any(x.get('event_id')==mid for x in existing):existing.append(row)
    for v in player_rows.values():v.sort(key=lambda x:x['date'])
    raw_count=len(rows);rows=filter_unresolved_draw_rows(rows);filtered_count=raw_count-len(rows)
    rows.sort(key=lambda x:(x['club'],x['date']));by_club={name:[] for name in teams.values()}
    for r in rows:by_club.setdefault(r['club'],[]).append({k:v for k,v in r.items() if k!='club'})
    minute_rows=[a for apps in player_rows.values() for a in apps if a.get('minutes') is not None]
    source_counts=Counter(a.get('minutes_source') for a in minute_rows)
    OUT.write_text(json.dumps({'status':'SUCCESS','generated_at_utc':now.isoformat(),'current_gw':current_gw,'next_gw':next_gw,'source':'FotMob public league feed + pre-rendered match pages','coverage':list(competition_map.values()),'club_competition_ids':PRIMARY_COMPETITIONS,'international_competition_ids':INTERNATIONAL_COMPETITIONS,'range_start':start.isoformat(),'range_end':end.isoformat(),'clubs':by_club,'players':player_rows,'player_minutes_lookback_days':8,'player_minute_observations':len(minute_rows),'minute_source_counts':dict(source_counts),'unresolved_draw_rows_filtered':filtered_count,'failures':failures},indent=2,ensure_ascii=False)+'\n')
    print(f'Wrote {OUT} with {len(rows)} club-fixture rows, {len(player_rows)} player workload records, {len(minute_rows)} minute observations {dict(source_counts)}; filtered={filtered_count} failures={len(failures)}')
if __name__=='__main__':main()
