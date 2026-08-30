import hashlib
import json
from datetime import datetime, timezone

import full_squad_chip_optimizer as opt

# Base cache life is deliberately long midweek. It contracts automatically as
# the official FPL deadline approaches so expensive full-squad searches become
# more responsive when late news and price changes matter most.
DEFAULT_CACHE_HOURS = 6

# Production search profile. Exact legality and final XI/captain rescoring remain
# unchanged; this only limits how many partial squad states are carried forward.
opt.SHORTLIST_TOP = {'GKP': 10, 'DEF': 16, 'MID': 18, 'FWD': 14}
opt.CHEAP_EXTRA = 5
opt.BEAM_WIDTH = 600
opt.FINALISTS = 30


def load(path, default):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def q(v, step=.25):
    try:
        x = float(v)
        return round(x / step) * step
    except Exception:
        return None


def cache_policy(latest):
    hours = latest.get('hours_to_deadline')
    try:
        hours = float(hours)
    except Exception:
        hours = None
    phase = str((latest.get('deadline_context') or {}).get('phase') or 'unknown')
    if hours is None:
        ttl = DEFAULT_CACHE_HOURS
    elif hours <= 6:
        ttl = .5
    elif hours <= 24:
        ttl = 1
    elif hours <= 72:
        ttl = 2
    else:
        ttl = DEFAULT_CACHE_HOURS
    return {'ttl_hours': ttl, 'phase': phase, 'hours_to_deadline': hours}


def model_fingerprint():
    """Quantized fingerprint of football inputs used by the full-squad search.

    This intentionally ignores tiny refresh-to-refresh numerical noise while
    invalidating the deep cache when a relevant player's model strength,
    availability, price or schedule-risk class moves materially.
    """
    pool = load(opt.POOL, {})
    rows = pool.get('players') or []
    packed = []
    for x in rows:
        pid = int(x.get('player_id') or 0)
        if not pid:
            continue
        packed.append((
            pid,
            q(x.get('six_gw_score'), .5),
            q(x.get('adjusted_availability', x.get('availability')), .05),
            q(x.get('price'), .1),
            str(x.get('schedule_risk') or ''),
        ))
    packed.sort()
    raw = json.dumps(packed, separators=(',', ':'), ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def signature_payload():
    latest = load(opt.LATEST, {})
    budget = load(opt.BUDGET, {})
    squad = latest.get('current_squad_next5') or latest.get('squad_next5') or []
    return {
        'next_gw': latest.get('next_gw'),
        'squad': sorted((int(x.get('player_id') or 0), float(x.get('price') or 0)) for x in squad),
        'bank': latest.get('current_bank', (latest.get('me') or {}).get('bank')),
        'budget': budget.get('spendable_budget'),
        'budget_method': budget.get('budget_method'),
        'model_fingerprint': model_fingerprint(),
        'profile': {'beam': opt.BEAM_WIDTH, 'shortlist': opt.SHORTLIST_TOP, 'cheap': opt.CHEAP_EXTRA},
    }


def signature():
    payload = signature_payload()
    raw = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(raw).hexdigest()[:20], payload


def fresh_cached(sig, policy):
    old = load(opt.OUT, {})
    if old.get('status') != 'SUCCESS' or old.get('input_signature') != sig:
        return None
    try:
        generated = datetime.fromisoformat(str(old.get('generated_at_utc')).replace('Z', '+00:00'))
        age_h = (datetime.now(timezone.utc) - generated).total_seconds() / 3600
    except Exception:
        return None
    return old if age_h < float(policy['ttl_hours']) else None


def stamp_cache_state(out, state, sig, payload, policy):
    out['input_signature'] = sig
    out['model_fingerprint'] = payload.get('model_fingerprint')
    out['cache_ttl_hours'] = policy['ttl_hours']
    out['cache_state'] = state
    out['cache_last_checked_at_utc'] = datetime.now(timezone.utc).isoformat()
    out['deadline_refresh_policy'] = {
        'phase': policy['phase'],
        'hours_to_deadline': policy['hours_to_deadline'],
        'ttl_hours': policy['ttl_hours'],
        'rule': '6h normal; 2h inside 72h; 1h inside 24h; 30m inside 6h',
    }
    out['search_profile'] = {
        'beam_width': opt.BEAM_WIDTH,
        'finalists': opt.FINALISTS,
        'shortlist_top': opt.SHORTLIST_TOP,
        'cheap_extra': opt.CHEAP_EXTRA,
    }
    opt.OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + '\n')


def main():
    latest = load(opt.LATEST, {})
    policy = cache_policy(latest)
    sig, payload = signature()
    cached = fresh_cached(sig, policy)
    if cached:
        stamp_cache_state(cached, 'HIT', sig, payload, policy)
        print(json.dumps({'status': 'SUCCESS', 'cache': 'HIT', 'cache_ttl_hours': policy['ttl_hours'], 'deadline_phase': policy['phase'], 'input_signature': sig, 'model_fingerprint': payload.get('model_fingerprint'), 'generated_at_utc': cached.get('generated_at_utc')}))
        return

    opt.run()
    out = load(opt.OUT, {})
    if out.get('status') != 'SUCCESS':
        raise RuntimeError('Full-squad chip optimiser did not produce SUCCESS')
    stamp_cache_state(out, 'MISS', sig, payload, policy)
    print(json.dumps({'status': 'SUCCESS', 'cache': 'MISS', 'cache_ttl_hours': policy['ttl_hours'], 'deadline_phase': policy['phase'], 'input_signature': sig, 'model_fingerprint': payload.get('model_fingerprint'), 'wc_gain': (out.get('best_wildcard') or {}).get('incremental_expected_points_vs_current_squad'), 'best_fh_gw': (out.get('best_free_hit') or {}).get('gw')}))


if __name__ == '__main__':
    main()
