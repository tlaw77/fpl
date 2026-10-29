const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const context = {
  window: {},
  document: {documentElement: {dataset: {}}},
  module: {exports: {}},
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('docs/active-decision-signal-stage119.js', 'utf8'), context);
const api = context.window.FPLActiveDecisionSignal;

const synthesis = {
  current_action: {action: 'TRANSFER', headline: 'A → B + C → D', transfer_count: 2},
  robustness: {
    single_step_leader: 'X → Y',
    single_step_edge_over_hold_6gw: 12.2,
    required_edge: 2,
    transfer_clears_gate: false,
    measured_leader_support_models: 1,
    required_consensus_models: 2,
    multi_transfer_clears_gate: true,
    multi_transfer_route: 'A → B + C → D',
    multi_transfer_edge_over_roll: 9.65,
    multi_transfer_required_edge: 3.5,
  },
};
const signal = api.fromSynthesis(synthesis);
assert.equal(signal.route, 'A → B + C → D');
assert.equal(signal.type, 'multi_transfer');
assert.equal(signal.edge, 9.65);
assert.equal(signal.required, 3.5);
assert.equal(signal.validationLabel, 'Adaptive-rival test');
assert.equal(signal.validationValue, 'PASS');
assert.equal(signal.gateClear, true);

const timing = api.execution({hours_to_deadline: 72, decision_synthesis: synthesis}, signal);
assert.equal(timing.label, 'PLAN 2 TRANSFERS');
assert.equal(timing.title, 'PLAN READY · WAIT TO EXECUTE');
assert.equal(timing.canExecute, false);

const rows = [
  {action: 'HOLD', active_route: 'X → Y', active_route_type: 'single_transfer_challenger', active_edge_over_hold_6gw: 12},
  {action: 'TRANSFER', active_route: 'A → B + C → D', active_route_type: 'multi_transfer', active_edge_over_hold_6gw: 9.5},
  {action: 'TRANSFER', active_route: 'A → B + C → D', active_route_type: 'multi_transfer', active_edge_over_hold_6gw: 9.65},
];
assert.equal(api.sameRouteTail(rows).length, 2);

const latest = JSON.parse(fs.readFileSync('data/latest.json', 'utf8'));
const live = api.fromSynthesis(latest.decision_synthesis);
if (live.action === 'TRANSFER') {
  assert.equal(live.gateClear, true);
  assert.equal(live.route, latest.decision_synthesis.current_action.headline);
}

console.log('active decision signal tests passed');

assert.equal(api.execution({hours_to_deadline:1,decision_synthesis:{current_action:{execution_ready:false,execution_reason:"Pending Pedro news"}}}, {action:"TRANSFER",gateClear:true}).canExecute,false);
assert.equal(api.execution({decision_synthesis:{team_news_review:{generated_at_utc:"2020-01-01T00:00:00Z"}}}, {action:"TRANSFER",gateClear:true}).label,"REFRESH TEAM NEWS");

// Completed earlier moves cannot hide a newly evaluated additional route.
const extra = {...synthesis, current_action: {...synthesis.current_action,
  completed_transfer: {event:9,route:'Pedro → Isak',source:'official'},next_transfer_hit_cost:4}};
assert.notEqual(api.execution({next_gw:9,hours_to_deadline:1,decision_synthesis:extra}, api.fromSynthesis(extra)).state,'completed');
extra.current_action.action='HOLD';extra.current_action.reason='Waiting beats the hit.';
extra.robustness={active_transfer_gate_clear:false};
const held=api.execution({next_gw:9,decision_synthesis:extra},api.fromSynthesis(extra));
assert.equal(held.state,'hold');assert.equal(held.copy,'Waiting beats the hit.');
extra.current_action.completed_transfer.source='local_execution_confirmation';
assert.equal(api.execution({next_gw:9,decision_synthesis:extra},api.fromSynthesis(extra)).state,'completed');
