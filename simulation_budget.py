"""Shared deadline-aware Monte Carlo iteration budgets.

Keep normal midweek refreshes efficient while spending more samples when a
FPL deadline is close and late information matters most. Decision thresholds do
not change; only Monte Carlo sampling precision changes.
"""

PROFILES = {
    'single': {'normal': 1800, 'approaching': 2400, 'deadline_day': 3200, 'final': 4500, 'locked': 1800},
    'path': {'normal': 1200, 'approaching': 1600, 'deadline_day': 2200, 'final': 3000, 'locked': 1200},
    'adaptive': {'normal': 1200, 'approaching': 1600, 'deadline_day': 2200, 'final': 2800, 'locked': 1200},
    'chip': {'normal': 1200, 'approaching': 1500, 'deadline_day': 1900, 'final': 2400, 'locked': 1200},
}


def phase(latest):
    value = str((latest.get('deadline_context') or {}).get('phase') or 'normal')
    return value if value in ('normal', 'approaching', 'deadline_day', 'final', 'locked') else 'normal'


def iterations(latest, layer):
    p = phase(latest)
    table = PROFILES.get(layer) or PROFILES['single']
    return int(table.get(p, table['normal']))


def metadata(latest, layer):
    p = phase(latest)
    return {
        'layer': layer,
        'deadline_phase': p,
        'hours_to_deadline': latest.get('hours_to_deadline'),
        'iterations': iterations(latest, layer),
        'policy': 'lighter normal-week sampling; higher precision inside 72h/24h/6h of official FPL deadline',
    }
