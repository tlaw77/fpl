const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const context = {
  window: {
    FPLCoreData: {},
    FPLActiveDecisionSignal: {
      fromSynthesis: () => ({action: 'TRANSFER', route: 'Thomas → Affengruber + Greaves → Bogle', type: 'multi_transfer', edge: 9.09, score: 100, gateClear: true}),
      execution: () => ({label: 'PLAN 2 TRANSFERS', canExecute: false}),
    },
    addEventListener() {},
  },
  document: {querySelector: () => null, addEventListener() {}, visibilityState: 'visible'},
  localStorage: {getItem: () => null, setItem() {}},
  setTimeout() {},
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('docs/monitoring-session-stage83.js', 'utf8'), context);

const result = context.window.FPLMonitoringSessionTest.changeSet(
  {leader: 'Thomas → Affengruber + Greaves → Bogle', route_type: 'multi_transfer'},
  {leader: 'Greaves → Bogle', route_type: 'single_transfer_challenger'},
);
assert.equal(result.headline, 'Recommended route changed');
assert.deepEqual(Array.from(result.items, x => x[0]), ['Previous route', 'Current plan', 'Timing']);
assert.equal(result.items[2][1], 'Wait before executing');
assert.ok(!JSON.stringify(result).includes('signal pts'));
assert.ok(!JSON.stringify(result).includes('projected pts'));

const resetTrend = context.window.FPLMonitoringSessionTest.trendHtml(
  {leader: 'Thomas → Affengruber + Greaves → Bogle', route_type: 'multi_transfer'},
  {leader: 'Greaves → Bogle', route_type: 'single_transfer_challenger', saved_at: new Date(Date.now() - 6 * 3600e3).toISOString()},
);
assert.ok(resetTrend.includes('New baseline started'));
assert.ok(resetTrend.includes('Waiting for same-route history'));
assert.ok(!resetTrend.includes('Pressure rising'));
assert.ok(!resetTrend.includes('signal pts'));

const postTransfer = context.window.FPLMonitoringSessionTest.changeSet(
  {completed: 'Thomas → Affengruber + Greaves → Bogle', leader: 'Cherki → Gakpo', route_type: 'single_transfer_challenger', next_hit: 4},
  {completed: '', leader: 'Thomas → Affengruber + Greaves → Bogle', route_type: 'multi_transfer'},
);
assert.equal(postTransfer.headline, 'Completed transfers applied');
assert.deepEqual(Array.from(postTransfer.items, x => x[0]), ['Completed route', 'Current instruction', 'Additional-move watch', 'Cost of another move']);
assert.equal(postTransfer.items[1][1], 'HOLD · no further transfer');
assert.equal(postTransfer.items[3][1], '−4 points');

const additionalWatch = context.window.FPLMonitoringSessionTest.changeSet(
  {completed: 'Thomas → Affengruber + Greaves → Bogle', leader: 'Cherki → Gakpo', route_type: 'single_transfer_challenger', next_hit: 4},
  {completed: 'Thomas → Affengruber + Greaves → Bogle', leader: 'Kinsky → Tzolakis', route_type: 'single_transfer_challenger', next_hit: 4},
);
assert.equal(additionalWatch.headline, 'Additional-move watch changed');
assert.deepEqual(Array.from(additionalWatch.items, x => x[0]), ['Completed route', 'Previous challenger', 'Current challenger', 'Instruction']);

const postTransferTrend = context.window.FPLMonitoringSessionTest.trendHtml(
  {completed: 'Thomas → Affengruber + Greaves → Bogle', leader: 'Cherki → Gakpo', route_type: 'single_transfer_challenger'},
  {completed: '', leader: 'Thomas → Affengruber + Greaves → Bogle', route_type: 'multi_transfer', saved_at: new Date().toISOString()},
);
assert.ok(postTransferTrend.includes('POST-TRANSFER WATCH'));
assert.ok(postTransferTrend.includes('Tracking additional moves only'));

console.log('monitoring session wording tests passed');
