const assert=require('assert/strict'),fs=require('fs'),vm=require('vm');
const saved={},storage={getItem:k=>saved[k]||null,setItem:(k,v)=>saved[k]=v,removeItem:k=>delete saved[k]};let html='';
const host={querySelector(){return null},querySelectorAll(){return []},prepend(sec){html=sec.innerHTML}};
const ctx={window:{addEventListener(){}},localStorage:storage,document:{readyState:'loading',addEventListener(){},querySelector:s=>s==='#dc-team-view'?host:null,documentElement:{dataset:{}},createElement:()=>({dataset:{},isConnected:true,querySelectorAll:()=>Array(11)})},setTimeout(){},fetch:async()=>({ok:false}),console,MutationObserver:function(){}};vm.createContext(ctx);
for(const path of ['docs/working-plan-multi-stage118.js','docs/executed-plan-stage124.js','docs/pick-team-authoritative-stage99.js']){let source=fs.readFileSync(path,'utf8');if(path.includes('authoritative'))source=source.replace('window.FPLPickTeamAuthoritativeTest={effectiveSquad};','window.FPLPickTeamAuthoritativeTest={effectiveSquad,render};');vm.runInContext(source,ctx)}
const squad=Array.from({length:15},(_,i)=>({player_id:i+1,player:`Player ${i+1}`,position:i<2?'GKP':i<7?'DEF':i<12?'MID':'FWD',price:5}));squad[7].player='B.Fernandes';squad[12].player='João Pedro';
const incoming=[{player_id:379,player:'Isak',position:'FWD',price:9},{player_id:286,player:'Belloumi',position:'MID',price:5}];
const plan={moves:[{out:squad[12],in:{player_id:379,player:'Isak'}},{out:squad[7],in:{player_id:286,player:'Belloumi'}}]};
const raw={next_gw:9,current_squad_next5:squad,free_transfers_remaining_next_gw:2,decision_synthesis:{current_action:{}}},api=ctx.window.FPLExecutedPlan,receipt=api.buildReceipt(raw,plan);
saved.fplExecutedPlanV1=JSON.stringify(receipt);saved.fplWorkingPlanV2=JSON.stringify(plan);
const updated=api.effectiveData(raw,{players:incoming});assert.equal(updated.current_squad_next5.length,15);assert(updated.current_squad_next5.some(p=>p.player_id===379&&p.position==='FWD'));assert(updated.current_squad_next5.some(p=>p.player_id===286));assert(!raw.current_squad_next5.some(p=>p.player_id===379));
assert.equal(api.reconcile(updated).status,'awaiting-official');assert(saved.fplWorkingPlanV2,'Local application must not clear the draft as an official sync');
saved.fplExecutedPlanV1=JSON.stringify({...receipt,status:'officially-reconciled'});delete saved.fplWorkingPlanV2;
const review={status:'SUCCESS',recommended_xi_ids:[1,3,4,5,6,8,9,10,13,14,15],bench_order_ids:[2,7,11,12],captain:{player_id:14,player:'Player 14'},vice_captain:{player_id:9,player:'Player 9'}};
ctx.window.FPLPickTeamAuthoritativeTest.render(raw,review,{players:incoming});assert(html.includes('Isak'));assert(html.includes('Belloumi'));assert(!html.includes('<strong>João Pedro</strong>'));assert(!html.includes('<strong>B.Fernandes</strong>'));assert(html.includes('CONFIRMED SQUAD'));
assert.equal(api.effectiveData(updated,{players:incoming}).current_squad_next5.length,15);
assert.equal(api.reconcile({...updated,current_squad_source:'official'}).status,'officially-reconciled');
assert(!api.effectiveData({...raw,next_gw:10},{players:incoming}).current_squad_next5.some(p=>p.player_id===379));
console.log('Passed: full confirmed squad, stale server render, reload with cleared draft, no false reconciliation, idempotence, receipt expiry.');
