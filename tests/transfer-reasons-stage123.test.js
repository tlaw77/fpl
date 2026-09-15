const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const pool = JSON.parse(fs.readFileSync('data/player_pool.json', 'utf8'));
const context = {
  window: {},
  localStorage: {getItem: () => null, setItem() {}},
  document: {readyState: 'loading', addEventListener() {}, documentElement: {dataset: {}}, querySelector: () => null},
  setTimeout() {},
  fetch: async () => ({ok: true, json: async () => pool}),
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('docs/free-transfer-portfolio-stage117.js', 'utf8'), context);
const api = context.window.FPLFreeTransferPortfolioTest;

const stability = api.moveReason({out_id: 173, in_id: 650}, pool);
assert.equal(stability.headline, 'Better medium-term outlook');
assert.ok(stability.main.includes('returns per appearance'));
assert.ok(stability.main.includes('availability'));
assert.ok(stability.tradeoff.includes('not a one-week fixture chase'));

const ceiling = api.moveReason({out_id: 306, in_id: 330}, pool);
assert.equal(ceiling.headline, 'Clearer six-week case');
assert.ok(ceiling.main.includes('recent output is much stronger'));
assert.ok(ceiling.tradeoff.includes('fixtures are tougher'));
assert.ok(ceiling.tradeoff.includes('£0.5m'));

assert.equal(api.actionTransfers({action: 'TRANSFER', transfers: [{route: 'A → B'}, {route: 'C → D'}]}).length, 2);
console.log('transfer reasons tests passed');
