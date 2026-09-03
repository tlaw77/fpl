import json
from datetime import datetime, timezone
from pathlib import Path

import captaincy_model as cm
import simulation_engine as s
from projection_calibration import expected_gw as calibrated_expected_gw, season_maturity

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
MARKET = Path('data/market.json')
OUT = Path('data/captaincy_review.json')


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def pid(x):
    return int(x.get('player_id') or x.get('id') or 0)


def first_fixture(p):
    rows = p.get('fixtures') or []
    return rows[0] if rows else {}


def reasons(p, mean, cv, fixture, edge=None):
    out = []
    opp = (fixture or {}).get('opponent') or 'opponent'
    venue = str((fixture or {}).get('venue') or '').upper()
    fdr = s.n((fixture or {}).get('difficulty'), 3)
    if venue == 'H' and fdr <= 2:
        out.append(f'High-ceiling home fixture vs {opp} (FDR {int(fdr)}).')
    elif fdr <= 2:
        out.append(f'Favourable fixture vs {opp} (FDR {int(fdr)}).')
    if s.n(p.get('price')) >= 10:
        out.append('Premium asset with a stronger captaincy ceiling than a normal XI pick.')
    if s.n(p.get('form')) > 0:
        out.append(f"Recent form {s.n(p.get('form')):.1f}; PPG {s.n(p.get('points_per_game')):.1f}.")
    if s.n(p.get('availability'), 1) >= .95:
        out.append('Strong minutes/availability signal.')
    if cv <= .85:
        out.append('Lower projection uncertainty than several alternatives.')
    if edge is not None and edge > .25:
        out.append(f'Captaincy score leads the next option by {edge:.2f}.')
    return out[:4]


def selection_reason(bench, edge_player, bench_mean, edge_mean, gw):
    out = []
    pos = bench.get('position') or ''
    bf = first_fixture(bench)
    ef = first_fixture(edge_player) if edge_player else {}
    if edge_player:
        gap = edge_mean - bench_mean
        if gap > .05:
            out.append(f"{edge_player.get('player')} projects {edge_mean:.2f} vs {bench_mean:.2f} for GW{gw} (+{gap:.2f}).")
        else:
            out.append(f"{edge_player.get('player')} holds the final {pos} place in the legal best XI; the projection gap is only {abs(gap):.2f}.")
        bfd, efd = s.n(bf.get('difficulty'), 3), s.n(ef.get('difficulty'), 3)
        if bfd != efd:
            if bfd > efd:
                out.append(f"Fixture is tougher: {bf.get('opponent') or 'opponent'} FDR {int(bfd)} vs {ef.get('opponent') or 'opponent'} FDR {int(efd)}.")
            else:
                out.append(f"Fixture is easier on paper (FDR {int(bfd)} vs {int(efd)}), but the calibrated player projection still favours {edge_player.get('player')}.")
        ba, ea = s.n(bench.get('availability'), 1), s.n(edge_player.get('availability'), 1)
        if abs(ba - ea) >= .05:
            out.append(f"Availability/minutes signal: {ba*100:.0f}% vs {ea*100:.0f}%.")
    if pos == 'GKP':
        out.append('Only one goalkeeper can start, so the higher projected goalkeeper takes the XI place.')
    elif not edge_player:
        out.append('Formation constraints and the total-XI optimisation leave this player on the bench rather than a direct same-position swap.')
    return out[:3]


def run():
    latest = load(LATEST, {})
    pool = load(POOL, {})
    scout = load(SCOUT, {})
    market = load(MARKET, {})
    if latest.get('status') != 'SUCCESS':
        raise RuntimeError('latest.json not ready')

    current_gw = int(latest.get('current_gw') or 0)
    gw = int(latest.get('next_gw') or current_gw + 1)
    maturity = season_maturity(current_gw)
    by_id, by_name = s.player_maps(pool)
    sm, mm = s.scout_lookup(scout), s.market_lookup(market)
    rows = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    squad = [s.enrich(x, by_id, by_name) for x in rows]
    squad = [x for x in squad if x]
    pool_rows = [x for x in pool.get('players') or [] if pid(x)]
    vals = [s.n(x.get('six_gw_score')) for x in pool_rows]
    lo, hi = s.percentile(vals, .10), s.percentile(vals, .90)

    exp_for_gw = {}
    for p in squad:
        exp_for_gw[pid(p)] = calibrated_expected_gw(p, gw, lo, hi, sm, mm, current_gw=current_gw)

    means = {player_id: vals[0] for player_id, vals in exp_for_gw.items()}
    xi, _ = s.best_xi(squad, means)
    xi_ids = [pid(p) for p in xi]
    xi_set = set(xi_ids)
    ranked = cm.ranked_candidates(squad, xi_ids, gw, exp_for_gw)

    # Persist the selection explanation from the exact same calibrated GW means used
    # by best_xi, so the UI never has to invent a second selection model.
    bench = [p for p in squad if pid(p) not in xi_set]
    non_gk_bench = sorted([p for p in bench if p.get('position') != 'GKP'], key=lambda p: exp_for_gw.get(pid(p), (0, 0))[0], reverse=True)
    gk_bench = sorted([p for p in bench if p.get('position') == 'GKP'], key=lambda p: exp_for_gw.get(pid(p), (0, 0))[0], reverse=True)
    bench_order = non_gk_bench + gk_bench
    selection_rationale = []
    for p in bench_order:
        mean, cv = exp_for_gw.get(pid(p), (0, 0))
        same = [x for x in xi if x.get('position') == p.get('position')]
        edge_player = min(same, key=lambda x: exp_for_gw.get(pid(x), (0, 0))[0]) if same else None
        edge_mean = exp_for_gw.get(pid(edge_player), (0, 0))[0] if edge_player else 0
        selection_rationale.append({
            'player_id': pid(p),
            'player': p.get('player'),
            'position': p.get('position'),
            'expected_points': round(mean, 2),
            'projection_cv': round(cv, 3),
            'edge_player_id': pid(edge_player) if edge_player else None,
            'edge_player': edge_player.get('player') if edge_player else None,
            'edge_expected_points': round(edge_mean, 2) if edge_player else None,
            'edge': round(edge_mean - mean, 2) if edge_player else None,
            'reasons': selection_reason(p, edge_player, mean, edge_mean, gw),
        })

    xi_projection = []
    for p in xi:
        mean, cv = exp_for_gw.get(pid(p), (0, 0))
        xi_projection.append({
            'player_id': pid(p),
            'player': p.get('player'),
            'position': p.get('position'),
            'expected_points': round(mean, 2),
            'projection_cv': round(cv, 3),
        })

    candidates = []
    for row in ranked:
        p = row['player']
        f = row['fixture']
        candidates.append({
            'player_id': row['player_id'],
            'player': p.get('player'),
            'club': p.get('club'),
            'position': p.get('position'),
            'price': s.n(p.get('price')),
            'opponent': (f or {}).get('opponent'),
            'venue': (f or {}).get('venue'),
            'fixture_difficulty': s.n((f or {}).get('difficulty'), 3),
            'expected_points': round(row['mean'], 2),
            'projection_cv': round(row['cv'], 3),
            'form': s.n(p.get('form')),
            'points_per_game': s.n(p.get('points_per_game')),
            'availability': s.n(p.get('availability'), 1),
            'captaincy_score': round(row['captaincy_score'], 3),
        })

    top = candidates[:5]
    if not top:
        raise RuntimeError('No captaincy candidates')
    leader = top[0]
    vice = top[1] if len(top) > 1 else None
    edge = leader['captaincy_score'] - (vice or leader)['captaincy_score']
    leader['reasons'] = reasons(leader, leader['expected_points'], leader['projection_cv'], {
        'opponent': leader.get('opponent'), 'venue': leader.get('venue'), 'difficulty': leader.get('fixture_difficulty')
    }, edge)
    for c in top[1:]:
        c['reasons'] = reasons(c, c['expected_points'], c['projection_cv'], {
            'opponent': c.get('opponent'), 'venue': c.get('venue'), 'difficulty': c.get('fixture_difficulty')
        })
        c['gap_to_leader'] = round(leader['captaincy_score'] - c['captaincy_score'], 3)

    confidence = max(45, min(90, round(58 + edge * 9 + max(0, .9 - leader['projection_cv']) * 18)))
    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 3,
        'next_gw': gw,
        'season_maturity_weight': round(maturity, 3),
        'recommended_xi_ids': xi_ids,
        'xi_projection': xi_projection,
        'bench_order_ids': [pid(p) for p in bench_order],
        'selection_rationale': selection_rationale,
        'captain': leader,
        'vice_captain': vice,
        'shortlist': top,
        'confidence': confidence,
        'score_edge_to_second': round(edge, 3),
        'method_note': 'XI explanations use the same calibrated GW projections and legal best-XI optimiser as the simulations. Captaincy candidates are restricted to that XI and ranked by the shared captaincy model.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'captain': leader['player'], 'vice': (vice or {}).get('player'), 'confidence': confidence, 'version': 3}))


if __name__ == '__main__':
    run()
