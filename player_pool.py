import json, urllib.request
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

def f(v,d=0.0):
    try:return float(v)
    except Exception:return d

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
    # Rested/unused players should not inherit the full club congestion penalty.
    mod=1.0-(1.0-base_mod)*participation
    if away and mins>=60:mod-=.015
    return max(.78,min(1.0,mod))

def workload_band(minutes):
    if minutes is None:return 'Unknown'
    if minutes>=80:return 'Heavy'
    if minutes>=55:return 'Moderate'
    if minutes>=25:return 'Light'
    return 'Rested / cameo'

def expected_minutes_signal(p,current_gw,reliability,position):
    """Conservative free xMins estimate from official FPL starts/minutes.

    It is intentionally shrunk hard in opening GWs. The aim is not to claim
    lineup certainty; it provides a separate rotation/minutes signal that the
    projection model can combine with availability, Scout and schedule load.
    """
    priors={'GKP':82.0,'DEF':70.0,'MID':68.0,'FWD':67.0}
    prior=priors.get(position,68.0)
    games=max(1,int(current_gw or 1))
    starts=max(0.0,f(p.get('starts')))
    minutes=max(0.0,f(p.get('minutes')))
    mpg=min(90.0,minutes/games)
    start_rate=min(1.0,starts/games)
    # Current-season evidence is useful but deliberately cannot dominate early.
    evidence=min(.78,max(.12,reliability*.72))
    observed=mpg
    if starts>0:
        observed=max(observed,min(86.0,(minutes/max(starts,1))*start_rate))
    xmins=prior*(1-evidence)+observed*evidence
    return round(max(8.0,min(88.0,xmins)),1),round(start_rate,3)

def main():
    b=get(f'{BASE}/bootstrap-static/'); fixtures=get(f'{BASE}/fixtures/')
    latest=json.loads(LATEST.read_text())
    schedule=json.loads(SCHEDULE.read_text()) if SCHEDULE.exists() else {'clubs':{},'players':{}}
    current_gw=int(latest.get('current_gw') or 1); next_gw=int(latest.get('next_gw') or current_gw+1)
    reliability=min(1.0,max(.20,current_gw/5.0))
    teams={t['id']:t['name'] for t in b['teams']}; pos={x['id']:x['singular_name_short'] for x in b['element_types']}
    team_signals={t['id']:{
        'strength_overall_home':f(t.get('strength_overall_home')),
        'strength_overall_away':f(t.get('strength_overall_away')),
        'strength_attack_home':f(t.get('strength_attack_home')),
        'strength_attack_away':f(t.get('strength_attack_away')),
        'strength_defence_home':f(t.get('strength_defence_home')),
        'strength_defence_away':f(t.get('strength_defence_away')),
    } for t in b['teams']}
    fx=defaultdict(list)
    for fixture in fixtures:
        gw=fixture.get('event')
        if gw is None or gw<next_gw or gw>=next_gw+6:continue
        for tid,oid,venue,key in [(fixture['team_h'],fixture['team_a'],'H','team_h_difficulty'),(fixture['team_a'],fixture['team_h'],'A','team_a_difficulty')]:
            fx[tid].append({'gw':gw,'opponent':teams.get(oid,''),'venue':venue,'difficulty':fixture.get(key) or 3,'kickoff_time':fixture.get('kickoff_time'),
                            'opponent_team_id':oid,'opponent_strength':team_signals.get(oid,{})})
    for v in fx.values():v.sort(key=lambda x:(x['gw'],x.get('kickoff_time') or ''))
    exposure={x.get('player_id'):x for x in latest.get('player_exposure',[])}
    mine={x.get('player_id') for x in (latest.get('current_squad_next5') or latest.get('squad_next5') or [])}
    player_load=(schedule.get('players') or {})
    rows=[]
    for p in b['elements']:
        if p.get('status')=='u':continue
        fs=fx.get(p['team'],[])[:6]
        if not fs:continue
        club=teams[p['team']]; position=pos[p['element_type']]
        extras=(schedule.get('clubs') or {}).get(club,[])
        diffs=[float(x['difficulty']) for x in fs]; ease=6-(sum(diffs)/len(diffs))
        avail=(p.get('chance_of_playing_next_round') if p.get('chance_of_playing_next_round') is not None else 100)/100
        form=f(p.get('form')); ppg=f(p.get('points_per_game')); global_own=f(p.get('selected_by_percent'))
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

        xmins,start_rate=expected_minutes_signal(p,current_gw,reliability,position)
        xg=f(p.get('expected_goals')); xa=f(p.get('expected_assists')); xgi=f(p.get('expected_goal_involvements'),xg+xa)
        xg90=f(p.get('expected_goals_per_90')); xa90=f(p.get('expected_assists_per_90'))
        xgi90=f(p.get('expected_goal_involvements_per_90'),xg90+xa90)
        ep_next=f(p.get('ep_next'))
        # Underlying contribution is intentionally small and maturity-weighted.
        pos_xgi_prior={'GKP':.01,'DEF':.10,'MID':.30,'FWD':.42}.get(position,.25)
        underlying_edge=max(-.20,min(.35,xgi90-pos_xgi_prior))
        underlying_bonus=underlying_edge*2.4*reliability
        minutes_bonus=((xmins-68.0)/20.0)*.55*reliability

        observed=(min(form,12)*1.15+min(ppg,12)*.95)*reliability
        score=round(observed+ease*2.15+adjusted_avail*1.8+global_own*.045+mini*.018-congestion_penalty+underlying_bonus+minutes_bonus,2)
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
        rows.append({'player_id':p['id'],'player':p['web_name'],'club':club,'position':position,'price':p['now_cost']/10,
                     'availability':avail,'adjusted_availability':round(adjusted_avail,3),'schedule_modifier':round(player_sched_mod,3),
                     'club_schedule_modifier':round(club_sched_mod,3),'schedule_risk':schedule_risk,'schedule_note':schedule_note,
                     'extra_club_fixtures_6gw':len(horizon_extra),'days_rest_before_next_pl':round(rest_days,1) if rest_days is not None else None,
                     'midweek_minutes':round(float(midweek_minutes),1) if midweek_minutes is not None else None,
                     'midweek_started':midweek_started,'midweek_away':midweek_away if closest_app else None,
                     'midweek_workload':workload_band(midweek_minutes),'recent_non_pl_minutes':round(recent_minutes,1),
                     'player_workload_observed':midweek_minutes is not None,
                     'expected_minutes':xmins,'observed_start_rate':start_rate,'season_starts':int(f(p.get('starts'))),'season_minutes':int(f(p.get('minutes'))),
                     'expected_goals':round(xg,3),'expected_assists':round(xa,3),'expected_goal_involvements':round(xgi,3),
                     'expected_goals_per_90':round(xg90,3),'expected_assists_per_90':round(xa90,3),'expected_goal_involvements_per_90':round(xgi90,3),
                     'official_ep_next':round(ep_next,2),'team_strength':team_signals.get(p['team'],{}),
                     'global_ownership_pct':global_own,'mini_league_ownership_pct':mini,'effective_ownership_pct':eo,'role':role,
                     'form':form,'points_per_game':ppg,'fixtures':fs,'fixture_ease_6':round(ease,2),'six_gw_score':score,
                     'sample_reliability':round(reliability,2),'in_public_squad':p['id'] in mine,'news':p.get('news') or ''})
    rows.sort(key=lambda x:x['six_gw_score'],reverse=True)
    OUT.write_text(json.dumps({'status':'SUCCESS','generated_at_utc':datetime.now(timezone.utc).isoformat(),'current_gw':current_gw,'next_gw':next_gw,
                               'horizon':6,'sample_reliability':round(reliability,2),'schedule_load_source':schedule.get('source'),
                               'schedule_load_coverage':schedule.get('coverage',[]),'player_workload_source':'ESPN match summaries where available',
                               'public_signal_sources':['Official FPL bootstrap expected stats','Official FPL starts/minutes','Official FPL team strength'],
                               'players':rows},indent=2,ensure_ascii=False)+'\n')
    observed=sum(1 for x in rows if x.get('player_workload_observed'))
    print(f'Wrote {OUT} with {len(rows)} players, reliability={reliability:.2f}, observed workloads={observed}')
if __name__=='__main__':main()
