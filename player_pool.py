import json, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE='https://fantasy.premierleague.com/api'
LATEST=Path('data/latest.json'); OUT=Path('data/player_pool.json'); SCHEDULE=Path('data/schedule_load.json')

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'fpl-player-pool/1.2'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def dt(s):
    if not s:return None
    return datetime.fromisoformat(str(s).replace('Z','+00:00'))

def rest_modifier(days):
    if days is None:return 1.0
    if days<=2.5:return .82
    if days<=3.5:return .88
    if days<=4.5:return .94
    return 1.0

def main():
    b=get(f'{BASE}/bootstrap-static/'); fixtures=get(f'{BASE}/fixtures/')
    latest=json.loads(LATEST.read_text())
    schedule=json.loads(SCHEDULE.read_text()) if SCHEDULE.exists() else {'clubs':{}}
    current_gw=int(latest.get('current_gw') or 1); next_gw=int(latest.get('next_gw') or current_gw+1)
    reliability=min(1.0,max(.20,current_gw/5.0))
    teams={t['id']:t['name'] for t in b['teams']}; pos={x['id']:x['singular_name_short'] for x in b['element_types']}
    fx=defaultdict(list)
    for f in fixtures:
        gw=f.get('event')
        if gw is None or gw<next_gw or gw>=next_gw+6:continue
        ko=dt(f.get('kickoff_time'))
        for tid,oid,venue,key in [(f['team_h'],f['team_a'],'H','team_h_difficulty'),(f['team_a'],f['team_h'],'A','team_a_difficulty')]:
            fx[tid].append({'gw':gw,'opponent':teams.get(oid,''),'venue':venue,'difficulty':f.get(key) or 3,'kickoff_time':f.get('kickoff_time')})
    for v in fx.values():v.sort(key=lambda x:(x['gw'],x.get('kickoff_time') or ''))
    exposure={x.get('player_id'):x for x in latest.get('player_exposure',[])}
    mine={x.get('player_id') for x in (latest.get('current_squad_next5') or latest.get('squad_next5') or [])}
    rows=[]
    for p in b['elements']:
        if p.get('status')=='u':continue
        fs=fx.get(p['team'],[])[:6]
        if not fs:continue
        club=teams[p['team']]
        extras=(schedule.get('clubs') or {}).get(club,[])
        diffs=[float(f['difficulty']) for f in fs]; ease=6-(sum(diffs)/len(diffs))
        avail=(p.get('chance_of_playing_next_round') if p.get('chance_of_playing_next_round') is not None else 100)/100
        form=float(p.get('form') or 0); ppg=float(p.get('points_per_game') or 0); global_own=float(p.get('selected_by_percent') or 0)
        mini=float((exposure.get(p['id']) or {}).get('ownership_pct') or 0); eo=float((exposure.get(p['id']) or {}).get('effective_ownership_pct') or mini)

        next_ko=dt(fs[0].get('kickoff_time'))
        prior=[]
        if next_ko:
            for e in extras:
                ed=dt(e.get('date'))
                if ed and ed<next_ko and (next_ko-ed).total_seconds()<=6*86400:
                    prior.append((ed,e))
        prior.sort(key=lambda x:x[0],reverse=True)
        closest=prior[0] if prior else None
        rest_days=((next_ko-closest[0]).total_seconds()/86400) if closest and next_ko else None
        sched_mod=rest_modifier(rest_days)
        adjusted_avail=max(0,min(1,avail*sched_mod))
        horizon_extra=[]
        horizon_start=dt(fs[0].get('kickoff_time')) if fs else None
        horizon_end=dt(fs[-1].get('kickoff_time')) if fs else None
        if horizon_start and horizon_end:
            horizon_extra=[e for e in extras if dt(e.get('date')) and horizon_start-datetime.resolution<=dt(e.get('date'))<=horizon_end+datetime.resolution]
        congestion_penalty=min(1.2,len(horizon_extra)*.12+(1-sched_mod)*2.0)

        observed=(min(form,12)*1.15+min(ppg,12)*.95)*reliability
        score=round(observed+ease*2.15+adjusted_avail*1.8+global_own*.045+mini*.018-congestion_penalty,2)
        role='Shield' if eo>=75 else ('Neutral' if eo>=40 else 'Leverage')
        schedule_risk='High' if sched_mod<=.84 else ('Medium' if sched_mod<1 or len(horizon_extra)>=3 else 'Low')
        schedule_note='No known club congestion before next PL fixture'
        if closest:
            schedule_note=f"{closest[1].get('competition','Midweek match')} · {rest_days:.1f}-day turnaround"
        elif horizon_extra:
            schedule_note=f"{len(horizon_extra)} non-PL club fixture{'s' if len(horizon_extra)!=1 else ''} in 6-GW horizon"
        rows.append({'player_id':p['id'],'player':p['web_name'],'club':club,'position':pos[p['element_type']],'price':p['now_cost']/10,
                     'availability':avail,'adjusted_availability':round(adjusted_avail,3),'schedule_modifier':round(sched_mod,3),
                     'schedule_risk':schedule_risk,'schedule_note':schedule_note,'extra_club_fixtures_6gw':len(horizon_extra),
                     'days_rest_before_next_pl':round(rest_days,1) if rest_days is not None else None,
                     'global_ownership_pct':global_own,'mini_league_ownership_pct':mini,'effective_ownership_pct':eo,'role':role,
                     'form':form,'points_per_game':ppg,'fixtures':fs,'fixture_ease_6':round(ease,2),'six_gw_score':score,
                     'sample_reliability':round(reliability,2),'in_public_squad':p['id'] in mine,'news':p.get('news') or ''})
    rows.sort(key=lambda x:x['six_gw_score'],reverse=True)
    OUT.write_text(json.dumps({'status':'SUCCESS','generated_at_utc':datetime.now(timezone.utc).isoformat(),'current_gw':current_gw,'next_gw':next_gw,
                               'horizon':6,'sample_reliability':round(reliability,2),'schedule_load_source':schedule.get('source'),
                               'schedule_load_coverage':schedule.get('coverage',[]),'players':rows},indent=2,ensure_ascii=False)+'\n')
    print(f'Wrote {OUT} with {len(rows)} players, reliability={reliability:.2f}')
if __name__=='__main__':main()
