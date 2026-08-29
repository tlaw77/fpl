import json
from datetime import datetime, timezone

import path_simulation as p
from projection_calibration import expected_gw as calibrated_expected_gw, season_maturity


def run():
    latest = p.load_json(p.LATEST, {})
    pool = p.load_json(p.POOL, {})
    scout = p.load_json(p.SCOUT, {})
    market = p.load_json(p.MARKET, {})
    chip = p.load_json(p.CHIPS, {})
    by_id, by_name = p.player_maps(pool)
    scout_maps, market_maps = p.scout_lookup(scout), p.market_lookup(market)

    raw = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    base_squad = [p.enrich(x, by_id, by_name) for x in raw]
    base_squad = [x for x in base_squad if x]
    rivals = p.rival_squads(latest, by_id, by_name)
    next_gw = int(latest.get('next_gw') or 1)
    current_gw = int(latest.get('current_gw') or max(0, next_gw - 1))
    maturity = season_maturity(current_gw)
    gws = list(range(next_gw, min(39, next_gw + p.DEPTH)))

    pool_rows = [x for x in pool.get('players') or [] if p.pid(x)]
    model_vals = [p.n(x.get('six_gw_score')) for x in pool_rows]
    lo, hi = p.percentile(model_vals, .10), p.percentile(model_vals, .90)

    # path_simulation.expected_table resolves its module-level expected_gw at runtime.
    # Override it here so beam search and Monte Carlo share the same calibrated means.
    p.expected_gw = lambda player, gw, model_lo, model_hi, sm, mm: calibrated_expected_gw(
        player, gw, model_lo, model_hi, sm, mm, current_gw=current_gw
    )
    exp = p.expected_table(pool_rows, gws, lo, hi, scout_maps, market_maps)

    raw_ft = latest.get('free_transfers_remaining_next_gw')
    if raw_ft is None:
        raw_ft = (latest.get('me') or {}).get('free_transfers_next_gw')
    if raw_ft is None:
        raw_ft = 1
    start_ft = max(0, min(p.MAX_FT, int(raw_ft)))
    bank = p.n(latest.get('current_bank', (latest.get('me') or {}).get('bank')))

    finalists = p.beam_search(base_squad, bank, start_ft, gws, pool_rows, exp)
    results = p.simulate_paths(finalists, rivals, gws, exp, latest)
    rival_meta = [{k: r.get(k) for k in ('entry_id', 'team_name', 'manager', 'rank', 'total_points')} for r in rivals]
    portfolio = chip.get('portfolio') or chip.get('summary') or {}

    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine_version': 4,
        'planner': 'bounded beam search + GW-specific shared-outcome Monte Carlo + live FT state + season calibration',
        'projection_model': 'season-maturity calibrated',
        'season_maturity_weight': round(maturity, 3),
        'depth_gameweeks': gws[:p.DEPTH],
        'beam_width': p.BEAM_WIDTH,
        'iterations': p.ITERATIONS,
        'starting_free_transfers': start_ft,
        'max_free_transfers': p.MAX_FT,
        'transfer_hit_cost': 4,
        'next_transfer_hit_cost': int(latest.get('next_transfer_hit_cost') or (0 if start_ft > 0 else 4)),
        'chip_portfolio_context': portfolio,
        'rivals': rival_meta,
        'recommendation': results[0] if results else None,
        'paths': results,
        'method_note': 'Each path is scored with the actual squad owned in each Gameweek. Current-deadline hits use live FT state. Early-season form and model extremes are shrunk toward positional and fixture priors, with the evidence weight increasing automatically as the season matures.',
    }
    p.OUT.parent.mkdir(parents=True, exist_ok=True)
    p.OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'best': output['recommendation'], 'paths': len(results), 'starting_ft': start_ft, 'maturity': round(maturity, 3)}))


if __name__ == '__main__':
    run()
