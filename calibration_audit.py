import json
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROJECTIONS = Path('data/projection_history')
HISTORY = Path('data/history')
OUT = Path('data/calibration_audit.json')


def load(path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return {} if default is None else default


def n(v, d=0.0):
    try:
        x = float(v)
        return x if math.isfinite(x) else d
    except Exception:
        return d


def mean(values):
    return sum(values) / len(values) if values else None


def rmse(values):
    return math.sqrt(sum(x * x for x in values) / len(values)) if values else None


def outcome_map(gw):
    path = HISTORY / f'gw{gw}' / 'player_outcomes.json'
    data = load(path, {})
    return {int(x.get('player_id') or 0): x for x in data.get('players') or [] if x.get('player_id')}


def calibration_status(gameweeks):
    if gameweeks < 3:
        return 'INSUFFICIENT_EVIDENCE'
    if gameweeks < 6:
        return 'ACCUMULATING'
    if gameweeks < 12:
        return 'DESCRIPTIVE_ONLY'
    return 'ACTIONABLE_REVIEW'


def probability_metrics(rows, prob_key, actual_fn):
    pairs = []
    for r in rows:
        p = max(0.0, min(1.0, n(r.get(prob_key))))
        actual = 1.0 if actual_fn(r) else 0.0
        pairs.append((p, actual))
    if not pairs:
        return None
    brier = mean([(p - a) ** 2 for p, a in pairs])
    predicted = mean([p for p, _ in pairs])
    observed = mean([a for _, a in pairs])
    return {
        'n': len(pairs),
        'mean_predicted_probability': round(predicted, 4),
        'observed_rate': round(observed, 4),
        'calibration_gap': round(observed - predicted, 4),
        'brier_score': round(brier, 4),
    }


def grouped(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or 'UNKNOWN')].append(row)
    out = {}
    for name, vals in groups.items():
        errors = [n(x.get('actual_points')) - n(x.get('expected_points')) for x in vals]
        abs_errors = [abs(x) for x in errors]
        mins_errors = [n(x.get('actual_minutes')) - n(x.get('expected_minutes')) for x in vals]
        out[name] = {
            'n': len(vals),
            'mean_points_bias_actual_minus_forecast': round(mean(errors), 3),
            'mae_points': round(mean(abs_errors), 3),
            'mean_minutes_bias_actual_minus_forecast': round(mean(mins_errors), 3),
        }
    return out


def main():
    matched_rows = []
    evaluated_gws = []
    skipped = []

    for projection_file in sorted(PROJECTIONS.glob('gw*.json')):
        try:
            gw = int(projection_file.stem[2:])
        except Exception:
            continue
        outcomes = outcome_map(gw)
        if not outcomes:
            skipped.append({'gw': gw, 'reason': 'finalized_outcomes_not_available'})
            continue
        projection = load(projection_file, {})
        if int(projection.get('target_gw') or 0) != gw:
            skipped.append({'gw': gw, 'reason': 'target_gw_mismatch'})
            continue
        rows = []
        for p in projection.get('players') or []:
            pid = int(p.get('player_id') or 0)
            outcome = outcomes.get(pid)
            if not outcome:
                continue
            row = dict(p)
            row['actual_points'] = n(outcome.get('total_points'))
            row['actual_minutes'] = n(outcome.get('minutes'))
            row['actual_appearance'] = 1 if n(outcome.get('minutes')) > 0 else 0
            row['actual_60_plus'] = 1 if n(outcome.get('minutes')) >= 60 else 0
            row['actual_80_plus'] = 1 if n(outcome.get('minutes')) >= 80 else 0
            rows.append(row)
        if rows:
            evaluated_gws.append(gw)
            matched_rows.extend(rows)

    gw_count = len(evaluated_gws)
    status = calibration_status(gw_count)
    point_errors = [n(x.get('actual_points')) - n(x.get('expected_points')) for x in matched_rows]
    absolute_errors = [abs(x) for x in point_errors]
    minute_errors = [n(x.get('actual_minutes')) - n(x.get('expected_minutes')) for x in matched_rows]
    standardized = []
    coverage80 = []
    for row in matched_rows:
        sd = max(.25, n(row.get('projection_sd'), .25))
        error = n(row.get('actual_points')) - n(row.get('expected_points'))
        standardized.append(error / sd)
        lo = n(row.get('expected_points')) - 1.2816 * sd
        hi = n(row.get('expected_points')) + 1.2816 * sd
        coverage80.append(1 if lo <= n(row.get('actual_points')) <= hi else 0)

    metrics = {
        'player_observations': len(matched_rows),
        'evaluable_gameweeks': gw_count,
        'evaluated_gws': evaluated_gws,
        'mean_points_bias_actual_minus_forecast': round(mean(point_errors), 4) if point_errors else None,
        'mae_points': round(mean(absolute_errors), 4) if absolute_errors else None,
        'rmse_points': round(rmse(point_errors), 4) if point_errors else None,
        'mean_minutes_bias_actual_minus_forecast': round(mean(minute_errors), 4) if minute_errors else None,
        'mean_standardized_error': round(mean(standardized), 4) if standardized else None,
        'nominal_80pct_interval_observed_coverage': round(mean(coverage80), 4) if coverage80 else None,
        'appearance_probability': probability_metrics(matched_rows, 'prob_appearance', lambda r: r.get('actual_appearance') == 1),
        'sixty_plus_probability': probability_metrics(matched_rows, 'prob_60_plus', lambda r: r.get('actual_60_plus') == 1),
        'eighty_plus_probability': probability_metrics(matched_rows, 'prob_80_plus', lambda r: r.get('actual_80_plus') == 1),
        'by_position': grouped(matched_rows, 'position') if matched_rows else {},
        'by_minutes_band': grouped(matched_rows, 'minutes_band') if matched_rows else {},
        'by_signal_agreement': grouped(matched_rows, 'signal_agreement') if matched_rows else {},
    }

    alerts = []
    if gw_count >= 6 and point_errors:
        bias = mean(point_errors)
        if abs(bias) >= .55:
            alerts.append({
                'type': 'POINTS_MEAN_BIAS',
                'severity': 'WATCH',
                'detail': f'Average actual-minus-forecast bias is {bias:+.2f} points across {gw_count} GWs.',
            })
        coverage = mean(coverage80)
        if coverage is not None and (coverage < .70 or coverage > .90):
            alerts.append({
                'type': 'UNCERTAINTY_CALIBRATION',
                'severity': 'WATCH',
                'detail': f'Nominal 80% interval is covering {coverage*100:.1f}% of observations.',
            })
    if gw_count >= 12:
        for key, label in [('appearance_probability', 'appearance'), ('sixty_plus_probability', '60+'), ('eighty_plus_probability', '80+')]:
            m = metrics.get(key) or {}
            gap = n(m.get('calibration_gap'))
            if abs(gap) >= .08:
                alerts.append({
                    'type': 'MINUTES_PROBABILITY_BIAS',
                    'severity': 'REVIEW',
                    'detail': f'{label} observed rate differs from predicted probability by {gap:+.1%}.',
                })

    recommendation = {
        'status': status,
        'auto_tuning_enabled': False,
        'minimum_gws_for_descriptive_review': 6,
        'minimum_gws_for_actionable_review': 12,
        'instruction': (
            'Accumulate evidence only; do not alter coefficients.' if gw_count < 6 else
            'Review biases descriptively but do not auto-change coefficients.' if gw_count < 12 else
            'Bias alerts may justify a bounded manual coefficient review. Automatic self-mutation remains disabled.'
        ),
    }

    output = {
        'status': 'SUCCESS',
        'version': 1,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'calibration_status': status,
        'metrics': metrics,
        'alerts': alerts,
        'recommendation': recommendation,
        'skipped_projection_gws': skipped,
        'method_note': 'Pairs hindsight-safe pre-GW projection_history snapshots with finalized all-player FPL outcomes. Evaluates point bias/error, uncertainty coverage and minutes-probability calibration. Evidence gates are based on completed Gameweeks, not raw player-row count, to avoid false confidence from hundreds of correlated observations in one week.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'calibration_status': status, 'gameweeks': gw_count, 'players': len(matched_rows), 'alerts': len(alerts)}))


if __name__ == '__main__':
    main()
