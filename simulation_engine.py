import json
import math
import random
import statistics
from datetime import datetime, timezone
from pathlib import Path

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
OUT = Path('data/simulation.json')

ITERATIONS = 3000
MAX_TRANSFER_ROUTES = 10
HORIZON = 6


def n(v, d=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else d
    except Exception:
        return d


def norm(s):
    return str(s or '').strip().lower()


def percentile(vals, p):
    if not vals:
        return 0.0
    xs = sorted(vals)
    k = (len(xs)-1) * p
    a, b = math.floor(k), math.ceil(k)
    if a == b:
        return xs[a]
    return xs[a] * (b-k) + xs[b] * (k-a)


def load_json(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def player_maps(pool):
    rows = pool.get('players') or []
    return {int(p['player_id']): p for p in rows if p.get('player_id')}, {norm(p.get('player')): p for p in rows}


def enrich(raw, by_id, by_name):
    if not raw:
        return None
    pid = int(raw.get('player_id') or 0)
    p = by_id.get(pid) or by_name.get(norm(raw.get('player')))
    if p:
        z = dict(p)
        z.update({k: v for k, v in raw.items() if v is not None})
        return z
    return dict(raw)


def fixture(p, gw):
    return next((f for f in (p.get('fixtures') or []) if int(f.get('gw') or -1) == int(gw)), None)


def scout_lookup(scout):
    by_id, by_name = {}, {}
    for p in scout.get('players') or []:
        if p.get('player_id'):
            by_id[int(p['player_id'])] = p
        by_name[norm(p.get('player'))] = p
    return by_id, by_name


def market_lookup(market):
    by_id, by_name = {}, {}
    rows = (market.get('urgent_relevant') or []) + (market.get('my_squad_and_targets') or [])
    for p in rows:
        if p.get('player_id'):
            by_id[int(p['player_id'])] = p
        by_name[norm(p.get('player'))] = p
    return by_id, by_name


def expected_gw(p, gw, model_lo, model_hi, scout_maps, market_maps):
    f = fixture(p, gw)
    if not f:
        return 0.0, 0.0
    pos_base = {'GKP': 3.1, 'DEF': 3.3, 'MID': 3.7, 'FWD': 3.9}.get(p.get('position'), 3.5)
    reliability = min(.55, max(.10, n(p.get('sample_reliability'), .35)))
    ppg = max(0.0, min(12.0, n(p.get('points_per_game'), pos_base)))
    base = pos_base * (1-reliability) + ppg * reliability

    model = n(p.get('six_gw_score'), model_lo)
    model_pct = .5 if model_hi <= model_lo else max(0.0, min(1.0, (model-model_lo)/(model_hi-model_lo)))
    model_factor = .86 + model_pct * .28

    diff = n(f.get('difficulty'), 3)
    fixture_factor = max(.68, min(1.34, 1 + (3-diff)*.115 + (.045 if f.get('venue') == 'H' else 0)))
    avail = max(0.0, min(1.0, n(p.get('adjusted_availability', p.get('availability')), 1)))
    sched = max(.75, min(1.05, n(p.get('schedule_modifier'), 1)))

    sid, sname = scout_maps
    s = sid.get(int(p.get('player_id') or 0)) or sname.get(norm(p.get('player'))) or {}
    merit = norm(s.get('merit'))
    scout_factor = 1.0
    if any(x in merit for x in ('strong', 'reinforces', 'worth investigating')):
        scout_factor += .035
    if any(x in merit for x in ('avoid', 'concern', 'sell')):
        scout_factor -= .055

    mean = base * model_factor * fixture_factor * avail * sched * scout_factor

    # Uncertainty is deliberately higher while the season sample is immature.
    cv = .78 - reliability*.22
    if norm(p.get('schedule_risk')) == 'high':
        cv += .12
    elif norm(p.get('schedule_risk')) == 'medium':
        cv += .05
    if not p.get('player_workload_observed', False):
        cv += .04
    mid, mname = market_maps
    m = mid.get(int(p.get('player_id') or 0)) or mname.get(norm(p.get('player'))) or {}
    if 'strong_' in norm(m.get('market_status')):
        cv += .025
    return max(0.0, mean), max(.35, min(1.15, cv))


def sample_points(rng, mean, cv):
    if mean <= 0:
        return 0.0
    shape = max(.65, 1/(cv*cv))
    scale = mean/shape
    return rng.gammavariate(shape, scale)


def valid_club_limit(squad):
    counts = {}
    for p in squad:
        key = p.get('team_id') or p.get('club')
        counts[key] = counts.get(key, 0) + 1
    return max(counts.values(), default=0) <= 3


def formations():
    out = []
    for d in range(3, 6):
        for m in range(2, 6):
            for f in range(1, 4):
                if d+m+f == 10:
                    out.append((d,m,f))
    return out


def best_xi(squad, exp_by_id):
    pos = {k: [] for k in ('GKP','DEF','MID','FWD')}
    for p in squad:
        pos.setdefault(p.get('position'), []).append(p)
    if not pos['GKP']:
        return [], None
    gk = max(pos['GKP'], key=lambda p: exp_by_id.get(int(p.get('player_id') or 0), 0))
    best, best_score = [], -1
    for d,m,f in formations():
        if len(pos['DEF']) < d or len(pos['MID']) < m or len(pos['FWD']) < f:
            continue
        xi = [gk]
        for k, take in (('DEF',d),('MID',m),('FWD',f)):
            xi += sorted(pos[k], key=lambda p: exp_by_id.get(int(p.get('player_id') or 0), 0), reverse=True)[:take]
        score = sum(exp_by_id.get(int(p.get('player_id') or 0),0) for p in xi)
        if score > best_score:
            best, best_score = xi, score
    cap = max(best, key=lambda p: exp_by_id.get(int(p.get('player_id') or 0), 0), default=None)
    return best, cap


def apply_move(squad, move, by_id, by_name):
    if not move:
        return list(squad)
    out = move.get('out') or {}
    inc = move.get('safe_in') or move.get('in') or move.get('aggressive_in') or {}
    out_id = int(out.get('player_id') or 0)
    out_name = norm(out.get('player'))
    new = []
    removed = False
    for p in squad:
        if not removed and ((out_id and int(p.get('player_id') or 0) == out_id) or (out_name and norm(p.get('player')) == out_name)):
            removed = True
            continue
        new.append(p)
    incoming = enrich(inc, by_id, by_name)
    if not removed or not incoming:
        return None
    new.append(incoming)
    if len(new) != 15 or not valid_club_limit(new):
        return None
    return new


def candidate_routes(latest, base_squad, by_id, by_name):
    rows = (latest.get('current_next_gw_decisions') or {}).get('safe_moves') or []
    candidates = [{'key':'ROLL','label':'Roll / no transfer','move':None,'squad':list(base_squad)}]
    seen = set()
    for m in rows[:MAX_TRANSFER_ROUTES*2]:
        out = m.get('out') or {}; inc = m.get('safe_in') or m.get('in') or {}
        label = f"{out.get('player','—')} → {inc.get('player','—')}"
        if label in seen:
            continue
        sq = apply_move(base_squad, m, by_id, by_name)
        if not sq:
            continue
        seen.add(label)
        candidates.append({'key':label,'label':label,'move':m,'squad':sq})
        if len(candidates) >= MAX_TRANSFER_ROUTES+1:
            break
    return candidates


def rival_squads(latest, by_id, by_name):
    out = []
    for r in latest.get('rivals') or []:
        picks = r.get('picks') or r.get('squad') or []
        sq = [enrich(p, by_id, by_name) for p in picks]
        sq = [p for p in sq if p]
        if len(sq) >= 11:
            out.append({'entry_id': r.get('entry_id'), 'team_name': r.get('team_name'), 'manager': r.get('manager'),
                        'rank': r.get('rank'), 'total_points': n(r.get('total_points')), 'squad': sq[:15]})
    return out


def run():
    latest = load_json(LATEST,{})
    pool = load_json(POOL,{})
    scout = load_json(SCOUT,{})
    market = load_json(MARKET,{})
    by_id, by_name = player_maps(pool)
    scout_maps, market_maps = scout_lookup(scout), market_lookup(market)
    base_raw = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    base_squad = [enrich(p,by_id,by_name) for p in base_raw]
    base_squad = [p for p in base_squad if p]
    rivals = rival_squads(latest, by_id, by_name)
    candidates = candidate_routes(latest, base_squad, by_id, by_name)
    next_gw = int(latest.get('next_gw') or 1)
    gws = list(range(next_gw, min(39,next_gw+HORIZON)))

    pool_models = [n(p.get('six_gw_score')) for p in pool.get('players') or []]
    model_lo, model_hi = percentile(pool_models,.10), percentile(pool_models,.90)

    # Universe and expected-point table.
    universe = {}
    for c in candidates:
        for p in c['squad']:
            universe[int(p.get('player_id') or 0)] = p
    for r in rivals:
        for p in r['squad']:
            universe[int(p.get('player_id') or 0)] = p
    universe.pop(0,None)

    exp = {}
    for gw in gws:
        exp[gw] = {}
        for pid,p in universe.items():
            exp[gw][pid] = expected_gw(p,gw,model_lo,model_hi,scout_maps,market_maps)

    # Precompute rational XI/captain choices by route and rival for each GW.
    cand_lineups = {}
    for c in candidates:
        cand_lineups[c['key']] = {}
        for gw in gws:
            ex = {pid:v[0] for pid,v in exp[gw].items()}
            xi,cap = best_xi(c['squad'],ex)
            cand_lineups[c['key']][gw] = ([int(p.get('player_id') or 0) for p in xi], int(cap.get('player_id') or 0) if cap else 0)
    rival_lineups = []
    for r in rivals:
        bygw = {}
        for gw in gws:
            ex = {pid:v[0] for pid,v in exp[gw].items()}
            xi,cap = best_xi(r['squad'],ex)
            bygw[gw] = ([int(p.get('player_id') or 0) for p in xi], int(cap.get('player_id') or 0) if cap else 0)
        rival_lineups.append(bygw)

    seed = str(latest.get('generated_at_utc') or '') + '|simulation-v1'
    rng = random.Random(seed)
    me_start = n((latest.get('me') or {}).get('total_points'))
    route_totals = {c['key']: [] for c in candidates}
    route_ranks = {c['key']: [] for c in candidates}
    route_gain_places = {c['key']: 0 for c in candidates}
    route_beat = {c['key']: [0]*len(rivals) for c in candidates}
    current_rank = int((latest.get('me') or {}).get('rank') or (len(rivals)+1))

    for _ in range(ITERATIONS):
        outcomes = {}
        for gw in gws:
            outcomes[gw] = {pid: sample_points(rng,*params) for pid,params in exp[gw].items()}

        rival_scores=[]
        for idx,r in enumerate(rivals):
            total=r['total_points']
            for gw in gws:
                xi,cap=rival_lineups[idx][gw]
                total += sum(outcomes[gw].get(pid,0) for pid in xi) + outcomes[gw].get(cap,0)
            rival_scores.append(total)

        for c in candidates:
            total=me_start
            for gw in gws:
                xi,cap=cand_lineups[c['key']][gw]
                total += sum(outcomes[gw].get(pid,0) for pid in xi) + outcomes[gw].get(cap,0)
            route_totals[c['key']].append(total-me_start)
            rank=1+sum(1 for x in rival_scores if x>total)
            route_ranks[c['key']].append(rank)
            if rank < current_rank:
                route_gain_places[c['key']] += 1
            for i,rv in enumerate(rival_scores):
                if total > rv:
                    route_beat[c['key']][i]+=1

    results=[]
    for c in candidates:
        vals=route_totals[c['key']]; ranks=route_ranks[c['key']]
        p10=percentile(vals,.10); p90=percentile(vals,.90)
        mean=statistics.fmean(vals) if vals else 0
        exp_rank=statistics.fmean(ranks) if ranks else current_rank
        beat_probs=[round(route_beat[c['key']][i]/ITERATIONS,3) for i in range(len(rivals))]
        # Utility rewards points and rank improvement, mildly penalising downside dispersion.
        utility = mean + (current_rank-exp_rank)*5.0 - max(0,mean-p10)*.12
        results.append({
            'route': c['label'], 'action':'ROLL' if c['move'] is None else 'TRANSFER',
            'expected_points_6gw': round(mean,2), 'p10_points_6gw':round(p10,2), 'p90_points_6gw':round(p90,2),
            'expected_rank_after_horizon':round(exp_rank,2),
            'prob_gain_league_place':round(route_gain_places[c['key']]/ITERATIONS,3),
            'prob_finish_ahead_each_rival': beat_probs,
            'utility_score':round(utility,3),
            'incoming_starts_gw3': bool((c.get('move') or {}).get('safe_incoming_starts')) if c.get('move') else None,
        })
    results.sort(key=lambda x:x['utility_score'], reverse=True)

    rival_meta=[{'entry_id':r['entry_id'],'team_name':r['team_name'],'manager':r['manager'],'rank':r['rank'],'total_points':r['total_points']} for r in rivals]
    winner=results[0] if results else None
    output={
        'status':'SUCCESS','generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'engine_version':1,'iterations':ITERATIONS,'horizon_gws':gws,
        'shared_outcome_simulation':True,'candidate_count':len(results),'rivals':rival_meta,
        'recommendation':winner,
        'routes':results,
        'method_note':'Monte Carlo decision support. Shared player outcomes are used across your team and rivals; each squad is re-optimised for legal XI and captain each GW. Inputs include fixture difficulty, model strength, availability, schedule/workload risk, Scout evidence and market uncertainty. Early-season outputs are comparative simulations, not guaranteed FPL point forecasts.'
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':'SUCCESS','winner':winner,'iterations':ITERATIONS}))


if __name__=='__main__':
    run()
