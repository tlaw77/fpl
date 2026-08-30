import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

DATA = Path('data')
CURRENT = DATA / 'model_health.json'
HEALTH_HISTORY = DATA / 'model_health_history'
ACTIVATION = HEALTH_HISTORY / 'activation.json'
INDEX = HEALTH_HISTORY / 'index.json'
FINALIZED_HISTORY = DATA / 'history'


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def file_meta(path):
    return {'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha256(path)}


def validate_health(payload, expected_gw=None):
    if payload.get('status') != 'SUCCESS':
        raise RuntimeError('Model-health snapshot is not successful')
    if expected_gw is not None and int(payload.get('current_gw') or 0) != int(expected_gw):
        raise RuntimeError(f"Model-health snapshot GW mismatch: expected {expected_gw}, got {payload.get('current_gw')}")
    tuning = payload.get('continuous_tuning') or {}
    if tuning.get('auto_coefficient_mutation') is not False:
        raise RuntimeError('Automatic coefficient mutation safeguard is not locked off')


def ensure_activation(current_gw):
    HEALTH_HISTORY.mkdir(parents=True, exist_ok=True)
    if ACTIVATION.exists():
        activation = load(ACTIVATION)
        activation_gw = int(activation.get('activation_gw') or 0)
        if activation_gw <= 0:
            raise RuntimeError('Invalid model-health persistence activation marker')
        return activation
    activation = {
        'version': 1,
        'activation_gw': int(current_gw),
        'activated_at_utc': datetime.now(timezone.utc).isoformat(),
        'principle': 'Only Gameweeks at or after activation are required to have finalized model-health evidence; older archives are legacy history rather than persistence failures.',
    }
    write_json(ACTIVATION, activation)
    return activation


def amend_manifest(target, health_path):
    manifest_path = target / 'manifest.json'
    manifest = load(manifest_path)
    files = [x for x in manifest.get('files', []) if x.get('name') != 'model_health.json']
    files.append(file_meta(health_path))
    manifest['files'] = sorted(files, key=lambda x: x.get('name', ''))
    manifest['model_health_persisted_at_utc'] = datetime.now(timezone.utc).isoformat()
    write_json(manifest_path, manifest)


def persist():
    if not CURRENT.exists():
        raise RuntimeError('data/model_health.json is missing; run model_health.py first')
    current = load(CURRENT)
    validate_health(current)
    current_gw = int(current.get('current_gw') or 0)
    if current_gw <= 0:
        raise RuntimeError('Current model-health snapshot has no valid Gameweek')

    HEALTH_HISTORY.mkdir(parents=True, exist_ok=True)
    current_history = HEALTH_HISTORY / f'gw{current_gw}.json'
    if not current_history.exists():
        shutil.copy2(CURRENT, current_history)
    validate_health(load(current_history), expected_gw=current_gw)

    activation = ensure_activation(current_gw)
    activation_gw = int(activation['activation_gw'])
    persisted = []
    legacy = []
    missing_required = []

    for target in sorted(FINALIZED_HISTORY.glob('gw*'), key=lambda p: int(p.name[2:]) if p.name[2:].isdigit() else 999):
        if not target.name[2:].isdigit() or not (target / 'manifest.json').exists():
            continue
        gw = int(target.name[2:])
        source = HEALTH_HISTORY / f'gw{gw}.json'
        if gw < activation_gw:
            legacy.append(gw)
            continue
        if not source.exists():
            missing_required.append(gw)
            continue
        payload = load(source)
        validate_health(payload, expected_gw=gw)
        dest = target / 'model_health.json'
        if not dest.exists() or sha256(dest) != sha256(source):
            shutil.copy2(source, dest)
        amend_manifest(target, dest)
        persisted.append(gw)

    evidence_gws = sorted(set(persisted))
    if missing_required:
        persistence_status = 'DEGRADED'
    elif evidence_gws:
        persistence_status = 'HEALTHY'
    else:
        persistence_status = 'LEARNING'

    index = {
        'status': 'SUCCESS',
        'version': 1,
        'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'activation_gw': activation_gw,
        'current_gw': current_gw,
        'persistence_status': persistence_status,
        'finalized_health_gameweeks': evidence_gws,
        'longitudinal_evidence_gameweeks': len(evidence_gws),
        'legacy_finalized_gameweeks': sorted(set(legacy)),
        'missing_required_gameweeks': sorted(set(missing_required)),
        'auto_coefficient_mutation': False,
        'method_note': 'Persists the final in-Gameweek health belief into the immutable finalized-Gameweek archive. Pre-activation archives are explicitly treated as legacy rather than reconstructed with hindsight.',
    }
    write_json(INDEX, index)
    return index


def main():
    result = persist()
    if result['missing_required_gameweeks']:
        raise RuntimeError(f"Missing required finalized model-health snapshots: {result['missing_required_gameweeks']}")
    print(json.dumps({
        'status': result['status'],
        'persistence_status': result['persistence_status'],
        'activation_gw': result['activation_gw'],
        'evidence_gameweeks': result['longitudinal_evidence_gameweeks'],
    }))


if __name__ == '__main__':
    main()
