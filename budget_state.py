import json
from datetime import datetime, timezone
from pathlib import Path

import current_squad as cs

LATEST = Path('data/latest.json')
OUT = Path('data/budget_state.json')


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def main():
    data = json.loads(LATEST.read_text())
    next_gw = int(data.get('next_gw') or 0)
    entry_id = int((data.get('me') or {}).get('entry_id') or cs.MY_ENTRY_ID)
    current = data.get('current_squad_next5') or data.get('squad_next5') or []
    bank = n(data.get('current_bank', (data.get('me') or {}).get('bank')))

    raw_pick_keys = []
    exact_selling = {}
    if next_gw > 1:
        try:
            picks = cs.get_json(f'{cs.BASE}/entry/{entry_id}/event/{next_gw-1}/picks/')
            rows = picks.get('picks') or []
            if rows:
                raw_pick_keys = sorted(rows[0].keys())
            for row in rows:
                if row.get('selling_price') is not None:
                    exact_selling[int(row['element'])] = n(row['selling_price']) / 10
        except Exception:
            pass

    market_value = round(sum(n(p.get('price')) for p in current), 2)
    exact_available = len(exact_selling) == 15
    if exact_available:
        squad_liquidation = round(sum(exact_selling.values()), 2)
        method = 'public_pick_selling_price'
        confidence = 'exact'
    else:
        # Public FPL picks usually do not expose my-team selling values. Use current market
        # value as a transparent planning proxy; do not promote WC/FH solely on this budget.
        squad_liquidation = market_value
        method = 'current_market_value_proxy'
        confidence = 'estimated'

    spendable = round(squad_liquidation + bank, 2)
    output = {
        'status': 'SUCCESS',
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'entry_id': entry_id,
        'next_gw': next_gw,
        'bank': round(bank, 2),
        'current_squad_market_value': market_value,
        'estimated_squad_liquidation_value': squad_liquidation,
        'spendable_budget': spendable,
        'budget_method': method,
        'budget_confidence': confidence,
        'public_pick_keys': raw_pick_keys,
        'exact_selling_prices_found': len(exact_selling),
        'method_note': 'Wildcard and Free Hit squad searches require a spendable-budget constraint. Exact public selling values are used when exposed; otherwise current market value plus bank is retained only as a planning proxy and the chip gate must treat the result as provisional.',
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(output))


if __name__ == '__main__':
    main()
