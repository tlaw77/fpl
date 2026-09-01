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


def rounded(value, digits=4):
    return round(value, digits) if value is not None else None


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
    predicted = mean([p for p, _ in pairs])
    observed = mean([a for _, a in pairs])
    return {
        'n': len(pairs),
        'mean_predicted_probability': rounded(predicted),
        'observed_rate': rounded(observed),
        'calibration_gap': rounded(observed - predicted),
        'brier_score': rounded(mean([(p - a) ** 2 for p, a in pairs])),
    }


def grouped(rows, key):
    groups = defaultdict(list)
    for row in rows:
        groups[str(row.get(key) or 'UNKNOWN')].append(row)
    out = {}
    for name, vals in groups.items():
        errors = [n(x.get('actual_points')) - n(x.get('expected_points')) for x in vals]
        mins_errors = [n(x.get('actual_minutes')) - n(x.get('expected_minutes')) for x in vals]
        out[name] = {
            'n': len(vals),
            'mean_points_bias_actual_minus_forecast': rounded(mean(errors), 3),
            'mae_points': rounded(mean([abs(x) for x in errors]), 3),
            'mean_minutes_bias_actual_minus_forecast': rounded(mean(mins_errors), 3),
        }
    return out


def summarize_rows(rows):
    errors = [n(x.get('actual_points')) - n(x.get('expected_points')) for x in rows]
    minute_errors = [n(x.get('actual_minutes')) - n(x.get('expected_minutes')) for x in rows]
    standardized = []
    coverage80 = []
    for row in rows:
        sd = max(.25, n(row.get('projection_sd'), .25))
        error = n(row.get('actual_points')) - n(row.get('expected_points'))
        standardized.append(error / sd)
        lo = n(row.get('expected_points')) - 1.2816 * sd
        hi = n(row.get('expected_points')) + 1.2816 * sd
        coverage80.append(1 if lo <= n(row.get('actual_points')) <= hi else 0)
    return {
        'player_observations': len(rows),
        'mean_points_bias_actual_minus_forecast': rounded(mean(errors)),
        'mae_points': rounded(mean([abs(x) for x in errors])),
        'rmse_points': rounded(rmse(errors)),
        'mean_minutes_bias_actual_minus_forecast': rounded(mean(minute_errors)),
        'mean_standardized_error': rounded(mean(standardized)),
        'nominal_80pct_interval_observed_coverage': rounded(mean(coverage80)),
        'appearance_probability': probability_metrics(rows, 'prob_appearance', lambda r: r.get('actual_appearance') == 1),
        'sixty_plus_probability': probability_metrics(rows, 'prob_60_plus', lambda r: r.get('actual_60_plus') == 1),
        'eighty_plus_probability': probability_metrics(rows, 'prob_80_plus', lambda r: r.get('actual_80_plus') == 1),
    }


def main():
    matched_rows = []
    evaluated_gws = []
    gameweek_metrics = []
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
            gw_summary = summarize_rows(rows)
            gw_summary['gw'] = gw
            gameweek_metrics.append(gw_summary)

    gw_count = len(evaluated_gws)
    status = calibration_status(gw_count)
    metrics = summarize_rows(matched_rows)
    metrics.update({
        'evaluable_gameweeks': gw_count,
        'evaluated_gws': evaluated_gws,
        'by_position': grouped(matched_rows, 'position') if matched_rows else {},
        'by_minutes_band': grouped(matched_rows, 'minutes_band') if matched_rows else {},
        'by_signal_agreement': grouped(matched_rows, 'signal_agreement') if matched_rows else {},
    })

    drift = {
        'status': 'NOT_ENOUGH_WINDOWS',
        'recent_window_gws': [],
        'prior_window_gws': [],
        'points_bias_shift': None,
        'mae_shift': None,
        'minutes_bias_shift': None,
        'coverage_shift': None,
    }
    if gw_count >= 6:
        recent = gameweek_metrics[-3:]
        prior = gameweek_metrics[-6:-3]
        if len(recent) == 3 and len(prior) == 3:
            def gm(rows, key):
                vals = [n(x.get(key)) for x in rows if x.get(key) is not None]
                return mean(vals)
            drift = {
                'status': 'EVALUABLE',
                'recent_window_gws': [x['gw'] for x in recent],
                'prior_window_gws': [x['gw'] for x in prior],
                'points_bias_shift': rounded(gm(recent, 'mean_points_bias_actual_minus_forecast') - gm(prior, 'mean_points_bias_actual_minus_forecast')),
                'mae_shift': rounded(gm(recent, 'mae_points') - gm(prior, 'mae_points')),
                'minutes_bias_shift': rounded(gm(recent, 'mean_minutes_bias_actual_minus_forecast') - gm(prior, 'mean_minutes_bias_actual_minus_forecast')),
                'coverage_shift': rounded(gm(recent, 'nominal_80pct_interval_observed_coverage') - gm(prior, 'nominal_80pct_interval_observed_coverage')),
            }

    alerts = []
    if gw_count >= 6 and matched_rows:
        bias = n(metrics.get('mean_points_bias_actual_minus_forecast'))
        if abs(bias) >= .55:
            alerts.append({'type': 'POINTS_MEAN_BIAS', 'severity': 'WATCH', 'detail': f'Average actual-minus-forecast bias is {bias:+.2f} points across {gw_count} GWs.'})
        coverage = metrics.get('nominal_80pct_interval_observed_coverage')
        if coverage is not None and (coverage < .70 or coverage > .90):
            alerts.append({'type': 'UNCERTAINTY_CALIBRATION', 'severity': 'WATCH', 'detail': f'Nominal 80% interval is covering {coverage*100:.1f}% of observations.'})
        if drift.get('status') == 'EVALUABLE':
            if abs(n(drift.get('points_bias_shift'))) >= .45 or n(drift.get('mae_shift')) >= .40:
                alerts.append({'type': 'RECENT_CALIBRATION_DRIFT', 'severity': 'WATCH', 'detail': 'The latest 3-GW forecast-error profile has moved materially versus the previous 3-GW window.'})
    if gw_count >= 12:
        for key, label in [('appearance_probability', 'appearance'), ('sixty_plus_probability', '60+'), ('eighty_plus_probability', '80+')]:
            m = metrics.get(key) or {}
            gap = n(m.get('calibration_gap'))
            if abs(gap) >= .08:
                alerts.append({'type': 'MINUTES_PROBABILITY_BIAS', 'severity': 'REVIEW', 'detail': f'{label} observed rate differs from predicted probability by {gap:+.1%}.'})

    recommendation = {
        'status': status,
        'auto_tuning_enabled': False,
        'minimum_gws_for_descriptive_review': 6,
        'minimum_gws_for_actionable_review': 12,
        'instruction': (
            'Accumulate evidence only; do not alter coefficients.' if gw_count < 6 else
            'Review biases descriptively but do not auto-change coefficients.' if gw_count < 12 else
            'Bias/drift alerts may justify a bounded coefficient review. Automatic self-mutation remains disabled.'
        ),
    }

    output = {
        'status': 'SUCCESS',
        'version': 2,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'calibration_status': status,
        'metrics': metrics,
        'gameweek_metrics': gameweek_metrics,
        'drift': drift,
        'alerts': alerts,
        'recommendation': recommendation,
        'skipped_projection_gws': skipped,
        'method_note': 'Pairs hindsight-safe pre-GW projection_history snapshots with finalized all-player FPL outcomes. Evaluates point bias/error, uncertainty coverage and minutes-probability calibration. Drift compares the latest three completed GWs with the prior three. Evidence gates are based on completed Gameweeks, not raw player-row count.',
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'calibration_status': status, 'gameweeks': gw_count, 'players': len(matched_rows), 'drift': drift.get('status'), 'alerts': len(alerts)}))


if __name__ == '__main__':
    main()
