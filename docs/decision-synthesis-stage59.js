(()=>{
const BUILD='decision-synthesis-20260829-2034';
const q=(s,r=document)=>r.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const txt=el=>String(el?.textContent||'').replace(/\s+/g,' ').trim();
function leaguePosture(){const full=txt(q('#view-intel'));return((full.match(/\b(PROTECT|BALANCED|CONTROLLED CHASE|CHASE)\b/i)||[])[1]||'BALANCED').toUpperCase()}
function teamSummary(d){const cap=d?.me?.captain||'';return cap?`Captain ${cap} · full XI in Pick Team`:'Open Pick Team for XI'}
function render(){
  const d=window.FPLCoreData||{},syn=d.decision_synthesis,decision=syn?.current_action;
  if(!decision)return;
  const view=q('#view-transfer'),transferHost=q('#dc-transfer-view',view);if(!view||!transferHost)return;
  let host=q('#gw-decision-brief',view);if(!host){host=document.createElement('section');host.id='gw-decision-brief';host.className='gw-decision-brief';transferHost.insertAdjacentElement('beforebegin',host)}
  const gw=txt(q('#gw-pill'))||`GW ${syn.next_gw||'—'}`,confidence=Number(decision.confidence||0),tone=confidence>=80?'strong':confidence>=68?'good':'watch';
  const done=decision.completed_transfer?.route||'';
  const ft=Number(decision.free_transfers_remaining||0),hit=Number(decision.next_transfer_hit_cost||0);
  const chip=syn.chips||{},chipText=chip.action==='HOLD'?`HOLD · portfolio inflection GW${chip.latest_safe_start_gw||'—'}`:`${chip.action||'WATCH'} · reassess chip window`;
  host.dataset.tone=tone;
  host.dataset.synthesis='1';
  host.innerHTML=`<div class="gwd-top"><div><p class="eyebrow">${esc(gw)} DECISION</p><div class="gwd-action">${esc(decision.headline||decision.action||'HOLD')}</div></div><div class="gwd-confidence"><strong>${esc(confidence)}%</strong><span>confidence</span></div></div><p class="gwd-why">${esc(decision.reason||'')}</p><div class="gwd-strip"><span><b>TEAM</b>${esc(teamSummary(d))}</span><span><b>LEAGUE</b>${esc(leaguePosture())}</span></div><div class="gwd-watch"><b>STATE</b> ${esc(done?`${done} done · ${ft} FT left${hit?` · next move -${hit}`:''}`:`${ft} FT left${hit?` · next move -${hit}`:''}`)}</div><div class="gwd-watch"><b>CHIPS</b> ${esc(chipText)}</div>`;
  document.documentElement.dataset.decisionSynthesisBuild=BUILD;
}
function run(){[120,350,800,1500,2600].forEach(ms=>setTimeout(render,ms))}
function bind(){run();['fplCoreDataReady','fplSafePlanUpdated'].forEach(ev=>window.addEventListener(ev,run,{passive:true}));q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',()=>setTimeout(render,120),{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
