const assert=require('assert'),fs=require('fs'),vm=require('vm');
const storage=new Map(),context={window:{addEventListener(){},confirm:()=>true,FPLWorkingPlan:{apply:(base,catalog,plan)=>base.filter(x=>!plan.moves.some(m=>m.out.player_id===x.player_id)).concat(plan.moves.map(m=>catalog.find(x=>x.player_id===m.in.player_id))) }},document:{querySelector:()=>null,addEventListener(){},readyState:'loading',documentElement:{dataset:{}}},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},setTimeout(){},fetch(){}};
vm.createContext(context);vm.runInContext(fs.readFileSync('docs/executed-plan-stage124.js','utf8'),context);
const api=context.window.FPLExecutedPlan,plan={moves:[{out:{player_id:1,player:'Thomas'},in:{player_id:3,player:'Affengruber'}},{out:{player_id:2,player:'Greaves'},in:{player_id:4,player:'Bogle'}}]},data={next_gw:5,free_transfers_remaining_next_gw:2,current_squad_next5:[{player_id:1},{player_id:2},...Array.from({length:13},(_,i)=>({player_id:10+i}))],decision_synthesis:{current_action:{action:'TRANSFER'}}},pool={players:[{player_id:3},{player_id:4}]};
const receipt=api.buildReceipt(data,plan,'2026-09-15T23:40:55Z');
assert.equal(receipt.route,'Thomas → Affengruber + Greaves → Bogle');assert.equal(receipt.free_transfers_remaining,0);assert.equal(receipt.hit_cost,0);
api.applyLocal(data,pool,receipt);assert.equal(data.current_squad_next5.length,15);assert.ok(data.current_squad_next5.some(x=>x.player_id===3));assert.ok(!data.current_squad_next5.some(x=>x.player_id===1));assert.equal(data.decision_synthesis.current_action.action,'HOLD');assert.equal(data.next_transfer_hit_cost,4);
assert.equal(api.officialApplied(data,receipt),true);
console.log('executed plan tests passed');
