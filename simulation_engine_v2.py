import json
import random
import statistics
from datetime import datetime, timezone

import captaincy_model as cm
import league_win_model as lwm
import simulation_engine as s
from projection_calibration import expected_gw as calibrated_expected_gw, season_maturity


def model_lineup(squad, gw, exp, league_context=None):
    means = {pid: v[0] for pid, v in exp.get(gw, {}).items()}
    xi, _ = s.best_xi(squad, means)
    ids = [int(p.get('player_id') or 0) for p in xi]
    cap_id = cm.choose_captain(squad, ids, gw, exp.get(gw, {}), league_context=league_context)
    return ids, cap_id


def expected_lineup_score(xi, cap, gw, exp):
    values = exp.get(gw, {})
    return sum(values.get(pid, (0.0, 0.0))[0] for pid in xi) + values.get(cap, (0.0, 0.0))[0]


def league_objective_state(current_gw, current_rank, me_points, rivals):
    """Describe how much mini-league outcome should influence utility."""
    stage = max(0.0, min(1.0, float(current_gw or 0) / 38.0))
    rival_points = [s.n(r.get('total_points')) for r in rivals]
    leader_points = max([me_points, *rival_points], default=me_points)
    gap_to_leader = max(0.0, leader_points - me_points)
    remaining = max(1, 38 - int(current_gw or 0))
    chase_rate = gap_to_leader / remaining

    lead_prob_weight = 2.0 + 24.0 * (stage ** 1.7)
    gap_weight = .025 + .16 * (stage ** 1.5)
    season_win_weight = 1.5 + 28.0 * (stage ** 1.9)
    if current_rank == 1:
        posture = 'PROTECT_EDGE'
    elif chase_rate >= 2.0:
        posture = 'CHASE'
        lead_prob_weight *= 1.18
        season_win_weight *= 1.20
    elif chase_rate >= .8:
        posture = 'CONTROLLED_CHASE'
        lead_prob_weight *= 1.08
        season_win_weight *= 1.10
    else:
        posture = 'BALANCED'

    return {
        'season_stage': round(stage, 3),
        'current_rank': int(current_rank),
        'current_gap_to_leader': round(gap_to_leader, 2),
        'gameweeks_remaining': remaining,
        'required_gain_per_remaining_gw': round(chase_rate, 3),
        'posture': posture,
        'lead_probability_weight': round(lead_prob_weight, 3),
        'season_win_probability_weight': round(season_win_weight, 3),
        'leader_gap_weight': round(gap_weight, 4),
    }


def compact_captain_mode(row):
    if not row:
        return None
    return {
        'player_id': int(row.get('player_id') or 0),
        'player': (row.get('player') or {}).get('player'),
        'expected_points': round(s.n(row.get('mean')), 2),
        'captaincy_score': round(s.n(row.get('captaincy_score')), 3),
        'safe_score': round(s.n(row.get('safe_score')), 3),
        'chase_score': round(s.n(row.get('chase_score')), 3),
        'mini_league_ownership_pct': row.get('mini_league_ownership_pct'),
        'ev_gap_to_best': row.get('ev_gap_to_best'),
        'chase_eligible': row.get('chase_eligible'),
    }


def run():
    latest = s.load_json(s.LATEST, {})
    pool = s.load_json(s.POOL, {})
    scout = s.load_json(s.SCOUT, {})
    market = s.load_json(s.MARKET, {})
    by_id, by_name = s.player_maps(pool)
    scout_maps, market_maps = s.scout_lookup(scout), s.market_lookup(market)

    base_raw = latest.get('current_squad_next5') or latest.get('squad_next5') or latest.get('squad') or []
    base_squad = [s.enrich(p, by_id, by_name) for p in base_raw]
    base_squad = [p for p in base_squad if p]
    rivals = s.rival_squads(latest, by_id, by_name)
    candidates = s.candidate_routes(latest, base_squad, by_id, by_name)
    next_gw = int(latest.get('next_gw') or 1)
    current_gw = int(latest.get('current_gw') or max(0, next_gw - 1))
    maturity = season_maturity(current_gw)
    gws = list(range(next_gw, min(39, next_gw + s.HORIZON)))
    captain_context = cm.build_league_context(latest, current_gw)

    raw_ft = latest.get('free_transfers_remaining_next_gw')
    if raw_ft is None:
        raw_ft = (latest.get('me') or {}).get('free_transfers_next_gw')
    if raw_ft is None:
        raw_ft = 1
    remaining_ft = max(0, min(5, int(raw_ft)))
    next_hit_cost = int(latest.get('next_transfer_hit_cost') or (0 if remaining_ft > 0 else 4))

    pool_models = [s.n(p.get('six_gw_score')) for p in pool.get('players') or []]
    model_lo, model_hi = s.percentile(pool_models, .10), s.percentile(pool_models, .90)

    universe = {}
    for c in candidates:
        for p in c['squad']:
            universe[int(p.get('player_id') or 0)] = p
    for r in rivals:
        for p in r['squad']:
            universe[int(p.get('player_id') or 0)] = p
    universe.pop(0, None)

    exp = {}
    for gw in gws:
        exp[gw] = {}
        for pid, player in universe.items():
            exp[gw][pid] = calibrated_expected_gw(player, gw, model_lo, model_hi, scout_maps, market_maps, current_gw=current_gw)

    cand_lineups = {}
    cand_weekly_means = {}
    for c in candidates:
        cand_lineups[c['key']] = {}
        weekly = []
        for gw in gws:
            # Only the immediate deadline receives league-state captaincy. Future
            # gameweeks revert to Best-EV because strategy should be re-optimised
            # after each deadline rather than pre-committed weeks in advance.
            context = captain_context if gw == next_gw else None
            lineup = model_lineup(c['squad'], gw, exp, league_context=context)
            cand_lineups[c['key']][gw] = lineup
            weekly.append(expected_lineup_score(*lineup, gw, exp))
        cand_weekly_means[c['key']] = statistics.fmean(weekly) if weekly else 0.0

    baseline_key = next((c['key'] for c in candidates if c.get('move') is None), 'ROLL')
    baseline_first_xi, baseline_first_cap = cand_lineups.get(baseline_key, {}).get(next_gw, ([], 0))
    baseline_ranked = cm.ranked_candidates(base_squad, baseline_first_xi, next_gw, exp.get(next_gw, {}), league_context=captain_context)
    baseline_modes = cm.captain_modes(baseline_ranked, captain_context)

    rival_lineups = []
    rival_weekly_means = []
    for r in rivals:
        bygw = {}
        weekly = []
        for gw in gws:
            # Rival behaviour uses the football-EV captain model. We do not assume
            # rivals share our own protect/chase posture.
            lineup = model_lineup(r['squad'], gw, exp)
            bygw[gw] = lineup
            weekly.append(expected_lineup_score(*lineup, gw, exp))
        rival_lineups.append(bygw)
        rival_weekly_means.append(statistics.fmean(weekly) if weekly else 0.0)

    rng = random.Random(str(latest.get('generated_at_utc') or '') + '|simulation-v8-captain-strategy')
    me_start = s.n((latest.get('me') or {}).get('total_points'))
    current_rank = int((latest.get('me') or {}).get('rank') or (len(rivals) + 1))
    objective = league_objective_state(current_gw, current_rank, me_start, rivals)
    horizon_end = max(gws) if gws else current_gw
    residual = lwm.residual_season_parameters(current_gw, horizon_end, league_size=len(rivals) + 1)
    league_weekly_reference = statistics.fmean([cand_weekly_means.get(baseline_key, 0.0), *rival_weekly_means]) if rivals else cand_weekly_means.get(baseline_key, 0.0)
    residual_conf_factor = {'LOW': .35, 'MEDIUM': .65, 'HIGH': .90}.get(residual.get('confidence'), .35)

    route_totals = {c['key']: [] for c in candidates}
    route_ranks = {c['key']: [] for c in candidates}
    route_gain_places = {c['key']: 0 for c in candidates}
    route_beat = {c['key']: [0] * len(rivals) for c in candidates}
    route_lead = {c['key']: 0 for c in candidates}
    route_gap_to_best_rival = {c['key']: [] for c in candidates}
    route_season_win = {c['key']: 0 for c in candidates}
    route_terminal_gap = {c['key']: [] for c in candidates}

    for _ in range(s.ITERATIONS):
        outcomes = {}
        for gw in gws:
            outcomes[gw] = {pid: s.sample_points(rng, *params) for pid, params in exp[gw].items()}

        rival_scores = []
        for idx, r in enumerate(rivals):
            total = r['total_points']
            for gw in gws:
                xi, cap = rival_lineups[idx][gw]
                total += sum(outcomes[gw].get(pid, 0) for pid in xi) + outcomes[gw].get(cap, 0)
            rival_scores.append(total)
        best_rival = max(rival_scores, default=me_start)

        me_residual_draw = rng.gauss(0.0, 1.0)
        rival_residual_draws = [rng.gauss(0.0, 1.0) for _ in rivals]
        terminal_rivals = [
            lwm.terminal_score(
                rival_scores[i],
                rival_weekly_means[i] - league_weekly_reference,
                rival_residual_draws[i],
                residual,
            )
            for i in range(len(rivals))
        ]
        best_terminal_rival = max(terminal_rivals, default=me_start)

        for c in candidates:
            total = me_start
            hit = 0 if c['move'] is None else next_hit_cost
            for gw in gws:
                xi, cap = cand_lineups[c['key']][gw]
                total += sum(outcomes[gw].get(pid, 0) for pid in xi) + outcomes[gw].get(cap, 0)
            total -= hit
            route_totals[c['key']].append(total - me_start)
            rank = 1 + sum(1 for x in rival_scores if x > total)
            route_ranks[c['key']].append(rank)
            route_gap_to_best_rival[c['key']].append(total - best_rival)
            if rank == 1:
                route_lead[c['key']] += 1
            if rank < current_rank:
                route_gain_places[c['key']] += 1
            for i, rv in enumerate(rival_scores):
                if total > rv:
                    route_beat[c['key']][i] += 1

            terminal_me = lwm.terminal_score(
                total,
                cand_weekly_means[c['key']] - league_weekly_reference,
                me_residual_draw,
                residual,
            )
            route_terminal_gap[c['key']].append(terminal_me - best_terminal_rival)
            if all(terminal_me >= rv for rv in terminal_rivals):
                route_season_win[c['key']] += 1

    results = []
    for c in candidates:
        vals = route_totals[c['key']]
        ranks = route_ranks[c['key']]
        gaps = route_gap_to_best_rival[c['key']]
        terminal_gaps = route_terminal_gap[c['key']]
        p10, p90 = s.percentile(vals, .10), s.percentile(vals, .90)
        mean = statistics.fmean(vals) if vals else 0
        exp_rank = statistics.fmean(ranks) if ranks else current_rank
        lead_prob = route_lead[c['key']] / s.ITERATIONS
        season_win_prob = route_season_win[c['key']] / s.ITERATIONS
        expected_gap = statistics.fmean(gaps) if gaps else 0.0
        expected_terminal_gap = statistics.fmean(terminal_gaps) if terminal_gaps else 0.0

        rank_value = (current_rank - exp_rank) * 5.0
        downside_penalty = max(0, mean - p10) * .12
        league_value = (
            lead_prob * objective['lead_probability_weight']
            + expected_gap * objective['leader_gap_weight']
            + season_win_prob * objective['season_win_probability_weight'] * residual_conf_factor
        )
        utility = mean + rank_value - downside_penalty + league_value

        hit = 0 if c['move'] is None else next_hit_cost
        incoming_starts = None
        out_id = None
        in_id = None
        post_xi, post_cap = cand_lineups.get(c['key'], {}).get(next_gw, ([], 0))
        if c['move'] is not None and gws:
            out = c['move'].get('out') or {}
            inc = c['move'].get('safe_in') or c['move'].get('in') or {}
            out_id = int(out.get('player_id') or 0) or None
            in_id = int(inc.get('player_id') or 0) or None
            incoming_starts = bool(in_id and in_id in set(post_xi))
        results.append({
            'route': c['label'],
            'action': 'ROLL' if c['move'] is None else 'TRANSFER',
            'hit_cost': hit,
            'out_player_id': out_id,
            'in_player_id': in_id,
            'expected_points_6gw': round(mean, 2),
            'p10_points_6gw': round(p10, 2),
            'p90_points_6gw': round(p90, 2),
            'expected_rank_after_horizon': round(exp_rank, 2),
            'prob_gain_league_place': round(route_gain_places[c['key']] / s.ITERATIONS, 3),
            'prob_league_lead_after_horizon': round(lead_prob, 3),
            'expected_gap_to_best_rival_after_horizon': round(expected_gap, 2),
            'estimated_prob_win_mini_league': round(season_win_prob, 3),
            'estimated_final_gap_to_best_rival': round(expected_terminal_gap, 2),
            'season_win_estimate_confidence': residual.get('confidence'),
            'prob_finish_ahead_each_rival': [round(route_beat[c['key']][i] / s.ITERATIONS, 3) for i in range(len(rivals))],
            'league_objective_value': round(league_value, 3),
            'utility_score': round(utility, 3),
            'incoming_starts_gw3': incoming_starts,
            'decision_lineup_gw': next_gw,
            'baseline_xi_ids': list(baseline_first_xi),
            'baseline_captain_id': baseline_first_cap,
            'post_transfer_xi_ids': list(post_xi),
            'post_transfer_captain_id': post_cap,
        })
    results.sort(key=lambda x: x['utility_score'], reverse=True)

    rival_meta = [
        {'entry_id': r['entry_id'], 'team_name': r['team_name'], 'manager': r['manager'], 'rank': r['rank'], 'total_points': r['total_points']}
        for r in rivals
    ]
    winner = results[0] if results else None
    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'engine_version': 8,
        'projection_model': 'season-maturity calibrated + immediate league-aware captaincy + mini-league season-win objective',
        'season_maturity_weight': round(maturity, 3),
        'iterations': s.ITERATIONS,
        'horizon_gws': gws,
        'shared_outcome_simulation': True,
        'remaining_free_transfers_current_deadline': remaining_ft,
        'next_transfer_hit_cost': next_hit_cost,
        'candidate_count': len(results),
        'league_objective': objective,
        'residual_season_model': residual,
        'captaincy_strategy': {
            'posture': captain_context.get('posture'),
            'season_stage': captain_context.get('season_stage'),
            'recommended_mode': baseline_modes.get('recommended_mode'),
            'best_ev': compact_captain_mode(baseline_modes.get('BEST_EV')),
            'safe': compact_captain_mode(baseline_modes.get('SAFE')),
            'chase': compact_captain_mode(baseline_modes.get('CHASE')),
            'applies_to_gw': next_gw,
            'future_gws_revert_to_best_ev': True,
        },
        'rivals': rival_meta,
        'recommendation': winner,
        'routes': results,
        'backtest_contract': {
            'target_gw': next_gw,
            'baseline_xi_ids': list(baseline_first_xi),
            'baseline_captain_id': baseline_first_cap,
            'note': 'Each route stores exact out/in IDs plus the pre-decision and post-transfer XI/captain selected by the model at decision time. Immediate captaincy may use the explicit league-state mode; future gameweeks revert to Best-EV and are re-optimised at their own deadlines.'
        },
        'method_note': 'Expected FPL points remain primary. Immediate captaincy uses Safe/Best-EV/Chase logic with an EV-gap guardrail; future captaincy remains Best-EV because league state will be re-evaluated each deadline. The explicit player-level Monte Carlo covers the planning horizon, followed by a high-variance mean-reverting residual-season continuation for mini-league win probability.',
    }
    s.OUT.parent.mkdir(parents=True, exist_ok=True)
    s.OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'winner': winner, 'iterations': s.ITERATIONS, 'maturity': round(maturity, 3), 'remaining_ft': remaining_ft, 'next_hit_cost': next_hit_cost, 'engine_version': 8, 'league_posture': objective['posture'], 'captain_mode': baseline_modes.get('recommended_mode'), 'season_win_confidence': residual.get('confidence'), 'captain': baseline_first_cap}))


if __name__ == '__main__':
    run()
