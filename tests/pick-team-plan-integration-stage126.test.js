const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const selected = {moves: [{
  out: {player_id: 94, player: 'Schade'},
  in: {player_id: 101, player: 'Henderson'},
}]};
const context = {
  window: {
    addEventListener() {},
    FPLWorkingPlan: {
      pending: () => true,
      apply(base, catalog, plan) {
        const out = new Set(plan.moves.map(move => move.out.player_id));
        return base.filter(player => !out.has(player.player_id)).concat(
          plan.moves.map(move => catalog.find(player => player.player_id === move.in.player_id)),
        );
      },
    },
  },
  localStorage: {getItem: () => JSON.stringify(selected)},
  document: {readyState: 'loading', addEventListener() {}, querySelector: () => null, documentElement: {dataset: {}}},
  setTimeout() {},
  fetch() {},
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('docs/pick-team-authoritative-stage99.js', 'utf8'), context);

const base = Array.from({length: 15}, (_, i) => ({player_id: i === 7 ? 94 : i + 1, player: i === 7 ? 'Schade' : `Player ${i + 1}`}));
const pool = [{player_id: 101, player: 'Henderson'}];
const result = context.window.FPLPickTeamAuthoritativeTest.effectiveSquad(base, pool, selected);

assert.equal(result.length, 15, 'selected transfer must preserve a 15-player squad');
assert.ok(result.some(player => player.player === 'Henderson'), 'incoming player should be present');
assert.ok(!result.some(player => player.player === 'Schade'), 'outgoing player should be removed');

console.log('pick-team working-plan integration tests passed');
