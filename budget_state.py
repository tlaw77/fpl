import json
from datetime import datetime, timezone
from pathlib import Path

import current_squad as cs

LATEST = Path('data/latest.json')
OUT = Path('data/budget_state.json')
GW1_ARCHIVE = Path('data/history/gw1/dashboard_snapshot.json')


def n(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def selling_price(current_price, purchase_price):
    """Reconstruct the FPL selling price from purchase and current price.

    Prices are converted to integer tenths first so the profit-share rule is applied
    without floating-point ambiguity. If a player rose, the manager receives half the
    profit rounded down to the nearest 0.1m; price falls are passed through in full.
    """
    cur = int(round(n(current_price) * 10))
    buy = int(round(n(purchase_price) * 10))
    if cur > buy:
        sell = buy + (cur - buy) // 2
    else:
        sell = cur
    return sell / 10


def purchase_ledger(entry_id, current_ids):
    """Build the best available purchase-price ledger for the current squad.

    Initial players are seeded from the immutable GW1 archive. Every public transfer
    then removes the outgoing player and records the incoming transaction cost. A
    current player missing from both sources (for example a user-declared transfer
    waiting for the public endpoint) is filled later from its current acquisition price
    and explicitly marked as a fallback basis.
    """
    ledger = {}
    basis = {}
    archive = load(GW1_ARCHIVE, {})
    for p in archive.get('squad') or archive.get('squad_next5') or []:
        pid = int(p.get('player_id') or 0)
        if pid:
            ledger[pid] = n(p.get('price'))
            basis[pid] = 'gw1_archive'

    transfers = []
    try:
        transfers = cs.get_json(f'{cs.BASE}/entry/{entry_id}/transfers/') or []
    except Exception:
        transfers = []

    for t in sorted(transfers, key=lambda x: (int(x.get('event') or 0), x.get('time') or '')):
        out_id = int(t.get('element_out') or 0)
        in_id = int(t.get('element_in') or 0)
        if out_id:
            ledger.pop(out_id, None)
            basis.pop(out_id, None)
        if in_id and t.get('element_in_cost') is not None:
            ledger[in_id] = n(t.get('element_in_cost')) / 10
            basis[in_id] = 'transfer_history'

    # Only expose currently-held ledger entries; historic players are irrelevant to the
    # spendable-budget calculation and would make coverage metrics confusing.
    ledger = {pid: price for pid, price in ledger.items() if pid in current_ids}
    basis = {pid: src for pid, src in basis.items() if pid in current_ids}
    return ledger, basis, transfers


def main():
    data = json.loads(LATEST.read_text())
    next_gw = int(data.get('next_gw') or 0)
    entry_id = int((data.get('me') or {}).get('entry_id') or getattr(cs, 'ENTRY_ID', 5332809))
    current = data.get('current_squad_next5') or data.get('squad_next5') or []
    bank = n(data.get('current_bank', (data.get('me') or {}).get('bank')))
    current_ids = {int(p.get('player_id') or 0) for p in current if p.get('player_id')}

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
    exact_available = len(exact_selling) == len(current) == 15
    purchase_prices, purchase_basis, transfers = purchase_ledger(entry_id, current_ids)

    reconstructed = {}
    fallback_ids = []
    for p in current:
        pid = int(p.get('player_id') or 0)
        if not pid:
            continue
        current_price = n(p.get('price'))
        purchase = purchase_prices.get(pid)
        if purchase is None:
            # Most commonly this is a user-declared transfer that has not appeared in the
            # public transaction endpoint yet. Treat current price as acquisition price;
            # that is conservative for a new purchase and remains auditable in the output.
            purchase = current_price
            purchase_prices[pid] = purchase
            purchase_basis[pid] = 'current_price_pending_history'
            fallback_ids.append(pid)
        reconstructed[pid] = selling_price(current_price, purchase)

    reconstructed_available = len(reconstructed) == len(current) == 15 and GW1_ARCHIVE.exists()

    if exact_available:
        squad_liquidation = round(sum(exact_selling.values()), 2)
        method = 'public_pick_selling_price'
        confidence = 'exact'
        sell_map = exact_selling
    elif reconstructed_available:
        squad_liquidation = round(sum(reconstructed.values()), 2)
        method = 'purchase_ledger_fpl_sell_rule'
        confidence = 'reconstructed'
        sell_map = reconstructed
    else:
        squad_liquidation = market_value
        method = 'current_market_value_proxy'
        confidence = 'estimated'
        sell_map = {int(p.get('player_id') or 0): n(p.get('price')) for p in current if p.get('player_id')}

    spendable = round(squad_liquidation + bank, 2)
    rows = []
    for p in current:
        pid = int(p.get('player_id') or 0)
        rows.append({
            'player_id': pid,
            'player': p.get('player'),
            'current_price': round(n(p.get('price')), 1),
            'purchase_price': round(n(purchase_prices.get(pid, p.get('price'))), 1),
            'selling_price': round(n(sell_map.get(pid, p.get('price'))), 1),
            'purchase_basis': purchase_basis.get(pid, 'unknown'),
        })

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
        'reconstructed_selling_prices_found': len(reconstructed),
        'purchase_ledger_coverage': len(purchase_prices),
        'pending_history_player_ids': fallback_ids,
        'public_transfer_count': len(transfers),
        'players': rows,
        'method_note': (
            'Wildcard and Free Hit searches use the best available spendable budget. '
            'Exact public selling values are preferred. Otherwise purchase prices are '
            'reconstructed from the archived GW1 squad plus public transfer costs and the '
            'FPL half-profit selling rule. Any newly declared transfer not yet visible in '
            'public history uses current price as its temporary acquisition basis and is '
            'listed explicitly. Only if reconstruction is unavailable does the engine fall '
            'back to current market value.'
        ),
    }
    OUT.write_text(json.dumps(output, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({
        'status': output['status'],
        'budget_confidence': confidence,
        'spendable_budget': spendable,
        'reconstructed': len(reconstructed),
        'pending_history': len(fallback_ids),
    }))


if __name__ == '__main__':
    main()
