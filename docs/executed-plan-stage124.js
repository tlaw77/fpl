(()=>{
const BUILD='executed-plan-stage124-20260916-2',PLAN_KEY='fplWorkingPlanV2',EXECUTED_KEY='fplExecutedPlanV1',POOL_URL='https://raw.githubusercontent.com/tlaw77/fpl/main/data/player_pool.json';
const q=(s,r=document)=>r.querySelector(s),n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const read=(key)=>{try{return JSON.parse(localStorage.getItem(key)||'null')}catch{return null}};
const write=(key,value)=>{try{localStorage.setItem(key,JSON.stringify(value));return true}catch{return false}};
const moves=plan=>(Array.isArray(plan?.moves)?plan.moves:[]).filter(x=>x?.out&&x?.in);
const route=plan=>moves(plan).map(x=>`${x.out.player||'—'} → ${x.in.player||'—'}`).join(' + ');
const includes=(rows,ref)=>(rows||[]).some(x=>Number(ref?.player_id)&&Number(x.player_id)===Number(ref.player_id));
function officialApplied(data,receipt){const rows=data?.current_squad_next5||data?.squad_next5||[],ms=moves(receipt);return !!ms.length&&ms.every(x=>includes(rows,x.in)&&!includes(rows,x.out))}
function buildReceipt(data,plan,at=new Date().toISOString()){
 const ms=moves(plan),starting=n(data?.free_transfers_remaining_next_gw,data?.decision_synthesis?.current_action?.free_transfers_remaining),used=Math.min(starting,ms.length),hit=Math.max(0,ms.length-starting)*4;
 return{version:1,event:n(data?.next_gw),confirmed_at_utc:at,status:'awaiting-official',route:route(plan),starting_free_transfers:starting,free_transfers_used:used,free_transfers_remaining:Math.max(0,starting-ms.length),hit_cost:hit,moves:ms};
}
function completeDecision(data,receipt){
 const syn=data.decision_synthesis||(data.decision_synthesis={}),a=syn.current_action||(syn.current_action={});
 a.completed_transfer={event:receipt.event,route:receipt.route,transfer_count:receipt.moves.length,confirmed_at_utc:receipt.confirmed_at_utc,source:'local_execution_confirmation'};
 a.action='HOLD';a.headline='HOLD';a.reason=`${receipt.route} is registered as completed. Further moves are assessed separately.`;a.free_transfers_remaining=receipt.free_transfers_remaining;a.next_transfer_hit_cost=receipt.free_transfers_remaining>0?0:4;a.transfer_count=0;
 data.free_transfers_available_before_moves=receipt.starting_free_transfers;data.free_transfers_used_next_gw=receipt.free_transfers_used;data.free_transfers_remaining_next_gw=receipt.free_transfers_remaining;data.transfer_hits_already_incurred_next_gw=receipt.hit_cost;data.next_transfer_hit_cost=receipt.free_transfers_remaining>0?0:4;data.declared_transfer_overlay_status='local_confirmation_pending_official';
}
function applyLocal(data,pool,receipt){
 if(!data||!receipt||officialApplied(data,receipt))return data;
 const base=data.current_squad_next5||data.squad_next5||[],api=window.FPLWorkingPlan;
 if(api?.apply){const applied=api.apply(base,pool?.players||[],receipt);if(applied.length===15){data.current_squad_next5=applied;data.current_squad_source='local_execution_confirmation'}}
 completeDecision(data,receipt);return data;
}
function reconcile(data){
 const receipt=read(EXECUTED_KEY);if(!receipt)return null;
 const completed=data?.decision_synthesis?.current_action?.completed_transfer;
 if(officialApplied(data,receipt)||(completed&&Number(completed.event)===Number(receipt.event)&&completed.route===receipt.route)){
  receipt.status='officially-reconciled';receipt.reconciled_at_utc=new Date().toISOString();write(EXECUTED_KEY,receipt);localStorage.removeItem(PLAN_KEY);return receipt;
 }
 return receipt;
}
function adoptOfficialPlan(data){const plan=read(PLAN_KEY);if(!moves(plan).length||!officialApplied(data,plan))return null;const receipt=buildReceipt(data,plan);receipt.status='officially-reconciled';receipt.reconciled_at_utc=new Date().toISOString();write(EXECUTED_KEY,receipt);localStorage.removeItem(PLAN_KEY);return receipt}
let pool=null,loading=null;
function loadPool(){if(pool)return Promise.resolve(pool);if(window.FPLPlayerPoolData){pool=window.FPLPlayerPoolData;return Promise.resolve(pool)}if(loading)return loading;loading=fetch(`${POOL_URL}?ep124=${Date.now()}`,{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null).then(x=>{pool=x;if(x)window.FPLPlayerPoolData=x;return x}).finally(()=>loading=null);return loading}
function confirmPlan(){
 const data=window.FPLCoreData||{},plan=read(PLAN_KEY),ms=moves(plan);if(!ms.length)return;
 if(!window.confirm(`Confirm these transfers were completed in FPL?\n\n${route(plan)}\n\nThis records the move in the app; it does not submit a transfer to FPL.`))return;
 const receipt=buildReceipt(data,plan);if(!write(EXECUTED_KEY,receipt))return;
 applyLocal(data,pool,receipt);window.dispatchEvent(new CustomEvent('fplTransferExecuted',{detail:receipt}));window.dispatchEvent(new CustomEvent('fplSafePlanUpdated',{detail:receipt}));render();
}
function clearLocal(){if(!window.confirm('Remove only the app confirmation? This cannot undo transfers already made in FPL.'))return;localStorage.removeItem(EXECUTED_KEY);location.reload()}
function render(){
 const view=q('#view-transfer'),host=q('#dc-transfer-view',view);if(!view||!host)return;q('[data-executed-plan]',view)?.remove();
 const data=window.FPLCoreData||{};let receipt=reconcile(data)||adoptOfficialPlan(data);const plan=read(PLAN_KEY),ms=moves(plan);if(!receipt&&!ms.length)return;
 const sec=document.createElement('section');sec.className=`dc-card ep124 ${receipt?'confirmed':'ready'}`;sec.dataset.executedPlan='1';
 if(receipt){const synced=receipt.status==='officially-reconciled';sec.innerHTML=`<div class="ep124-head"><div><p class="eyebrow">TRANSFER RECEIPT · GW${esc(receipt.event)}</p><h3>${synced?'Transfers confirmed by FPL':'Transfers registered in this app'}</h3></div><span>${synced?'SYNCED ✓':'APPLIED LOCALLY ✓'}</span></div><strong class="ep124-route">${esc(receipt.route)}</strong><p>${synced?'The official squad now contains these moves. The temporary working plan has been cleared.':'Your effective squad, transfer bank and completed-plan state update immediately on this device. The scheduled data refresh will reconcile it with FPL automatically.'}</p><div class="ep124-stats"><span><b>${receipt.moves.length}</b> made</span><span><b>${receipt.free_transfers_remaining}</b> FT left</span><span><b>${receipt.hit_cost?`−${receipt.hit_cost}`:'0'}</b> hit</span></div>${synced?'':`<button type="button" data-ep-correct>Correct this confirmation</button>`}`}
 else sec.innerHTML=`<div class="ep124-head"><div><p class="eyebrow">READY TO RECORD</p><h3>Made these transfers in FPL?</h3></div><span>${ms.length} MOVE${ms.length===1?'':'S'}</span></div><strong class="ep124-route">${esc(route(plan))}</strong><p>Confirm only after completing the moves in the official FPL app. This locks the full route as completed here and starts planning from the new squad immediately.</p><button type="button" data-ep-confirm>Confirm transfers made</button>`;
 const portfolio=q('[data-ft-portfolio]',view);if(portfolio)portfolio.insertAdjacentElement('beforebegin',sec);else host.prepend(sec);q('[data-ep-confirm]',sec)?.addEventListener('click',confirmPlan);q('[data-ep-correct]',sec)?.addEventListener('click',clearLocal);document.documentElement.dataset.executedPlanBuild=BUILD;
}
function hydrate(){const data=window.FPLCoreData;if(!data)return;const receipt=reconcile(data);if(receipt&&receipt.status!=='officially-reconciled')loadPool().then(p=>{applyLocal(data,p,receipt);render();window.dispatchEvent(new CustomEvent('fplSafePlanUpdated',{detail:receipt}))});else render()}
function run(){[80,300,800].forEach(ms=>setTimeout(hydrate,ms))}
function bind(){run();window.addEventListener('fplCoreDataReady',run,{passive:true});window.addEventListener('fplSafePlanUpdated',()=>setTimeout(render,40),{passive:true});q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',()=>setTimeout(render,80),{passive:true})}
window.FPLExecutedPlan={PLAN_KEY,EXECUTED_KEY,buildReceipt,officialApplied,applyLocal,reconcile,adoptOfficialPlan};
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
