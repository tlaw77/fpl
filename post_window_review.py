import json
from datetime import datetime, timezone
from pathlib import Path

CURRENT=Path('data/player_pool.json')
OUT=Path('data/post_window_review.json')
BASELINE_CANDIDATES=[
    Path('data/history/gw1/player_pool.json'),
    Path('data/history/gw2/player_pool.json'),
]


def load(path):
    return json.loads(path.read_text()) if path.exists() else None


def key(p):
    return int(p.get('player_id') or 0)


def compact(p):
    return {
        'player_id': key(p),
        'player': p.get('player'),
        'club': p.get('club'),
        'position': p.get('position'),
        'price': p.get('price'),
        'six_gw_score': p.get('six_gw_score'),
        'availability': p.get('adjusted_availability', p.get('availability')),
        'global_ownership_pct': p.get('global_ownership_pct'),
        'mini_league_ownership_pct': p.get('mini_league_ownership_pct'),
        'news': p.get('news') or '',
    }


def main():
    current=load(CURRENT)
    if not current:
        raise SystemExit('Missing current player pool')

    # Use the earliest archived in-season universe as the transfer-window baseline.
    baseline_path=next((p for p in BASELINE_CANDIDATES if p.exists()),None)
    baseline=load(baseline_path) if baseline_path else None
    if not baseline:
        OUT.write_text(json.dumps({
            'status':'WAITING_FOR_BASELINE','version':1,
            'generated_at_utc':datetime.now(timezone.utc).isoformat(),
            'message':'No archived player-pool baseline is available yet.'
        },indent=2)+'\n')
        return

    now={key(p):p for p in current.get('players',[]) if key(p)}
    old={key(p):p for p in baseline.get('players',[]) if key(p)}

    new_ids=sorted(set(now)-set(old))
    gone_ids=sorted(set(old)-set(now))
    common=set(now)&set(old)
    movers=[]
    for pid in common:
        a,b=old[pid],now[pid]
        if a.get('club')!=b.get('club'):
            movers.append({
                **compact(b),
                'from_club':a.get('club'),
                'to_club':b.get('club'),
                'change':'club_change'
            })

    new_options=[]
    for pid in new_ids:
        p=now[pid]
        uncertainty='HIGH'
        if float(p.get('adjusted_availability',p.get('availability')) or 0)>=.9 and not (p.get('news') or ''):
            uncertainty='MEDIUM'
        new_options.append({
            **compact(p),
            'change':'new_to_fpl_universe',
            'role_uncertainty':uncertainty,
            'review_note':'New option since the archived early-season player universe; require role/minutes evidence before treating projection confidence as established.'
        })
    new_options.sort(key=lambda x:float(x.get('six_gw_score') or -999),reverse=True)

    departures=[]
    for pid in gone_ids:
        p=old[pid]
        departures.append({**compact(p),'change':'left_current_player_universe'})

    # Structural role-pressure heuristic:
    # arrivals increase competition for same club/position; departures reduce it.
    arrival_buckets={}
    for x in new_options+movers:
        arrival_buckets.setdefault((x.get('club'),x.get('position')),[]).append(x)
    departure_buckets={}
    for x in departures:
        departure_buckets.setdefault((x.get('club'),x.get('position')),[]).append(x)
    for x in movers:
        departure_buckets.setdefault((x.get('from_club'),x.get('position')),[]).append({
            'player_id':x.get('player_id'),'player':x.get('player'),'club':x.get('from_club'),'position':x.get('position')
        })

    role_losers=[]; role_winners=[]
    for p in now.values():
        bucket=(p.get('club'),p.get('position'))
        arrivals=[x for x in arrival_buckets.get(bucket,[]) if int(x.get('player_id') or 0)!=key(p)]
        departures_here=[x for x in departure_buckets.get(bucket,[]) if int(x.get('player_id') or 0)!=key(p)]
        if arrivals:
            role_losers.append({
                **compact(p),'change':'competition_increased','pressure':'WATCH',
                'drivers':[x.get('player') for x in arrivals[:3]],
                'review_note':'Same-position competition increased. Monitor starts, minutes and role before downgrading projection materially.'
            })
        if departures_here:
            role_winners.append({
                **compact(p),'change':'competition_reduced','pressure':'POSITIVE_WATCH',
                'drivers':[x.get('player') for x in departures_here[:3]],
                'review_note':'Same-position competition reduced. Potential role winner, but confirm via actual selection/minutes.'
            })
    role_losers.sort(key=lambda x:float(x.get('six_gw_score') or -999),reverse=True)
    role_winners.sort(key=lambda x:float(x.get('six_gw_score') or -999),reverse=True)

    affected_clubs=sorted({x.get('club') for x in new_options if x.get('club')}|{x.get('from_club') for x in movers if x.get('from_club')}|{x.get('to_club') for x in movers if x.get('to_club')}|{x.get('club') for x in departures if x.get('club')})

    payload={
        'status':'SUCCESS','version':1,
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'baseline':{
            'path':str(baseline_path),'generated_at_utc':baseline.get('generated_at_utc'),
            'current_gw':baseline.get('current_gw'),'next_gw':baseline.get('next_gw')
        },
        'current':{
            'generated_at_utc':current.get('generated_at_utc'),'current_gw':current.get('current_gw'),'next_gw':current.get('next_gw')
        },
        'summary':{
            'new_options':len(new_options),'club_changes':len(movers),'departures_from_universe':len(departures),
            'role_winners':len(role_winners),'role_losers':len(role_losers),'affected_clubs':len(affected_clubs)
        },
        'affected_clubs':affected_clubs,
        'new_options':new_options[:30],
        'club_changes':sorted(movers,key=lambda x:float(x.get('six_gw_score') or -999),reverse=True),
        'departures':departures[:30],
        'role_winners':role_winners[:30],
        'role_losers':role_losers[:30],
        'method_note':'Compares the current official-FPL-derived Player Pool with the archived early-season Player Pool. Role winners/losers are structural same-position competition signals only; actual role confidence must be confirmed by starts, minutes, availability and team news.'
    }
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+'\n')
    print('Wrote',OUT,'summary=',payload['summary'])

if __name__=='__main__':
    main()
