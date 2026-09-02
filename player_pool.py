import json, urllib.request, math, statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE='https://fantasy.premierleague.com/api'
LATEST=Path('data/latest.json'); OUT=Path('data/player_pool.json'); SCHEDULE=Path('data/schedule_load.json')

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'fpl-player-pool/1.4'})
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

def workload_modifier(base_mod,minutes,away=False):
    if minutes is None:return base_mod
    mins=max(0,min(120,float(minutes)))
    participation=min(1.0,mins/90.0)
    mod=1.0-(1.0-base_mod)*participation
    if away and mins>=60:mod-=.015
    return max(.78,min(1.0,mod))

def workload_band(minutes):
    if minutes is None:return 'Unknown'
    if minutes>=80:return 'Heavy'
    if minutes>=55:return 'Moderate'
    if minutes>=25:return 'Light'
    return 'Rested / cameo'

def poisson_tail(lam,threshold):
    """P(X >= threshold) for Poisson(lam), bounded for safe early-season use."""
    lam=max(0.0,min(40.0,float(lam or 0)))
    threshold=max(1,int(threshold))
    term=math.exp(-lam)
    cdf=term
    for k in range(1,threshold):
        term*=lam/k
        cdf+=term
    return max(0.0,min(1.0,1.0-cdf))

def dc_threshold(position):
    return 10 if position=='DEF' else (12 if position in ('MID','FWD') else None)

def dc_band(expected_points):
    if expected_points is None:return 'N/A'
    if expected_points>=1.35:return 'Strong floor'
    if expected_points>=.85:return 'Useful floor'
    if expected_points>=.40:return 'Some floor'
    return 'Low floor'

def main():
    b=get(f'{BASE}/bootstrap-static/'); fixtures=get(f'{BASE}/fixtures/')
    latest=json.loads(LATEST.read_text())
    schedule=json.loads(SCHEDULE.read_text()) if SCHEDULE.exists() else {'clubs':{},'players':{}}
    current_gw=int(latest.get('current_gw') or 1); next_gw=int(latest.get('next_gw') or current_gw+1)
    reliability=min(1.0,max(.20,current_gw/5.0))
    teams={t['id']:t['name'] for t in b['teams']}; pos={x['id']:x['singular_name_short'] for x in b['element_types']}
    fx=defaultdict(list)
    for f in fixtures:
        gw=f.get('event')
        if gw is None or gw<next_gw or gw>=next_gw+6:continue
        for tid,oid,venue,key in [(f['team_h'],f['team_a'],'H','team_h_difficulty'),(f['team_a'],f['team_h'],'A','team_a_difficulty')]:
            fx[tid].append({'gw':gw,'opponent':teams.get(oid,''),'venue':venue,'difficulty':f.get(key) or 3,'kickoff_time':f.get('kickoff_time')})
    for v in fx.values():v.sort(key=lambda x:(x['gw'],x.get('kickoff_time') or ''))
    exposure={x.get('player_id'):x for x in latest.get('player_exposure',[])}
    mine={x.get('player_id') for x in (latest.get('current_squad_next5') or latest.get('squad_next5') or [])}
    player_load=(schedule.get('players') or {})
    rows=[]
    for p in b['elements']:
        if p.get('status')=='u':continue
        fs=fx.get(p['team'],[])[:6]
        if not fs:continue
        club=teams[p['team']]
        position=pos[p['element_type']]
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
        club_sched_mod=rest_modifier(rest_days)

        recent_apps=[]
        for a in player_load.get(str(p['id']),[]):
            ad=dt(a.get('date'))
            if next_ko and ad and ad<next_ko and (next_ko-ad).total_seconds()<=8*86400:
                recent_apps.append((ad,a))
        recent_apps.sort(key=lambda x:x[0],reverse=True)
        closest_app=recent_apps[0] if recent_apps else None
        midweek_minutes=closest_app[1].get('minutes') if closest_app else None
        midweek_started=bool(closest_app[1].get('started')) if closest_app else None
        midweek_away=(closest_app[1].get('home_away')=='away') if closest_app else False
        player_sched_mod=workload_modifier(club_sched_mod,midweek_minutes,midweek_away) if closest else 1.0
        adjusted_avail=max(0,min(1,avail*player_sched_mod))

        horizon_extra=[]
        horizon_start=dt(fs[0].get('kickoff_time')) if fs else None
        horizon_end=dt(fs[-1].get('kickoff_time')) if fs else None
        if horizon_start and horizon_end:
            horizon_extra=[e for e in extras if dt(e.get('date')) and horizon_start-datetime.resolution<=dt(e.get('date'))<=horizon_end+datetime.resolution]
        congestion_penalty=min(1.2,len(horizon_extra)*.10+(1-player_sched_mod)*2.2)

        observed=(min(form,12)*1.15+min(ppg,12)*.95)*reliability
        score=observed+ease*2.15+adjusted_avail*1.8+global_own*.045+mini*.018-congestion_penalty
        role='Shield' if eo>=75 else ('Neutral' if eo>=40 else 'Leverage')
        schedule_risk='High' if player_sched_mod<=.84 else ('Medium' if player_sched_mod<.97 or len(horizon_extra)>=3 else 'Low')
        schedule_note='No known club congestion before next PL fixture'
        if closest:
            comp=closest[1].get('competition','Midweek match')
            if closest_app and closest_app[1].get('event_id')==closest[1].get('event_id') and midweek_minutes is not None:
                schedule_note=f"{comp} · {midweek_minutes:.0f} mins · {rest_days:.1f}-day turnaround"
                if midweek_away:schedule_note+=' · away travel'
            else:
                schedule_note=f"{comp} · {rest_days:.1f}-day turnaround · player minutes unavailable"
        elif horizon_extra:
            schedule_note=f"{len(horizon_extra)} non-PL club fixture{'s' if len(horizon_extra)!=1 else ''} in 6-GW horizon"

        recent_minutes=sum(float(a.get('minutes') or 0) for _,a in recent_apps if a.get('minutes') is not None)
        threshold=dc_threshold(position)
        dc90=float(p.get('defensive_contribution_per_90') or 0) if threshold else None
        dc_total=float(p.get('defensive_contribution') or 0) if threshold else None
        dc_prob=poisson_tail(dc90,threshold) if threshold else None
        dc_xpts=2.0*dc_prob if threshold else None
        rows.append({'player_id':p['id'],'player':p['web_name'],'club':club,'position':position,'price':p['now_cost']/10,
                     'availability':avail,'adjusted_availability':round(adjusted_avail,3),'schedule_modifier':round(player_sched_mod,3),
                     'club_schedule_modifier':round(club_sched_mod,3),'schedule_risk':schedule_risk,'schedule_note':schedule_note,
                     'extra_club_fixtures_6gw':len(horizon_extra),'days_rest_before_next_pl':round(rest_days,1) if rest_days is not None else None,
                     'midweek_minutes':round(float(midweek_minutes),1) if midweek_minutes is not None else None,
                     'midweek_started':midweek_started,'midweek_away':midweek_away if closest_app else None,
                     'midweek_workload':workload_band(midweek_minutes),'recent_non_pl_minutes':round(recent_minutes,1),
                     'player_workload_observed':midweek_minutes is not None,
                     'global_ownership_pct':global_own,'mini_league_ownership_pct':mini,'effective_ownership_pct':eo,'role':role,
                     'form':form,'points_per_game':ppg,'fixtures':fs,'fixture_ease_6':round(ease,2),'six_gw_score_base':round(score,2),
                     'sample_reliability':round(reliability,2),'in_public_squad':p['id'] in mine,'news':p.get('news') or '',
                     'defensive_contribution':round(dc_total,2) if dc_total is not None else None,
                     'defensive_contribution_per_90':round(dc90,3) if dc90 is not None else None,
                     'defcon_threshold':threshold,
                     'defcon_hit_probability':round(dc_prob,3) if dc_prob is not None else None,
                     'defcon_expected_points_per_90':round(dc_xpts,3) if dc_xpts is not None else None,
                     'defcon_floor_band':dc_band(dc_xpts)})

    pos_dc={k:[] for k in ('DEF','MID','FWD')}
    for r in rows:
        if r['position'] in pos_dc and r.get('defcon_expected_points_per_90') is not None:
            pos_dc[r['position']].append(float(r['defcon_expected_points_per_90']))
    baselines={k:(statistics.median(v) if v else 0.0) for k,v in pos_dc.items()}
    for r in rows:
        x=r.get('defcon_expected_points_per_90')
        baseline=baselines.get(r['position'])
        edge=(float(x)-baseline) if x is not None and baseline is not None else 0.0
        r['defcon_position_baseline_xpts']=round(baseline,3) if baseline is not None else None
        r['defcon_edge_per_90']=round(edge,3) if x is not None else None
        r['six_gw_score']=round(float(r['six_gw_score_base'])+max(-.45,min(.45,edge))*reliability*1.4,2)

    rows.sort(key=lambda x:x['six_gw_score'],reverse=True)
    OUT.write_text(json.dumps({'status':'SUCCESS','generated_at_utc':datetime.now(timezone.utc).isoformat(),'current_gw':current_gw,'next_gw':next_gw,
                               'horizon':6,'sample_reliability':round(reliability,2),'schedule_load_source':schedule.get('source'),
                               'schedule_load_coverage':schedule.get('coverage',[]),'player_workload_source':'ESPN match summaries where available',
                               'defcon_model':{'version':1,'source':'official FPL bootstrap defensive_contribution_per_90','thresholds':{'DEF':10,'MID':12,'FWD':12},
                                               'method':'Poisson threshold probability; relative-to-position edge only to avoid double-counting PPG','position_baseline_expected_points_per_90':{k:round(v,3) for k,v in baselines.items()}},
                               'players':rows},indent=2,ensure_ascii=False)+'\n')
    observed=sum(1 for x in rows if x.get('player_workload_observed'))
    print(f'Wrote {OUT} with {len(rows)} players, reliability={reliability:.2f}, observed workloads={observed}, defcon=v1')
    try:
        from attacking_role import main as attacking_role_main
        attacking_role_main()
    except Exception as exc:
        print(f'Attacking-role enrichment skipped: {exc}')
    try:
        from post_window_review import main as post_window_review_main
        post_window_review_main()
    except Exception as exc:
        print(f'Post-window review skipped: {exc}')
if __name__=='__main__':main()
