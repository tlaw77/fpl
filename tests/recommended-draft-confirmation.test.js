const assert=require('assert/strict'),fs=require('fs'),vm=require('vm');
const saved={},events=[];
const ctx={window:{addEventListener(){},dispatchEvent(e){events.push(e.type)}},localStorage:{getItem:k=>saved[k]||null,setItem:(k,v)=>saved[k]=v},document:{readyState:'loading',addEventListener(){},querySelector(){return null},documentElement:{dataset:{}}},CustomEvent:function(t,o){this.type=t;this.detail=o?.detail},setTimeout(){},fetch:async()=>({ok:false}),console};
vm.createContext(ctx);
for(const file of ['docs/active-decision-signal-stage119.js','docs/free-transfer-portfolio-stage117.js','docs/executed-plan-stage124.js','docs/transfer-signal-stage80.js']){
 let source=fs.readFileSync(file,'utf8');
 if(file.includes('transfer-signal'))source=source.replace(/\}\)\(\);\s*$/, 'window.signalTest={chooseRecommended,gateHtml};})();');
 vm.runInContext(source,ctx);
}
const option={key:'multiple_now',available:true,first_action:{action:'TRANSFER',route:'Pedro → Isak + Fernandes → Belloumi',transfers:[{route:'Pedro → Isak',out_id:165,in_id:379},{route:'Fernandes → Belloumi',out_id:426,in_id:286}]}};
ctx.window.FPLCoreData={next_gw:9,decision_synthesis:{current_action:{action:'TRANSFER',headline:option.first_action.route,execution_ready:false},transfer_options:[option]}};
ctx.window.FPLTransferBudget={evaluate:()=>({ok:true,message:'Affordable'})};
const old={moves:[{out:{player:'Maguire'},in:{player:'Muharemović'}}]};
saved.fplWorkingPlanV2=JSON.stringify(old);
assert(ctx.window.FPLExecutedPlan.draftMismatch(ctx.window.FPLCoreData,old));
ctx.window.signalTest.chooseRecommended({setAttribute(){}});
const plan=JSON.parse(saved.fplWorkingPlanV2);
assert.equal(plan.moves.length,2);assert.equal(plan.moves[0].out.player_id,165);assert.equal(plan.moves[1].in.player_id,286);
assert(!ctx.window.FPLExecutedPlan.draftMismatch(ctx.window.FPLCoreData,plan));
assert.equal(saved.fplExecutedPlanV1,undefined,'Selecting must never record execution');
ctx.window.FPLTransferBudget.evaluate=()=>({ok:false,message:'Over budget'});
saved.fplWorkingPlanV2=JSON.stringify(old);ctx.window.signalTest.chooseRecommended({});assert.equal(saved.fplWorkingPlanV2,JSON.stringify(old));
const html=ctx.window.signalTest.gateHtml({active_edge_over_hold_6gw:5,active_required_edge:3,active_transfer_gate_clear:true,active_validation_clear:true},[],{canExecute:false,title:'WAIT',copy:'News pending'});
assert(html.includes('txs-trigger blocked'));assert(html.includes('data-use-recommended-draft'));
console.log('Passed: replace mismatched draft, preserve both moves, no execution receipt, budget refusal, waiting state.');
