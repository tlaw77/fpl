import { describe, expect, it } from 'vitest';

import { createShellModel, isViewId, viewIds } from './model';

describe('shell model', () => {
  it('exposes the five accepted primary views in canonical order', () => {
    const model = createShellModel();

    expect(model.navigation.map(({ id }) => id)).toEqual(viewIds);
    expect(model.navigation.map(({ label }) => label)).toEqual([
      'League Intel',
      'Transfer',
      'Pick Team',
      'Squad Strategy',
      'Player Pool',
    ]);
  });

  it('defaults to League Intel without writing persistent state', () => {
    expect(createShellModel().activeView).toBe('intel');
  });

  it('rejects unknown view identifiers', () => {
    expect(isViewId('team')).toBe(true);
    expect(isViewId('unknown')).toBe(false);
  });
});
