(()=>{
const BUILD='decision-synthesis-20260831-0118';
const CAP_URL='https://raw.githubusercontent.com/tlaw77/fpl/main/data/captaincy_review.json';
const q=(s,r=document)=>r.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const txt=el=>String(el?.textContent||'').replace(/\s+/g,' ').trim();
let capData=window.FPLCaptaincyReview||null,capLoading=null;
function leaguePosture(){const full=txt(q('#view-intel'));return((full.match(/\b(PROTECT|BALANCED|CONTROLLED CHASE|CHASE)\b/i)||[])[1]||'BALANCED').toUpperCase()}
function teamSummary(){const c=capData||window.FPLCaptaincyReview;if(c?.captain?.player){const vice=c?.vice_captain?.player;return `Captain ${c.captain.player}${vice?` · Vice ${vice}`:''} · full XI in Pick Team`}return 'Captaincy loading · full XI in Pick Team'}
async function ensureCaptaincy(){if(capData)return capData;if(window.FPLCaptaincyReview){capData=window.FPLCaptaincyReview;return capData}if(capLoading)return capLoading;capLoading=fetch(`${CAP_URL}?syn59=${Date.now()}`,{cache:'no-store'}).then(r=>r.ok?r.json():null).then(x=>{if(x){capData=x;window.FPLCaptaincyReview=x}return x}).catch(()=>null).finally(()=>{capLoading=null});return capLoading}
function render(){
  const d=window.FPLCoreData||{},syn=d.decision_synthesis,decision=syn?.current_action;
  if(!decision)return;
  const view=q('#view-transfer'),transferHost=q('#dc-transfer-view',view);if(!view||!transferHost)return;
  let host=q('#gw-decision-brief',view);if(!host){host=document.createElement('section');host.id='gw-decision-brief';host.className='gw-decision-brief';transferHost.insertAdjacentElement('beforebegin',host)}
  const gw=txt(q('#gw-pill'))||`GW ${syn.next_gw||'—'}`,confidence=Number(decision.confidence||0),tone=confidence>=80?'strong':confidence>=68?'good':'watch';
  const done=decision.completed_transfer?.route||'';
  const ft=Number(decision.free_transfers_remaining||0),hit=Number(decision.next_transfer_hit_cost||0);
  const chip=syn.chips||{},chipText=chip.action==='HOLD'?`HOLD · latest safe chip start GW${chip.latest_safe_start_gw||'—'}`:`${chip.action||'WATCH'} · check again for the best chip week`;
  const ftText=`${ft} free transfer${ft===1?'':'s'} left${hit?` · another transfer costs -${hit}`:''}`;
  host.dataset.tone=tone;
  host.dataset.synthesis='1';
  host.innerHTML=`<div class="gwd-top"><div><p class="eyebrow">${esc(gw)} DECISION</p><div class="gwd-action">${esc(decision.headline||decision.action||'HOLD')}</div></div><div class="gwd-confidence"><strong>${esc(confidence)}%</strong><span>confidence</span></div></div><p class="gwd-why">${esc(decision.reason||'')}</p><div class="gwd-strip"><span><b>TEAM</b>${esc(teamSummary())}</span><span><b>LEAGUE</b>${esc(leaguePosture())}</span></div><div class="gwd-watch"><b>THIS WEEK</b> ${esc(done?`${done} done · ${ftText}`:ftText)}</div><div class="gwd-watch"><b>CHIPS</b> ${esc(chipText)}</div>`;
  document.documentElement.dataset.decisionSynthesisBuild=BUILD;
}
function run(){[120,350,800,1500,2600].forEach(ms=>setTimeout(render,ms));ensureCaptaincy().then(()=>render())}
function bind(){run();['fplCoreDataReady','fplSafePlanUpdated','fplCaptaincyReviewReady'].forEach(ev=>window.addEventListener(ev,e=>{if(ev==='fplCaptaincyReviewReady'&&e.detail)capData=e.detail;run()},{passive:true}));q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',()=>setTimeout(render,120),{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
