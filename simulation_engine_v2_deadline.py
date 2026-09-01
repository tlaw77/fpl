"""Run the league-aware single-step simulation using the production deadline budget.

This wrapper keeps the richer feature simulation implementation isolated while
preserving production's deadline-aware iteration policy.  The underlying engine
reads simulation_engine.ITERATIONS, so setting it before run() avoids duplicating
or forking the simulation logic.
"""
import json
from pathlib import Path

import simulation_budget as sb
import simulation_engine as s
import simulation_engine_v2 as core

OUT = Path('data/simulation.json')


def run():
    latest = s.load_json(s.LATEST, {})
    iterations = int(sb.iterations(latest, 'single'))
    policy = sb.metadata(latest, 'single')
    if iterations < 1000:
        raise RuntimeError(f'Unsafe single-step iteration budget: {iterations}')

    s.ITERATIONS = iterations
    core.run()

    data = json.loads(OUT.read_text())
    data['iterations'] = iterations
    data['iteration_policy'] = policy
    data['engine_version'] = max(9, int(data.get('engine_version') or 0))
    data['deadline_aware_iterations'] = True
    data['method_note'] = (
        str(data.get('method_note') or '').rstrip() +
        ' Monte Carlo iteration count is deadline-aware: lighter away from the deadline and higher precision as the official FPL deadline approaches; strategic thresholds are unchanged.'
    ).strip()
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({
        'status': 'SUCCESS',
        'engine_version': data['engine_version'],
        'iterations': iterations,
        'deadline_phase': policy.get('deadline_phase'),
        'league_posture': (data.get('league_objective') or {}).get('posture'),
        'captain_mode': (data.get('captaincy_strategy') or {}).get('recommended_mode'),
    }))


if __name__ == '__main__':
    run()
