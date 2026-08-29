import json
from datetime import datetime, timezone
from pathlib import Path

LATEST = Path('data/latest.json')
STRATEGY = Path('data/strategy.json')
OUT = Path('data/chip_window.json')


def f_easy(f):
    if not f:
        return 0.0
    return max(0.0, 6.0 - float(f.get('difficulty') or 3))


def fixture_for(player, gw):
    return next((f for f in (player.get('fixtures') or []) if f.get('gw') == gw), None)


def player_strength(p):
    return float(p.get('decision_score') or 0)


def evaluate():
    latest = json.loads(LATEST.read_text())
    strategy = json.loads(STRATEGY.read_text()) if STRATEGY.exists() else {}
    current_gw = int(latest.get('current_gw') or 1)
    next_gw = int(latest.get('next_gw') or min(38, current_gw + 1))
    rows = latest.get('current_squad_next5') or latest.get('squad_next5') or []
    me_strategy = strategy.get('me') or {}
    inventory = (me_strategy.get('inventory') or {})
    remaining = set(inventory.get('remaining_this_half') or [])
    schedule = {int(x['gw']): x for x in strategy.get('confirmed_blank_double_events', []) if x.get('gw')}
    gws = sorted({int(f['gw']) for p in rows for f in (p.get('fixtures') or []) if f.get('gw')})[:5]
    if not gws:
        gws = list(range(next_gw, min(39, next_gw + 5)))

    half = 1 if next_gw <= 19 else 2
    expiry_gw = 19 if half == 1 else 38
    window_start = 1 if half == 1 else 20
    remaining_count = len(remaining)
    gameweeks_left = max(0, expiry_gw - next_gw + 1)
    latest_safe_start_gw = max(window_start, expiry_gw - max(0, remaining_count - 1)) if remaining_count else None
    slack_gws = max(0, gameweeks_left - remaining_count)

    per_gw = {}
    for gw in gws:
        player_rows = []
        for p in rows:
            f = fixture_for(p, gw)
            player_rows.append({
                'player': p.get('player'), 'position': p.get('position'), 'starter_now': bool(p.get('starter')),
                'score': player_strength(p), 'fixture': f, 'ease': f_easy(f),
                'availability': float(p.get('availability') if p.get('availability') is not None else 1),
            })
        playable = [x for x in player_rows if x['fixture'] and x['availability'] >= .75]
        weak = [x for x in playable if x['ease'] <= 1]
        per_gw[gw] = {'players': player_rows, 'playable': playable, 'weak': weak}

    evaluations = []
    early_sample = current_gw < 4

    tc_windows = []
    for gw, ctx in per_gw.items():
        cands = [x for x in ctx['playable'] if x['position'] != 'GKP']
        best = max(cands, key=lambda x: x['score'] + x['ease'] * 2.2, default=None)
        sched = schedule.get(gw, {})
        double = bool(sched.get('double_teams'))
        score = (best['score'] + best['ease'] * 2.2 if best else 0) + (10 if double else 0)
        tc_windows.append({'gw': gw, 'score': round(score, 2), 'best_player': best['player'] if best else None,
                           'opponent': (best['fixture'] or {}).get('opponent') if best else None,
                           'venue': (best['fixture'] or {}).get('venue') if best else None,
                           'double_signal': double})
    best_tc = max(tc_windows, key=lambda x: x['score'], default=None)
    tc_now = next((x for x in tc_windows if x['gw'] == next_gw), None)
    tc_status = 'hold'
    if tc_now and best_tc:
        if tc_now['double_signal'] and tc_now['score'] >= best_tc['score'] - 1: tc_status = 'strong_window'
        elif not early_sample and tc_now['score'] >= best_tc['score'] - 1: tc_status = 'candidate_window'
        elif not early_sample and tc_now['score'] >= best_tc['score'] - 3: tc_status = 'watch'
    tc_reasons = []
    if tc_now and tc_now['best_player']: tc_reasons.append(f"Current single-fixture model leader: {tc_now['best_player']} vs {tc_now['opponent']} {tc_now['venue']}")
    if early_sample and not (tc_now and tc_now['double_signal']): tc_reasons.append('Early-season single-fixture form is too noisy to justify Triple Captain.')
    else: tc_reasons.append('A confirmed Double Gameweek materially raises Triple Captain value.' if not (tc_now and tc_now['double_signal']) else 'Current window includes a confirmed double signal.')
    tc_reasons.append(f"Best modeled window in the next five is GW{best_tc['gw']}" if best_tc else 'No future window available.')
    evaluations.append({'chip':'Triple Captain','available':'Triple Captain' in remaining,'status':tc_status,'current_window':tc_now,'best_window_next5':best_tc,'reasons':tc_reasons})

    bb_windows=[]
    for gw,ctx in per_gw.items():
        bench = [x for x in ctx['players'] if not x['starter_now']]
        bench_playable = [x for x in bench if x['fixture'] and x['availability'] >= .75]
        bench_score=sum(x['score']*.08 + x['ease']*1.8 for x in bench_playable)
        score=bench_score + len(ctx['playable'])*.7 + (6 if len(bench_playable)==4 else 0)
        bb_windows.append({'gw':gw,'score':round(score,2),'bench_playable':len(bench_playable),'bench_easy':sum(1 for x in bench_playable if x['ease']>=3),'all_playable':len(ctx['playable'])})
    best_bb=max(bb_windows,key=lambda x:x['score'],default=None)
    bb_now=next((x for x in bb_windows if x['gw']==next_gw),None)
    bb_status='hold'
    if bb_now and best_bb:
        is_best_now = bb_now['gw'] == best_bb['gw'] and bb_now['score'] >= best_bb['score'] - .5
        if bb_now['bench_playable']==4 and bb_now['bench_easy']>=3 and is_best_now and (current_gw>=3 or bool(schedule.get(next_gw,{}).get('double_teams'))): bb_status='strong_window'
        elif bb_now['bench_playable']==4 and bb_now['bench_easy']>=3 and is_best_now and not early_sample: bb_status='candidate_window'
        elif bb_now['bench_playable']==4 and bb_now['bench_easy']>=3 and is_best_now: bb_status='watch'
    evaluations.append({'chip':'Bench Boost','available':'Bench Boost' in remaining,'status':bb_status,'current_window':bb_now,'best_window_next5':best_bb,'reasons':[f"{bb_now['bench_playable']}/4 bench players have a playable fixture; {bb_now['bench_easy']} have an easy one." if bb_now else 'Bench window unavailable.',f"The stronger modeled bench window is GW{best_bb['gw']}." if best_bb and bb_now and best_bb['gw'] != bb_now['gw'] else 'Current week is close to the best bench window visible.','Bench Boost should exploit unusual bench strength, not simply avoid wasting playable substitutes.']})

    fh_windows=[]
    for gw,ctx in per_gw.items():
        sched=schedule.get(gw,{})
        blank_count=len(sched.get('blank_teams') or [])
        double_count=len(sched.get('double_teams') or [])
        missing=15-len(ctx['playable'])
        weak=len(ctx['weak'])
        score=missing*3.2 + weak*.7 + blank_count*.45 + double_count*.9
        fh_windows.append({'gw':gw,'score':round(score,2),'squad_players_without_playable_fixture':missing,'weak_fixture_count':weak,'blank_team_count':blank_count,'double_team_count':double_count})
    best_fh=max(fh_windows,key=lambda x:x['score'],default=None)
    fh_now=next((x for x in fh_windows if x['gw']==next_gw),None)
    fh_status='hold'
    if fh_now and best_fh:
        if fh_now['squad_players_without_playable_fixture']>=5 or fh_now['blank_team_count']>=6: fh_status='strong_window'
        elif fh_now['squad_players_without_playable_fixture']>=3 or fh_now['double_team_count']>=4: fh_status='candidate_window'
        elif not early_sample and fh_now['score']>=best_fh['score']-1 and fh_now['score']>=5: fh_status='watch'
    evaluations.append({'chip':'Free Hit','available':'Free Hit' in remaining,'status':fh_status,'current_window':fh_now,'best_window_next5':best_fh,'reasons':[f"Current squad has {fh_now['squad_players_without_playable_fixture']} players without a playable fixture and {fh_now['weak_fixture_count']} weak fixtures." if fh_now else 'Coverage unavailable.','Free Hit value rises sharply in a major blank or unusually concentrated double.',f"Best disruption window currently visible is GW{best_fh['gw']}" if best_fh else 'No disruption window available.']})

    availability_risks=sum(1 for p in rows if float(p.get('availability') if p.get('availability') is not None else 1)<.75)
    next3_bad=0; next3_good=0
    for p in rows:
        fs=(p.get('fixtures') or [])[:3]
        if fs:
            avg=sum(float(f.get('difficulty') or 3) for f in fs)/len(fs)
            if avg>=3.7: next3_bad+=1
            if avg<=2.3: next3_good+=1
    structural_score=availability_risks*4 + next3_bad*1.2 - next3_good*.5
    wc_status='hold'
    if current_gw>=4 and structural_score>=16: wc_status='strong_window'
    elif current_gw>=3 and structural_score>=11: wc_status='candidate_window'
    elif current_gw>=3 and structural_score>=7: wc_status='watch'
    evaluations.append({'chip':'Wildcard','available':'Wildcard' in remaining,'status':wc_status,'current_window':{'gw':next_gw,'score':round(structural_score,2),'weak_assets':availability_risks,'poor_next3':next3_bad,'good_next3':next3_good},'best_window_next5':None,'reasons':[f"Current structure has {availability_risks} genuine availability-risk assets and {next3_bad} players with a poor next-three fixture run.",f"{next3_good} squad players have a good next-three fixture run.",'Very early Wildcards carry a high information cost: waiting reveals roles, form and team strength unless the squad is genuinely broken.']})

    # Portfolio optimisation: a chip is judged against the value of preserving it for the rest of its half-season.
    # GW19/GW38 are hard expiries; only one chip can be played per GW.
    rank={'strong_window':4,'candidate_window':3,'watch':2,'hold':1}
    for e in evaluations:
        e['half_season'] = half
        e['expires_after_gw'] = expiry_gw
        e['gameweeks_left_in_set'] = gameweeks_left
        cur=e.get('current_window') or {}; best=e.get('best_window_next5') or cur
        cur_score=float(cur.get('score') or 0); best_score=float((best or {}).get('score') or 0)
        ratio=(cur_score/best_score) if best_score>0 else 0
        e['current_vs_best_visible_ratio']=round(ratio,3)
        e['preservation_value']='high' if slack_gws>=8 else ('medium' if slack_gws>=4 else 'low')
        if e['available'] and gameweeks_left <= remaining_count:
            # No spare slots remain: every unused chip now needs a distinct GW.
            if e['status']=='hold': e['status']='watch'
            e['reasons'].append('Chip-set expiry pressure is now critical: there are no spare Gameweeks left for all remaining chips.')
        elif e['available'] and gameweeks_left <= remaining_count + 2:
            if e['status']=='hold' and ratio >= .9: e['status']='watch'
            e['reasons'].append('Chip-set expiry pressure is rising; preserve only if a clearly better slot is expected before the deadline.')
        elif e['available'] and ratio >= .97 and gameweeks_left <= 8 and e['status']=='hold':
            e['status']='watch'
            e['reasons'].append('This window is close to the best currently visible and the remaining chip window is shortening.')

    available_evals=[e for e in evaluations if e['available']]
    best_action=max(available_evals,key=lambda e:(rank[e['status']], e.get('current_vs_best_visible_ratio',0)),default=None)
    overall=best_action['status'] if best_action else 'hold'

    # Collision-aware visible plan: one chip per GW, choose the strongest visible candidate slot for each chip.
    proposed=[]; occupied=set()
    def candidate_score(e):
        b=e.get('best_window_next5') or e.get('current_window') or {}
        return float(b.get('score') or 0)
    for e in sorted(available_evals,key=lambda x:(rank[x['status']],candidate_score(x)),reverse=True):
        b=e.get('best_window_next5') or e.get('current_window') or {}
        preferred=int(b.get('gw') or next_gw)
        options=[g for g in gws if g not in occupied]
        chosen=preferred if preferred in options else (min(options,key=lambda g:abs(g-preferred)) if options else None)
        if chosen is not None:
            occupied.add(chosen)
            proposed.append({'chip':e['chip'],'preferred_gw':preferred,'provisional_gw':chosen,'status':e['status'],'visible_score':round(candidate_score(e),2)})

    pressure = 'critical' if gameweeks_left <= remaining_count else ('tight' if gameweeks_left <= remaining_count + 2 else ('watch' if gameweeks_left <= remaining_count + 5 else 'comfortable'))
    portfolio={
        'half':half,
        'window':f'GW{window_start}-GW{expiry_gw}',
        'expires_after_gw':expiry_gw,
        'remaining_chips':sorted(remaining),
        'remaining_count':remaining_count,
        'gameweeks_left':gameweeks_left,
        'slack_gameweeks':slack_gws,
        'latest_safe_start_gw':latest_safe_start_gw,
        'pressure':pressure,
        'hard_inflection_explanation':f'With {remaining_count} unused chip(s), GW{latest_safe_start_gw} is the latest point at which all can still be deployed in separate Gameweeks before GW{expiry_gw}.' if remaining_count else 'No chips remain in this half.',
        'provisional_visible_plan':proposed,
        'rules':['One chip per Gameweek.','Unused first-half chips expire after GW19 and do not carry into the second half.','A fresh set of all four chips is available in the second half.','If the first Free Hit is used in GW19, the second-half Free Hit cannot be used in GW20 because Free Hits cannot be consecutive.'],
        'optimisation_principle':'Maximise total incremental chip value across the half-season, not the isolated score of the next Gameweek. Preserve a chip only while its expected future option value exceeds the current window and there is enough calendar slack to use every remaining chip.'
    }

    summary={
        'status':overall,
        'headline':'Preserve chips' if overall=='hold' else ('Monitor, but no urgent chip use' if overall=='watch' else f"{best_action['chip']} has a credible current case"),
        'best_current_chip':best_action['chip'] if best_action else None,
        'next_confirmed_pivot':min((x['gw'] for x in strategy.get('confirmed_blank_double_events',[]) if x.get('gw')),default=None),
        'principle':portfolio['optimisation_principle'],
        'chip_set_pressure':pressure,
        'latest_safe_start_gw':latest_safe_start_gw,
        'expires_after_gw':expiry_gw
    }
    return {'status':'SUCCESS','generated_at_utc':datetime.now(timezone.utc).isoformat(),'current_gw':current_gw,'next_gw':next_gw,'summary':summary,'portfolio':portfolio,'evaluations':evaluations,'method_note':'Half-season portfolio decision support. It combines current squad availability, visible fixtures, confirmed blank/double assignments, individual chip heuristics, hard chip-set expiry, one-chip-per-GW scheduling constraints, and the option value of waiting. Visible fixture scores are not directly comparable between chip types; they are used to rank windows within each chip, while status and calendar pressure govern cross-chip prioritisation.'}


if __name__=='__main__':
    OUT.parent.mkdir(parents=True,exist_ok=True)
    result=evaluate()
    OUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':result['status'],'summary':result['summary'],'portfolio':result['portfolio']}))
