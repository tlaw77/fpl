import json, urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

BASE='https://fantasy.premierleague.com/api'
LATEST=Path('data/latest.json'); OUT=Path('data/player_pool.json')

def get(url):
    req=urllib.request.Request(url,headers={'User-Agent':'fpl-player-pool/1.1'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)

def main():
    b=get(f'{BASE}/bootstrap-static/'); fixtures=get(f'{BASE}/fixtures/')
    latest=json.loads(LATEST.read_text())
    current_gw=int(latest.get('current_gw') or 1); next_gw=int(latest.get('next_gw') or current_gw+1)
    reliability=min(1.0,max(.20,current_gw/5.0))
    teams={t['id']:t['name'] for t in b['teams']}; pos={x['id']:x['singular_name_short'] for x in b['element_types']}
    fx=defaultdict(list)
    for f in fixtures:
        gw=f.get('event')
        if gw is None or gw<next_gw or gw>=next_gw+6:continue
        for tid,oid,venue,key in [(f['team_h'],f['team_a'],'H','team_h_difficulty'),(f['team_a'],f['team_h'],'A','team_a_difficulty')]:
            fx[tid].append({'gw':gw,'opponent':teams.get(oid,''),'venue':venue,'difficulty':f.get(key) or 3})
    for v in fx.values():v.sort(key=lambda x:x['gw'])
    exposure={x.get('player_id'):x for x in latest.get('player_exposure',[])}
    mine={x.get('player_id') for x in (latest.get('current_squad_next5') or latest.get('squad_next5') or [])}
    rows=[]
    for p in b['elements']:
        if p.get('status')=='u':continue
        fs=fx.get(p['team'],[])[:6]
        if not fs:continue
        diffs=[float(f['difficulty']) for f in fs]; ease=6-(sum(diffs)/len(diffs))
        avail=(p.get('chance_of_playing_next_round') if p.get('chance_of_playing_next_round') is not None else 100)/100
        form=float(p.get('form') or 0); ppg=float(p.get('points_per_game') or 0); global_own=float(p.get('selected_by_percent') or 0)
        mini=float((exposure.get(p['id']) or {}).get('ownership_pct') or 0); eo=float((exposure.get(p['id']) or {}).get('effective_ownership_pct') or mini)
        observed=(min(form,12)*1.15+min(ppg,12)*.95)*reliability
        score=round(observed+ease*2.15+avail*1.8+global_own*.045+mini*.018,2)
        role='Shield' if eo>=75 else ('Neutral' if eo>=40 else 'Leverage')
        rows.append({'player_id':p['id'],'player':p['web_name'],'club':teams[p['team']],'position':pos[p['element_type']],'price':p['now_cost']/10,'availability':avail,'global_ownership_pct':global_own,'mini_league_ownership_pct':mini,'effective_ownership_pct':eo,'role':role,'form':form,'points_per_game':ppg,'fixtures':fs,'fixture_ease_6':round(ease,2),'six_gw_score':score,'sample_reliability':round(reliability,2),'in_public_squad':p['id'] in mine,'news':p.get('news') or ''})
    rows.sort(key=lambda x:x['six_gw_score'],reverse=True)
    OUT.write_text(json.dumps({'status':'SUCCESS','generated_at_utc':datetime.now(timezone.utc).isoformat(),'current_gw':current_gw,'next_gw':next_gw,'horizon':6,'sample_reliability':round(reliability,2),'players':rows},indent=2,ensure_ascii=False)+'\n')
    print(f'Wrote {OUT} with {len(rows)} players, reliability={reliability:.2f}')
if __name__=='__main__':main()
