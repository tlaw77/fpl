const assert = require('assert');
const fs = require('fs');

const guard = fs.readFileSync('docs/price-timing-stage121.css', 'utf8');
const intel = fs.readFileSync('docs/mobile-intel-unclip-stage78.css', 'utf8');
const html = fs.readFileSync('docs/index.html', 'utf8');

assert.match(guard, /html,body,.shell\{[^}]*overflow-x:clip!important/);
assert.match(guard, /\.dashboard-view[^}]*max-width:100%/);
assert.match(guard, /\.msc-trend-reset\{grid-template-columns:minmax\(0,1fr\)/);
assert.ok(!intel.includes('body,.shell,#view-intel'));
assert.ok(!intel.includes('overflow-x:visible!important'));
assert.ok(html.includes('price-timing-stage121.css?v=20260915-4'));
assert.ok(html.includes('mobile-intel-unclip-stage78.css?v=20260915-4'));

console.log('mobile overflow containment tests passed');
