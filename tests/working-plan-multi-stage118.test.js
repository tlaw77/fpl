const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const plan = {moves: [
  {out: {player_id: 1, player: 'Maguire'}, in: {player_id: 101, player: 'Affengruber'}},
  {out: {player_id: 2, player: 'Greaves'}, in: {player_id: 102, player: 'Bogle'}},
]};
const context = {
  window: {},
  localStorage: {getItem: () => JSON.stringify(plan)},
  document: {readyState: 'loading', addEventListener() {}, documentElement: {dataset: {}}},
  MutationObserver: function MutationObserver() { this.observe = () => {}; },
  setTimeout,
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('docs/working-plan-multi-stage118.js', 'utf8'), context);

const base = [
  {player_id: 1, player: 'Maguire', position: 'DEF', slot: 3, starter: true},
  {player_id: 2, player: 'Greaves', position: 'DEF', slot: 13, starter: false},
  {player_id: 3, player: 'Keeper', position: 'GKP', slot: 1, starter: true},
];
const catalog = [
  {player_id: 101, player: 'Affengruber', position: 'DEF', price: 4.5},
  {player_id: 102, player: 'Bogle', position: 'DEF', price: 4.7},
];
const api = context.window.FPLWorkingPlan;
const result = api.apply(base, catalog, plan);

assert.deepEqual(Array.from(result, x => x.player), ['Keeper', 'Affengruber', 'Bogle']);
assert.equal(result.find(x => x.player === 'Affengruber').slot, 3);
assert.equal(result.find(x => x.player === 'Bogle').slot, 13);
assert.equal(api.label(plan), 'Maguire → Affengruber + Greaves → Bogle');

const invalid = {moves: [...plan.moves, {
  out: {player_id: 999, player: 'Missing'},
  in: {player_id: 103, player: 'Other'},
}]};
assert.deepEqual(Array.from(api.apply(base, catalog, invalid), x => x.player), ['Maguire', 'Greaves', 'Keeper']);

console.log('working-plan multi-transfer tests passed');
