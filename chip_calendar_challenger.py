import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

CHIP = Path('data/chip_path_simulation.json')
CAL = Path('data/fixture_calendar_intelligence.json')
OUT = Path('data/chip_calendar_challenger.json')


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def main():
    chip = load(CHIP, {})
    cal = load(CAL, {})
    if chip.get('status') != 'SUCCESS' or cal.get('status') != 'SUCCESS':
        raise RuntimeError('Chip simulation or calendar intelligence unavailable')

    preservation = max(0.0, min(100.0, n(cal.get('chip_preservation_score'))))
    confirmed = cal.get('confirmed_doubles') or []
    possible = cal.get('potential_dgw_windows') or []
    future_windows = sorted({int(x.get('gw') or 0) for x in confirmed + possible if int(x.get('gw') or 0) > 0})
    confirmed_gws = {int(x.get('gw') or 0) for x in confirmed}

    scenarios = []
    for source in chip.get('scenarios') or []:
        row = deepcopy(source)
        chip_name = row.get('chip')
        gw = int(row.get('chip_gw') or 0)
        penalty = 0.0
        reason = 'No chip used.'
        if chip_name in ('Triple Captain', 'Bench Boost') and gw:
            later = [x for x in future_windows if x > gw]
            if gw in confirmed_gws:
                reason = 'Current chip window is already a confirmed Double Gameweek; no calendar preservation penalty.'
            elif later:
                # Maximum 1.6 utility points. This is deliberately smaller than the
                # normal difference between a genuinely exceptional and average chip window.
                scale = 1.0 if chip_name == 'Triple Captain' else .85
                penalty = min(1.6, preservation / 100.0 * 1.6 * scale)
                reason = f'Future DGW/blank optionality remains unresolved; preserving {chip_name} retains calendar option value.'
            else:
                reason = 'No stronger unresolved future calendar window is visible in the current horizon.'
        row['calendar_preservation_penalty'] = round(penalty, 3)
        row['calendar_adjusted_utility'] = round(n(row.get('utility_score')) - penalty, 3)
        row['calendar_reason'] = reason
        scenarios.append(row)

    scenarios.sort(key=lambda x: x.get('calendar_adjusted_utility', -999), reverse=True)
    best_tc = max((x for x in scenarios if x.get('chip') == 'Triple Captain'), key=lambda x: x.get('calendar_adjusted_utility', -999), default=None)
    best_bb = max((x for x in scenarios if x.get('chip') == 'Bench Boost'), key=lambda x: x.get('calendar_adjusted_utility', -999), default=None)

    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'version': 1,
        'challenger_only': True,
        'calendar_preservation_score': round(preservation),
        'future_calendar_windows': future_windows,
        'authoritative_chip_recommendation': chip.get('recommendation'),
        'calendar_adjusted_recommendation': scenarios[0] if scenarios else None,
        'best_calendar_adjusted_tc': best_tc,
        'best_calendar_adjusted_bb': best_bb,
        'scenarios': scenarios[:30],
        'promotion_rule': 'Do not override the authoritative chip model until calendar probabilities and historical priors have been validated across multiple gameweeks.',
        'method_note': 'Calendar intelligence contributes only a bounded opportunity-cost penalty for spending TC/BB before unresolved future DGW/blank windows. It never invents expected points for an unconfirmed fixture. Confirmed DGWs are scored by the shared projection model itself.',
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'preservation': round(preservation), 'authoritative': (chip.get('recommendation') or {}).get('chip'), 'challenger': (output.get('calendar_adjusted_recommendation') or {}).get('chip')}))


if __name__ == '__main__':
    main()
