(()=>{
const BUILD='transfer-synthesis-hierarchy-20260906-2';
const q=(s,r=document)=>r.querySelector(s);
function apply(){
  const d=window.FPLCoreData||{},syn=d.decision_synthesis,act=syn?.current_action;
  if(!act)return;
  const view=q('#view-transfer');if(!view)return;
  const holding=act.action==='HOLD',hit=Number(act.next_transfer_hit_cost||0);
  const lens=q('[data-decision-depth]',view);
  if(lens&&holding){
    const eye=q('.eyebrow',lens),h=q('h3',lens),status=q('.decision-status',lens),sub=q('.subtle',lens);
    if(eye)eye.textContent='DECISION GATE';
    if(h)h.textContent=act.headline||'Hold / roll';
    if(status)status.textContent='HOLD';
    if(sub)sub.textContent=hit?`The current move is complete. Any additional transfer now costs -${hit}; use the routes below only as contingencies if new information materially changes the decision.`:'The synthesized decision currently prefers holding. Routes below remain planning alternatives.';
    const items=lens.querySelectorAll('.decision-summary-item');if(items[0]){const small=q('small',items[0]);if(small)small.textContent='A heuristic route scores well, but the full agreement and timing gate still says HOLD.'}if(items[1]){const label=q('span',items[1]);if(label)label.textContent='Top heuristic model uplift'}if(items[2]){const label=q('span',items[2]);if(label)label.textContent='Top heuristic leverage uplift'}
  }
  const routes=q('[data-safe-routes]',view);
  if(routes&&holding){
    const eye=q('.eyebrow',routes),h=q('h3',routes),sub=q('.subtle',routes);
    if(eye)eye.textContent=hit?'ALTERNATIVE HIT ROUTES':'ALTERNATIVE ROUTES';
    if(h)h.textContent=hit?`Contingencies only · each extra move costs -${hit}`:'Contingencies to the current hold';
    if(sub)sub.textContent='These are lower-level model alternatives, not the active recommendation. The GW Decision above is authoritative unless its robustness gate changes.';
    let note=q('[data-synthesis-route-note]',routes);
    if(!note){note=document.createElement('div');note.dataset.synthesisRouteNote='1';note.style.cssText='margin:10px 0;padding:9px 10px;border-radius:10px;background:#201a0f;border:1px solid #f59e0b55;color:#fde68a;font-size:10px;line-height:1.45';routes.querySelector('.dc-player-list')?.insertAdjacentElement('beforebegin',note)}
    if(note){const rob=syn?.robustness||{},edge=Number(rob.single_step_edge_over_hold_6gw),support=Number(rob.measured_leader_support_models),required=Number(rob.required_consensus_models);note.textContent=hit?`HOLD gate active: ${act.completed_transfer?.route||'this week’s transfer'} is already done. A second move must overcome a -${hit} hit plus the evidence hurdle.`:`HOLD recommended. ${rob.single_step_leader||'The strongest measured route'}${Number.isFinite(edge)?` is +${edge.toFixed(1)} versus holding over six gameweeks`:''}, but exact-route agreement is ${Number.isFinite(support)?support:'—'}/${Number.isFinite(required)?required:'—'} required models. Reassess when evidence converges.`}
    routes.querySelectorAll('[data-transfer-choice]').forEach(btn=>{if(!String(btn.textContent||'').includes('Your choice'))btn.textContent='Save as contingency'});
  }
  document.documentElement.dataset.transferSynthesisHierarchyBuild=BUILD;
}
function run(){[180,500,1000,1800,3000].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();['fplCoreDataReady','fplSafePlanUpdated'].forEach(ev=>window.addEventListener(ev,run,{passive:true}));q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',()=>setTimeout(apply,180),{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
