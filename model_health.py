import json
from datetime import datetime, timezone
from pathlib import Path

LATEST = Path('data/latest.json')
POOL = Path('data/player_pool.json')
SCOUT = Path('data/scout_consensus.json')
CONSENSUS = Path('data/signal_consensus.json')
MARKET_STRENGTH = Path('data/market_strength.json')
CALIBRATION = Path('data/calibration_audit.json')
STABILITY = Path('data/simulation_stability.json')
BACKTEST = Path('data/backtest_summary.json')
OUT = Path('data/model_health.json')
HISTORY = Path('data/model_health_history')


def load(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if default is None else default


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def age_hours(payload):
    raw = payload.get('generated_at_utc')
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)
    except Exception:
        return None


def domain(status, detail, **extra):
    return {'status': status, 'detail': detail, **extra}


def severity_rank(status):
    return {'HEALTHY': 0, 'AVAILABLE': 0, 'LEARNING': 1, 'OPTIONAL_UNAVAILABLE': 1, 'WATCH': 2, 'REVIEW': 3, 'DEGRADED': 4}.get(status, 1)


def main():
    latest = load(LATEST)
    pool = load(POOL)
    scout = load(SCOUT)
    consensus = load(CONSENSUS)
    market = load(MARKET_STRENGTH)
    calibration = load(CALIBRATION)
    stability = load(STABILITY)
    backtest = load(BACKTEST)

    current_gw = int(latest.get('current_gw') or 0)
    next_gw = int(latest.get('next_gw') or current_gw + 1)
    domains = {}
    reasons = []

    player_count = len(pool.get('players') or [])
    if pool.get('status') == 'SUCCESS' and player_count >= 400:
        domains['core_projection_data'] = domain('HEALTHY', f'{player_count} current FPL players available to the projection model.', player_count=player_count)
    else:
        domains['core_projection_data'] = domain('DEGRADED', f'Player-pool coverage is unexpectedly low ({player_count}).', player_count=player_count)
        reasons.append('Core player-pool coverage is degraded.')

    scout_players = len(scout.get('players') or [])
    scout_age = age_hours(scout)
    if scout.get('status') == 'SUCCESS' and scout_players > 0:
        status = 'HEALTHY' if scout_age is None or scout_age <= 12 else 'WATCH'
        domains['scout_evidence'] = domain(status, f'{scout_players} players have current Scout consensus evidence.', player_count=scout_players, age_hours=round(scout_age, 2) if scout_age is not None else None)
        if status == 'WATCH':
            reasons.append('Scout evidence is older than the preferred freshness window.')
    else:
        domains['scout_evidence'] = domain('WATCH', 'Scout corroboration is unavailable; the core model can still operate without it.', player_count=scout_players)
        reasons.append('Scout corroboration is currently unavailable.')

    if market.get('status') == 'SUCCESS' and len(market.get('fixtures') or []) > 0:
        domains['independent_market'] = domain('AVAILABLE', f"Independent market calibration covers {len(market.get('fixtures') or [])} fixtures.", fixture_count=len(market.get('fixtures') or []))
    else:
        domains['independent_market'] = domain('OPTIONAL_UNAVAILABLE', 'No current free bookmaker fixture odds are available. The market factor safely falls back to neutral.', fixture_count=0)

    summary = consensus.get('summary') or {}
    total_consensus = sum(int(summary.get(k) or 0) for k in ('strong_agreement', 'mixed', 'high_disagreement', 'low_signal'))
    high_disagreement = int(summary.get('high_disagreement') or 0)
    disagreement_rate = high_disagreement / total_consensus if total_consensus else 0.0
    if total_consensus < 100:
        domains['signal_consensus'] = domain('WATCH', 'Cross-source signal coverage is lower than expected.', players=total_consensus)
        reasons.append('Cross-source consensus coverage is low.')
    elif disagreement_rate > .28:
        domains['signal_consensus'] = domain('WATCH', f'{disagreement_rate:.1%} of covered players show high cross-source disagreement.', players=total_consensus, high_disagreement_rate=round(disagreement_rate, 4))
        reasons.append('Cross-source disagreement is elevated.')
    else:
        domains['signal_consensus'] = domain('HEALTHY', f'Cross-source disagreement is contained at {disagreement_rate:.1%}.', players=total_consensus, high_disagreement_rate=round(disagreement_rate, 4))

    cal_status = calibration.get('calibration_status') or 'INSUFFICIENT_EVIDENCE'
    cal_alerts = calibration.get('alerts') or []
    cal_gws = int((calibration.get('metrics') or {}).get('evaluable_gameweeks') or 0)
    drift = calibration.get('drift') or {}
    if cal_status in ('INSUFFICIENT_EVIDENCE', 'ACCUMULATING'):
        domains['projection_calibration'] = domain('LEARNING', f'{cal_gws} completed projection-calibration Gameweeks; evidence is still accumulating.', gameweeks=cal_gws, drift_status=drift.get('status'))
    elif cal_alerts:
        review = any(str(x.get('severity')).upper() == 'REVIEW' for x in cal_alerts)
        domains['projection_calibration'] = domain('REVIEW' if review else 'WATCH', f'{len(cal_alerts)} calibration alert(s) require attention.', gameweeks=cal_gws, drift_status=drift.get('status'), alerts=cal_alerts)
        reasons.append('Projection calibration has active bias or drift alerts.')
    else:
        domains['projection_calibration'] = domain('HEALTHY', f'{cal_gws} completed Gameweeks show no material calibration alerts.', gameweeks=cal_gws, drift_status=drift.get('status'))

    stab_summary = stability.get('summary') or {}
    evidence_runs = n(stab_summary.get('effective_evidence_runs'))
    action_persistence = n(stab_summary.get('action_persistence_pct'))
    leader_persistence = n(stab_summary.get('leader_persistence_pct'))
    if stability.get('status') != 'SUCCESS' or evidence_runs <= 0:
        domains['decision_stability'] = domain('LEARNING', 'There is not yet enough weighted simulation-stability evidence.', effective_evidence_runs=evidence_runs)
    elif evidence_runs >= 6 and action_persistence < 50:
        domains['decision_stability'] = domain('WATCH', f'Authoritative action persisted in only {action_persistence:.1f}% of weighted recent evidence.', effective_evidence_runs=evidence_runs, action_persistence_pct=action_persistence, leader_persistence_pct=leader_persistence)
        reasons.append('Recommendation action is unstable across recent meaningful input changes.')
    else:
        domains['decision_stability'] = domain('HEALTHY', f'Authoritative action persistence is {action_persistence:.1f}% across {evidence_runs:.1f} weighted runs.', effective_evidence_runs=evidence_runs, action_persistence_pct=action_persistence, leader_persistence_pct=leader_persistence)

    bt_gws = int(backtest.get('evaluable_gameweeks') or 0)
    bt_summary = backtest.get('summary') or {}
    if bt_gws < 3:
        domains['realized_decision_quality'] = domain('LEARNING', f'{bt_gws} completed decision-backtest Gameweeks; regret metrics are not mature yet.', gameweeks=bt_gws)
    else:
        avg_regret = bt_summary.get('average_transfer_decision_regret_points')
        captain_regret = bt_summary.get('average_captain_regret_points')
        watch = (avg_regret is not None and n(avg_regret) >= 4.0) or (captain_regret is not None and n(captain_regret) >= 4.0)
        domains['realized_decision_quality'] = domain('WATCH' if watch else 'HEALTHY', 'Realized decision-regret metrics are now evaluable.', gameweeks=bt_gws, average_transfer_regret=avg_regret, average_captain_regret=captain_regret)
        if watch:
            reasons.append('Realized decision regret is elevated.')

    worst = max((severity_rank(x['status']) for x in domains.values()), default=1)
    if worst >= 4:
        overall = 'DEGRADED'
    elif worst >= 3:
        overall = 'REVIEW'
    elif worst >= 2:
        overall = 'WATCH'
    elif any(x['status'] in ('LEARNING', 'OPTIONAL_UNAVAILABLE') for x in domains.values()):
        overall = 'LEARNING'
    else:
        overall = 'HEALTHY'

    tuning_state = 'LOCKED_LEARNING'
    tuning_instruction = 'Do not change coefficients; collect completed-GW calibration and decision evidence.'
    if cal_gws >= 12:
        if cal_alerts:
            tuning_state = 'BOUNDED_REVIEW_AVAILABLE'
            tuning_instruction = 'Review flagged coefficients manually and validate any proposed adjustment through backtests before deployment.'
        else:
            tuning_state = 'STABLE_MONITORING'
            tuning_instruction = 'No calibration change is indicated; continue monitoring for drift.'

    output = {
        'status': 'SUCCESS',
        'version': 1,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'current_gw': current_gw,
        'next_gw': next_gw,
        'overall_health': overall,
        'domains': domains,
        'active_reasons': reasons,
        'continuous_tuning': {
            'state': tuning_state,
            'auto_coefficient_mutation': False,
            'calibration_gameweeks': cal_gws,
            'instruction': tuning_instruction,
            'principle': 'The engine may detect drift and recommend bounded review, but model coefficients are never automatically rewritten from weak or correlated evidence.',
        },
        'method_note': 'Continuous health monitor across source coverage, cross-source disagreement, simulation stability, hindsight-safe projection calibration and realized decision backtests. LEARNING is a valid healthy-early-season state, distinct from source or model degradation.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    HISTORY.mkdir(parents=True, exist_ok=True)
    (HISTORY / f'gw{current_gw}.json').write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'overall_health': overall, 'tuning_state': tuning_state, 'calibration_gws': cal_gws, 'reasons': len(reasons)}))


if __name__ == '__main__':
    main()
