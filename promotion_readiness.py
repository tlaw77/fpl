import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha256(path: Path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def assess(data_dir: Path):
    health_path = data_dir / 'model_health.json'
    history_dir = data_dir / 'model_health_history'
    index_path = history_dir / 'index.json'
    activation_path = history_dir / 'activation.json'
    finalized_dir = data_dir / 'history'

    required = [health_path, index_path, activation_path]
    missing_files = [str(p) for p in required if not p.exists()]
    if missing_files:
        return {
            'status': 'BLOCKED',
            'generated_at_utc': datetime.now(timezone.utc).isoformat(),
            'reason': 'Required model-health persistence artifacts are missing.',
            'missing_files': missing_files,
            'ready_to_promote': False,
        }

    health = load(health_path)
    index = load(index_path)
    activation = load(activation_path)
    activation_gw = int(activation.get('activation_gw') or 0)
    current_gw = int(health.get('current_gw') or 0)
    index_activation_gw = int(index.get('activation_gw') or 0)

    failures = []
    checks = {
        'health_success': health.get('status') == 'SUCCESS',
        'index_success': index.get('status') == 'SUCCESS',
        'activation_consistent': activation_gw > 0 and activation_gw == index_activation_gw,
        'current_gw_consistent': current_gw > 0 and current_gw == int(index.get('current_gw') or 0),
        'automatic_coefficient_mutation_disabled': (
            (health.get('continuous_tuning') or {}).get('auto_coefficient_mutation') is False
            and index.get('auto_coefficient_mutation') is False
        ),
        'no_missing_required_gameweeks': index.get('missing_required_gameweeks') == [],
    }

    for name, ok in checks.items():
        if not ok:
            failures.append(name)

    evidence_gws = sorted({int(gw) for gw in index.get('finalized_health_gameweeks', [])})
    verified_gws = []
    evidence_details = []

    for gw in evidence_gws:
        source = history_dir / f'gw{gw}.json'
        target = finalized_dir / f'gw{gw}'
        archived = target / 'model_health.json'
        manifest_path = target / 'manifest.json'
        detail = {'gw': gw, 'verified': False}

        if gw < activation_gw:
            detail['failure'] = 'pre_activation_evidence_claimed'
            failures.append(f'gw{gw}:pre_activation_evidence_claimed')
            evidence_details.append(detail)
            continue
        if not source.exists() or not archived.exists() or not manifest_path.exists():
            detail['failure'] = 'required_evidence_file_missing'
            failures.append(f'gw{gw}:required_evidence_file_missing')
            evidence_details.append(detail)
            continue

        source_payload = load(source)
        archived_payload = load(archived)
        manifest = load(manifest_path)
        manifest_entry = next(
            (entry for entry in manifest.get('files', []) if entry.get('name') == 'model_health.json'),
            None,
        )
        source_hash = sha256(source)
        archived_hash = sha256(archived)
        expected_hash = (manifest_entry or {}).get('sha256')

        gw_checks = {
            'source_gw_matches': int(source_payload.get('current_gw') or 0) == gw,
            'archive_gw_matches': int(archived_payload.get('current_gw') or 0) == gw,
            'source_archive_hash_match': source_hash == archived_hash,
            'manifest_contains_health': manifest_entry is not None,
            'manifest_hash_match': expected_hash == archived_hash,
            'archive_mutation_disabled': (
                (archived_payload.get('continuous_tuning') or {}).get('auto_coefficient_mutation') is False
            ),
        }
        failed_gw_checks = [name for name, ok in gw_checks.items() if not ok]
        detail.update({
            'checks': gw_checks,
            'source_sha256': source_hash,
            'archived_sha256': archived_hash,
            'manifest_sha256': expected_hash,
        })
        if failed_gw_checks:
            detail['failure'] = failed_gw_checks
            failures.extend(f'gw{gw}:{name}' for name in failed_gw_checks)
        else:
            detail['verified'] = True
            verified_gws.append(gw)
        evidence_details.append(detail)

    if failures:
        status = 'BLOCKED'
        reason = 'Promotion safety checks failed.'
        ready = False
    elif not evidence_gws:
        status = 'WAITING_EVIDENCE'
        reason = 'Engineering is complete; waiting for the first finalized post-activation Gameweek rollover.'
        ready = False
    elif len(verified_gws) != len(evidence_gws):
        status = 'BLOCKED'
        reason = 'Not every claimed finalized health snapshot could be verified.'
        ready = False
    else:
        status = 'READY'
        reason = 'At least one post-activation rollover has immutable, hash-matched model-health evidence.'
        ready = True

    return {
        'status': status,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'reason': reason,
        'ready_to_promote': ready,
        'activation_gw': activation_gw,
        'current_gw': current_gw,
        'persistence_status': index.get('persistence_status'),
        'evidence_gameweeks': evidence_gws,
        'verified_gameweeks': verified_gws,
        'checks': checks,
        'failures': failures,
        'evidence': evidence_details,
        'policy': {
            'minimum_verified_post_activation_rollovers': 1,
            'hindsight_reconstruction_allowed': False,
            'auto_coefficient_mutation_allowed': False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description='Assess FPL decision-engine promotion readiness.')
    parser.add_argument('--data-dir', default='data')
    parser.add_argument('--require-ready', action='store_true')
    parser.add_argument('--output', default=None)
    args = parser.parse_args()

    result = assess(Path(args.data_dir))
    output = Path(args.output) if args.output else Path(args.data_dir) / 'promotion_readiness.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({
        'status': result['status'],
        'ready_to_promote': result['ready_to_promote'],
        'activation_gw': result.get('activation_gw'),
        'verified_gameweeks': result.get('verified_gameweeks', []),
    }))

    if result['status'] == 'BLOCKED':
        raise SystemExit(1)
    if args.require_ready and not result['ready_to_promote']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
