const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const saved = {};
const context = {
  window: {dispatchEvent() {}},
  localStorage: {
    getItem: key => saved[key] || null,
    setItem: (key, value) => { saved[key] = value; },
  },
  document: {readyState: 'loading', addEventListener() {}, documentElement: {dataset: {}}, querySelector: () => null},
  CustomEvent: function CustomEvent(type, init) { this.type = type; this.detail = init?.detail; },
  setTimeout() {},
  fetch: async () => ({ok: false}),
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('docs/free-transfer-portfolio-stage117.js', 'utf8'), context);

const button = {textContent: '', dataset: {}, setAttribute(name, value) {this[name] = value;}};
const option = {key: 'one_now', actions: [], first_action: {action: 'TRANSFER', route: 'Schade → Henderson', out_id: 94, in_id: 101}};
const api = context.window.FPLFreeTransferPortfolioTest;

assert.equal(api.save(option, button), true);
assert.equal(JSON.parse(saved.fplWorkingPlanV2).portfolio_option, 'one_now');
assert.equal(JSON.parse(saved.fplWorkingPlanV2).moves.length, 1);
assert.equal(button.textContent, '✓ Plan selected');
assert.equal(button['aria-pressed'], 'true');

console.log('plan-choice persistence tests passed');
