import math


def clamp(value, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(value)))


def residual_season_parameters(current_gw, horizon_end_gw, league_size=8):
    """Parameters for a deliberately conservative season-end continuation model.

    The high-confidence Monte Carlo horizon is simulated player-by-player elsewhere.
    Beyond that horizon, exact squads/transfers are unknowable, so this layer mean-
    reverts current projected team strength and carries substantial residual variance.
    It is intended for route comparison, not false precision about final rank.
    """
    current_gw = max(0, min(38, int(current_gw or 0)))
    horizon_end_gw = max(current_gw, min(38, int(horizon_end_gw or current_gw)))
    remaining = max(0, 38 - horizon_end_gw)
    stage = clamp(current_gw / 38.0)

    # Only a fraction of current squad edge is assumed to persist, because future
    # transfers, captaincy and injuries rapidly change squads. Persistence fades
    # even further when a long residual season remains.
    persistence = clamp(.24 - remaining * .004 + stage * .08, .08, .28)

    # Manager-specific weekly residual noise after accounting for shared/common
    # FPL scoring. This intentionally keeps early-season win probabilities broad.
    weekly_specific_sd = 10.5
    residual_sd = weekly_specific_sd * math.sqrt(remaining) if remaining else 0.0

    # Probability outputs are less trustworthy when most of the season lies beyond
    # the explicit player-level simulation horizon.
    if remaining >= 20:
        confidence = 'LOW'
    elif remaining >= 10:
        confidence = 'MEDIUM'
    else:
        confidence = 'HIGH'

    return {
        'remaining_gameweeks_after_horizon': remaining,
        'season_stage': round(stage, 3),
        'projected_edge_persistence': round(persistence, 3),
        'weekly_manager_specific_sd': weekly_specific_sd,
        'residual_score_sd': round(residual_sd, 2),
        'league_size': max(1, int(league_size or 1)),
        'confidence': confidence,
        'method': 'Mean-reverting residual-season continuation after explicit player-level Monte Carlo horizon',
    }


def projected_residual_mean(weekly_edge, params):
    """Expected residual-season advantage relative to league-average scoring."""
    remaining = int(params.get('remaining_gameweeks_after_horizon') or 0)
    persistence = float(params.get('projected_edge_persistence') or 0.0)
    return float(weekly_edge or 0.0) * persistence * remaining


def terminal_score(horizon_total, weekly_edge, standard_normal_draw, params):
    mean_edge = projected_residual_mean(weekly_edge, params)
    sd = float(params.get('residual_score_sd') or 0.0)
    return float(horizon_total) + mean_edge + float(standard_normal_draw or 0.0) * sd
