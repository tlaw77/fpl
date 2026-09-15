const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const market = JSON.parse(fs.readFileSync('data/market.json', 'utf8'));
const pool = JSON.parse(fs.readFileSync('data/player_pool.json', 'utf8'));
const latest = {
  current_bank: 1.4,
  squad: [{player_id: 173, price: 4.0}, {player_id: 306, price: 4.0}],
  decision_synthesis: {
    current_action: {action: 'TRANSFER', headline: 'Thomas → Affengruber + Greaves → Bogle'},
    transfer_options: [{
      key: 'multiple_now',
      available: true,
      recommended_path: true,
      first_action: {
        action: 'TRANSFER',
        route: 'Thomas → Affengruber + Greaves → Bogle',
        transfers: [
          {out_id: 173, in_id: 650, route: 'Thomas → Affengruber'},
          {out_id: 306, in_id: 330, route: 'Greaves → Bogle'},
        ],
      },
    }],
  },
};
const context = {
  window: {
    FPLCoreData: latest,
    FPLActiveDecisionSignal: {fromSynthesis: () => ({action: 'TRANSFER', gateClear: true})},
    addEventListener() {},
  },
  document: {querySelector: () => null, addEventListener() {}, readyState: 'loading'},
  setTimeout() {},
  fetch: async () => ({ok: true, json: async () => market}),
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('docs/transfer-market-watch-stage94.js', 'utf8'), context);
const risk = context.window.FPLTransferMarketWatchTest.routeRisk(latest, market, pool);

assert.equal(risk.active, true);
assert.equal(risk.route, 'Thomas → Affengruber + Greaves → Bogle');
assert.equal(risk.label, 'ACT BEFORE UPDATE');
assert.equal(risk.verdict, 'EXECUTE IF FPL PRICES MATCH');
assert.equal(risk.buffer, 0.4);
assert.equal(risk.watchedSwing, 0.3);
assert.equal(risk.after, 0.1);
assert.ok(risk.copy.includes('execute before the next update'));
assert.ok(risk.copy.includes('Bogle'));
assert.ok(risk.copy.includes('Thomas and Greaves'));
assert.deepEqual(Array.from(risk.strongIncoming), ['Bogle']);
assert.deepEqual(Array.from(risk.blockers), []);

console.log('transfer market watch tests passed');
