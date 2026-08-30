import math


def n(value, default=0.0):
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except Exception:
        return default


def clamp(value, lo=0.0, hi=1.0):
    return max(lo, min(hi, float(value)))


def expected_minutes_profile(player, current_gw, reliability, position, availability=1.0):
    """Return a conservative probabilistic minutes profile from free FPL evidence.

    This model deliberately uses shrinkage in the opening weeks. The probabilities
    are intended to improve FPL scoring/risk simulation, not to claim exact lineup
    certainty. They obey the nesting constraints P(80+) <= P(60+) <= P(start)
    <= P(appearance).
    """
    games = max(1, int(current_gw or 1))
    starts = max(0.0, n(player.get('starts')))
    minutes = max(0.0, n(player.get('minutes')))
    availability = clamp(availability)

    start_prior = {'GKP': .88, 'DEF': .72, 'MID': .70, 'FWD': .68}.get(position, .70)
    appearance_prior = {'GKP': .91, 'DEF': .84, 'MID': .84, 'FWD': .83}.get(position, .84)
    start_mins_prior = {'GKP': 88.0, 'DEF': 76.0, 'MID': 72.0, 'FWD': 70.0}.get(position, 72.0)
    cameo_mins_prior = {'GKP': 5.0, 'DEF': 13.0, 'MID': 16.0, 'FWD': 17.0}.get(position, 15.0)
    cond60_prior = {'GKP': .98, 'DEF': .90, 'MID': .84, 'FWD': .82}.get(position, .85)
    cond80_prior = {'GKP': .94, 'DEF': .62, 'MID': .48, 'FWD': .43}.get(position, .50)

    # Evidence reaches ~0.57 in GW2, ~0.68 in GW3 and then rises gradually.
    # This learns quickly enough to identify bench roles without treating two
    # early starts as permanent lineup certainty.
    rel = clamp(reliability)
    evidence = clamp(.35 + .55 * rel, .28, .84)

    observed_start_rate = clamp(starts / games)
    observed_appearance_rate = clamp(minutes / max(1.0, games * 55.0))

    p_start = (start_prior * (1.0 - evidence) + observed_start_rate * evidence) * availability
    p_appearance = (appearance_prior * (1.0 - evidence) + observed_appearance_rate * evidence) * availability
    p_appearance = clamp(max(p_start, p_appearance))
    p_start = clamp(min(p_start, p_appearance))
    p_cameo = clamp(p_appearance - p_start)

    if starts > 0:
        # Season minutes include substitute minutes, so cap the observed starter
        # proxy and blend it with a positional prior rather than trusting it raw.
        observed_start_mins = clamp(minutes / max(starts, 1.0), 45.0, 90.0)
        start_minutes = start_mins_prior * (1.0 - evidence) + observed_start_mins * evidence
        observed_60_cond = clamp((observed_start_mins - 45.0) / 25.0)
        observed_80_cond = clamp((observed_start_mins - 65.0) / 20.0)
    else:
        start_minutes = start_mins_prior
        observed_60_cond = cond60_prior * .55
        observed_80_cond = cond80_prior * .45

    p60_cond = clamp(cond60_prior * (1.0 - evidence) + observed_60_cond * evidence)
    p80_cond = clamp(cond80_prior * (1.0 - evidence) + observed_80_cond * evidence)
    p60 = clamp(min(p_start, p_start * p60_cond))
    p80 = clamp(min(p60, p_start * p80_cond))

    expected_minutes = p_start * start_minutes + p_cameo * cameo_mins_prior
    expected_minutes = clamp(expected_minutes, 2.0, 89.0)

    if p_start >= .82 and p60 >= .72:
        band = 'NAILED'
    elif p_start >= .65:
        band = 'LIKELY_START'
    elif p_start >= .42:
        band = 'ROTATION'
    elif p_appearance >= .45:
        band = 'CAMEO_RISK'
    else:
        band = 'LOW_MINUTES'

    confidence_score = clamp(.28 + evidence * .55 + min(games, 8) * .018)
    confidence = 'HIGH' if confidence_score >= .76 else ('MEDIUM' if confidence_score >= .57 else 'LOW')

    return {
        'expected_minutes': round(expected_minutes, 1),
        'prob_appearance': round(p_appearance, 3),
        'prob_start': round(p_start, 3),
        'prob_cameo': round(p_cameo, 3),
        'prob_60_plus': round(p60, 3),
        'prob_80_plus': round(p80, 3),
        'observed_start_rate': round(observed_start_rate, 3),
        'evidence_weight': round(evidence, 3),
        'minutes_band': band,
        'confidence': confidence,
        'confidence_score': round(confidence_score, 3),
    }
