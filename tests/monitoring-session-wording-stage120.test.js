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

console.log('monitoring session wording tests passed');
