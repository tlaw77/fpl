(()=>{
const BUILD='decision-xi-alignment-20260906-2';
const KEY='fplWorkingPlanV2';
const q=(s,r=document)=>r.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
function plan(){try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}}
function norm(s){return String(s||'').trim().toLowerCase()}
function leader(){const d=window.FPLCoreData||{};return (d.current_next_gw_decisions?.safe_moves||[])[0]||null}
function sameRoute(m,p){const pm=p?.moves?.[0];if(!m||!pm)return false;return norm(pm.out?.player)===norm(m.out?.player)&&norm(pm.in?.player)===norm(m.safe_in?.player)}
function render(){const m=leader(),view=q('#view-transfer');if(!m||!view)return;q('#xi-alignment-card')?.remove();const route=`${m.out?.player||'—'} → ${m.safe_in?.player||'—'}`,working=plan(),aligned=sameRoute(m,working),mismatch=working?.moves?.[0]&&!aligned,w=working?.moves?.[0];
 const hero=q('.transfer-hero,.dc-recommendation',view);let warn=q('#working-choice-warning',view);if(mismatch&&hero){if(!warn){warn=document.createElement('div');warn.id='working-choice-warning';warn.style.cssText='margin-top:10px;padding:9px 10px;border-radius:10px;background:#2a2210;border:1px solid #fbbf2466;color:#f8d477;font-size:11px';hero.appendChild(warn)}warn.innerHTML=`<strong>WORKING CHOICE IS NO LONGER THE MODEL LEADER</strong><br><span style="color:#c7b889">${esc(w.out?.player||'—')} → ${esc(w.in?.player||'—')} remains your saved scenario.</span>`}else warn?.remove();document.documentElement.dataset.xiAlignmentBuild=BUILD}
function run(){[300,800,1500,2500].forEach(ms=>setTimeout(render,ms))}function bind(){run();window.addEventListener('fplCoreDataReady',run,{passive:true});window.addEventListener('fplSafePlanUpdated',run,{passive:true});q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',run,{passive:true})}if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
