const assert=require('assert'),fs=require('fs'),vm=require('vm');
const context={window:{},document:{readyState:'loading',addEventListener(){}}};
vm.runInNewContext(fs.readFileSync('docs/transfer-layout.js','utf8'),context);
const group=context.window.FPLTransferLayout.group;
const card=(...selectors)=>({matches:s=>s.split(',').some(x=>selectors.includes(x))});
assert.equal(group(card('[data-decision-signal]'),true,true),'decision');
assert.equal(group(card('[data-executed-plan]'),true,true),'decision');
assert.equal(group(card('[data-ft-portfolio]'),true,true),'compare');
assert.equal(group(card('[data-safe-routes]'),true,true),'obsolete');
assert.equal(group(card('[data-safe-routes]'),true,false),'compare');
for(const selector of ['#gw-decision-brief','#decision-twin-card','.transfer-hero','.decision-lens','[data-monitor="pressure"]']){
 assert.equal(group(card(selector),true,true),'obsolete');
 assert.equal(group(card(selector),false,false),'evidence');
}
assert.equal(group(card('#decision-history-panel'),true,true),'history');
assert.equal(group(card('[data-between-games-watch]'),true,true),'evidence');
assert.equal(group(card('[data-transfer-layout]'),true,true),'navigation');
console.log('Transfer layout classification and fallback tests passed');
