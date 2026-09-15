const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const latest = JSON.parse(fs.readFileSync('data/latest.json', 'utf8'));
const market = JSON.parse(fs.readFileSync('data/market.json', 'utf8'));
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
const risk = context.window.FPLTransferMarketWatchTest.routeRisk(latest, market);

assert.equal(risk.active, true);
assert.equal(risk.route, 'Thomas → Affengruber + Greaves → Bogle');
assert.equal(risk.label, 'WATCH TONIGHT');
assert.equal(risk.buffer, 0.4);
assert.equal(risk.watchedSwing, 0.3);
assert.equal(risk.after, 0.1);
assert.ok(risk.copy.includes('No panic'));
assert.ok(risk.copy.includes('Bogle'));
assert.ok(risk.copy.includes('Thomas and Greaves'));

console.log('transfer market watch tests passed');
