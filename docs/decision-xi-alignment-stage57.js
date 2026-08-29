(()=>{
const BUILD='decision-xi-alignment-20260829-2005';
const KEY='fplWorkingPlanV2';
const q=(s,r=document)=>r.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
function plan(){try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}}
function norm(s){return String(s||'').trim().toLowerCase()}
function leader(){const d=window.FPLCoreData||{};const rows=d.current_next_gw_decisions?.safe_moves||[];return rows[0]||null}
function sameRoute(m,p){const pm=p?.moves?.[0];if(!m||!pm)return false;return norm(pm.out?.player)===norm(m.out?.player)&&norm(pm.in?.player)===norm(m.safe_in?.player)}
function render(){
 const m=leader(),view=q('#view-transfer');if(!m||!view)return;
 const route=`${m.out?.player||'—'} → ${m.safe_in?.player||'—'}`;
 const starts=!!m.safe_incoming_starts,xi=n(m.safe_xi_gain),raw=n(m.safe_raw_player_gain),working=plan(),aligned=sameRoute(m,working);
 let box=q('#xi-alignment-card');if(!box){box=document.createElement('section');box.id='xi-alignment-card';box.className='dc-card';const host=q('#dc-transfer-view');host?.prepend(box)}
 const tone=starts?'#34d399':'#fbbf24';
 const status=starts?'STARTS IN BEST XI':'BENCH / STRUCTURE ONLY';
 const mismatch=working?.moves?.[0]&&!aligned;
 const w=working?.moves?.[0];
 box.style.cssText=`border:1px solid ${tone}66;border-left:5px solid ${tone};background:#101a2d;margin:0 0 12px`;
 box.innerHTML=`<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start"><div><p class="eyebrow" style="color:${tone};margin-bottom:4px">CURRENT MODEL LEADER</p><h3 style="margin:0 0 5px">${esc(route)}</h3></div><span style="padding:5px 8px;border-radius:999px;background:${tone}18;color:${tone};font-size:9px;font-weight:900;white-space:nowrap">${status}</span></div><p class="subtle" style="margin:0">Best-XI model lift <strong style="color:${tone}">+${xi.toFixed(1)}</strong> model units · isolated player lift +${raw.toFixed(1)}. ${starts?'The incoming player earns a starting place after the transfer.':'The incoming player does not improve this gameweek’s optimal XI, so the route is penalised for using a free transfer.'}</p>${mismatch?`<div style="margin-top:9px;padding:9px 10px;border-radius:10px;background:#2a2210;border:1px solid #fbbf2466;color:#f8d477;font-size:11px"><strong>WORKING CHOICE IS NO LONGER THE MODEL LEADER</strong><br><span style="color:#c7b889">${esc(w.out?.player||'—')} → ${esc(w.in?.player||'—')} remains your saved scenario; it has not been changed automatically.</span></div>`:''}`;
 const brief=q('#gw-decision-brief');if(brief){const a=q('.gwd-action',brief),why=q('.gwd-why',brief);if(a)a.textContent=route;if(why)why.textContent=`${route} is the current XI-aware model leader. ${starts?'The incoming player improves the optimal XI immediately.':'This is primarily a structural move rather than a GW starting-XI upgrade.'}${mismatch?' Your saved working choice is different and remains only a scenario.':''}`}
 document.documentElement.dataset.xiAlignmentBuild=BUILD;
}
function run(){[300,800,1500,2500].forEach(ms=>setTimeout(render,ms))}
function bind(){run();window.addEventListener('fplCoreDataReady',run,{passive:true});window.addEventListener('fplSafePlanUpdated',run,{passive:true});q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
