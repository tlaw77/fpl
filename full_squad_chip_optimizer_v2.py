import hashlib
import json
from datetime import datetime, timezone

import full_squad_chip_optimizer as opt

CACHE_HOURS = 4

# Production search budget: retain strong candidates plus cheap enablers, but keep
# the 30-minute ETL comfortably bounded. Exact legality and finalist rescoring stay intact.
opt.SHORTLIST_TOP = {'GKP': 12, 'DEF': 18, 'MID': 20, 'FWD': 16}
opt.CHEAP_EXTRA = 6
opt.BEAM_WIDTH = 1600
opt.FINALISTS = 60


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def signature():
    latest = load(opt.LATEST, {})
    budget = load(opt.BUDGET, {})
    squad = latest.get('current_squad_next5') or latest.get('squad_next5') or []
    payload = {
        'next_gw': latest.get('next_gw'),
        'squad': sorted((int(x.get('player_id') or 0), float(x.get('price') or 0)) for x in squad),
        'bank': latest.get('current_bank', (latest.get('me') or {}).get('bank')),
        'budget': budget.get('spendable_budget'),
        'budget_method': budget.get('budget_method'),
    }
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()[:20]


def fresh_cached(sig):
    old = load(opt.OUT, {})
    if old.get('status') != 'SUCCESS' or old.get('input_signature') != sig:
        return None
    try:
        generated = datetime.fromisoformat(str(old.get('generated_at_utc')).replace('Z', '+00:00'))
        age_h = (datetime.now(timezone.utc) - generated).total_seconds() / 3600
    except Exception:
        return None
    return old if age_h < CACHE_HOURS else None


def main():
    sig = signature()
    cached = fresh_cached(sig)
    if cached:
        print(json.dumps({'status': 'SUCCESS', 'cache': 'HIT', 'input_signature': sig, 'generated_at_utc': cached.get('generated_at_utc')}))
        return

    opt.run()
    out = load(opt.OUT, {})
    if out.get('status') != 'SUCCESS':
        raise RuntimeError('Full-squad chip optimiser did not produce SUCCESS')
    out['input_signature'] = sig
    out['cache_ttl_hours'] = CACHE_HOURS
    out['search_profile'] = {
        'beam_width': opt.BEAM_WIDTH,
        'finalists': opt.FINALISTS,
        'shortlist_top': opt.SHORTLIST_TOP,
        'cheap_extra': opt.CHEAP_EXTRA,
    }
    opt.OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({'status': 'SUCCESS', 'cache': 'MISS', 'input_signature': sig, 'wc_gain': (out.get('best_wildcard') or {}).get('incremental_expected_points_vs_current_squad'), 'best_fh_gw': (out.get('best_free_hit') or {}).get('gw')}))


if __name__ == '__main__':
    main()
