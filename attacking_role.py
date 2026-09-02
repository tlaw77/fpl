import json, math, statistics, urllib.request
from pathlib import Path
from datetime import datetime, timezone

BASE='https://fantasy.premierleague.com/api/bootstrap-static/'
POOL=Path('data/player_pool.json')

def get_json(url):
    req=urllib.request.Request(url,headers={'User-Agent':'fpl-attacking-role/1.0'})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.load(r)

def n(v,d=0.0):
    try:
        x=float(v)
        return x if math.isfinite(x) else d
    except Exception:
        return d

def per90(total,minutes):
    m=max(0.0,n(minutes))
    return 0.0 if m<=0 else n(total)*90.0/m

def confidence(minutes):
    m=n(minutes)
    if m>=540:return .95
    if m>=360:return .85
    if m>=180:return .68
    if m>=90:return .48
    if m>0:return .28
    return .12

def def_role_score(xgi90,threat90,creativity90):
    # Relative attacking-role proxy for FPL defenders. Deliberately bounded.
    a=min(1.0,max(0.0,xgi90/.45))
    t=min(1.0,max(0.0,threat90/36.0))
    c=min(1.0,max(0.0,creativity90/28.0))
    return .55*a+.25*t+.20*c

def mid_forward_score(xg90,threat90,xa90):
    # Secondary OOP proxy: midfielders whose output resembles a forward role.
    g=min(1.0,max(0.0,xg90/.55))
    t=min(1.0,max(0.0,threat90/45.0))
    a=min(1.0,max(0.0,xa90/.35))
    return .55*g+.30*t+.15*a

def label(position,score,conf):
    if conf<.35:return 'LOW SAMPLE'
    if position=='DEF':
        if score>=.72:return 'ADVANCED DEFENDER'
        if score>=.52:return 'ATTACKING ROLE WATCH'
    if position=='MID':
        if score>=.76:return 'FORWARD-ROLE CANDIDATE'
        if score>=.58:return 'ADVANCED MID WATCH'
    return 'STANDARD ROLE'

def main():
    if not POOL.exists():
        raise FileNotFoundError(POOL)
    pool=json.loads(POOL.read_text())
    boot=get_json(BASE)
    official={int(p['id']):p for p in boot.get('elements',[])}

    role_values={'DEF':[],'MID':[]}
    for row in pool.get('players',[]):
        p=official.get(int(row.get('player_id') or 0))
        if not p:continue
        mins=n(p.get('minutes'))
        xg90=per90(p.get('expected_goals'),mins)
        xa90=per90(p.get('expected_assists'),mins)
        xgi90=xg90+xa90
        threat90=per90(p.get('threat'),mins)
        creativity90=per90(p.get('creativity'),mins)
        pos=row.get('position')
        score=def_role_score(xgi90,threat90,creativity90) if pos=='DEF' else (mid_forward_score(xg90,threat90,xa90) if pos=='MID' else 0.0)
        conf=confidence(mins)*max(.25,n(row.get('sample_reliability'),.25))
        row.update({
            'attacking_role_source':'official_fpl_proxy',
            'attacking_role_score':round(score,3),
            'attacking_role_confidence':round(conf,3),
            'attacking_role_label':label(pos,score,conf),
            'expected_goals_per90_proxy':round(xg90,3),
            'expected_assists_per90_proxy':round(xa90,3),
            'expected_goal_involvements_per90_proxy':round(xgi90,3),
            'threat_per90_proxy':round(threat90,2),
            'creativity_per90_proxy':round(creativity90,2),
            'role_sample_minutes':round(mins,1),
        })
        if pos in role_values and mins>=45:
            role_values[pos].append(score)

    baselines={k:(statistics.median(v) if v else 0.0) for k,v in role_values.items()}
    for row in pool.get('players',[]):
        pos=row.get('position')
        if pos not in baselines:continue
        score=n(row.get('attacking_role_score'))
        edge=score-baselines[pos]
        conf=n(row.get('attacking_role_confidence'))
        row['attacking_role_position_baseline']=round(baselines[pos],3)
        row['attacking_role_edge']=round(edge,3)
        # Conservative ranking effect. six_gw_score already contains form/PPG, so only
        # the relative role edge is added and heavily confidence-shrunk.
        raw=max(-.35,min(.55,edge*.85))*conf
        row['attacking_role_rank_adjustment']=round(raw,3)
        row['six_gw_score']=round(n(row.get('six_gw_score'))+raw,2)

    pool['attacking_role_model']={
        'version':1,
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'source':'official FPL expected goals/assists, threat, creativity and minutes',
        'method':'position-relative attacking-role proxy; not a true average-position or heatmap feed',
        'defender_baseline':round(baselines.get('DEF',0),3),
        'midfielder_baseline':round(baselines.get('MID',0),3),
        'confidence_note':'Small samples are strongly down-weighted. ADVANCED labels are candidates, not confirmed tactical positions.'
    }
    pool['players'].sort(key=lambda x:n(x.get('six_gw_score')),reverse=True)
    POOL.write_text(json.dumps(pool,indent=2,ensure_ascii=False)+'\n')
    flagged=[x for x in pool.get('players',[]) if x.get('attacking_role_label') in ('ADVANCED DEFENDER','FORWARD-ROLE CANDIDATE')]
    print(f'Attacking-role enrichment complete: {len(flagged)} high-signal candidates')

if __name__=='__main__':main()
