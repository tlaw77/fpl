(()=>{
const BUILD='rival-adherence-20260829-0742';
const KEY='fplWorkingPlanV2';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
const norm=s=>String(s||'').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
function saved(){try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}}
function starters(rows){const a=(rows||[]).filter(p=>(p.slot||99)<=11||p.starter||n(p.multiplier)>0);return (a.length>=11?a:(rows||[])).slice(0,11)}
function applyPlan(rows){const base=(rows||[]).map(x=>({...x})),m=saved()?.moves?.[0];if(!m?.out||!m?.in)return base;const oid=Number(m.out.player_id),on=norm(m.out.player);const out=base.filter(p=>!(oid&&Number(p.player_id)===oid)&&norm(p.player)!==on);if(!out.some(p=>Number(p.player_id)===Number(m.in.player_id)))out.push({...m.in,_planned:true});return out}
function playerName(p){return p?.player||p?.web_name||''}
function score(p){return n(p?.six_gw_score??p?.decision_score??p?.score_improvement)}
function targetRival(d){const me=d?.me||{},rivals=[...(d?.rivals||[])],above=rivals.filter(r=>n(r.total_points)>n(me.total_points)).sort((a,b)=>n(a.total_points)-n(b.total_points));return above[0]||rivals.sort((a,b)=>Math.abs(n(a.total_points)-n(me.total_points))-Math.abs(n(b.total_points)-n(me.total_points)))[0]||null}
function evaluate(d){const r=targetRival(d);if(!r)return null;const raw=d.current_squad_next5||d.squad_next5||d.squad||[],my=starters(applyPlan(raw)),their=starters(r.picks||[]);const myIds=new Set(my.map(p=>Number(p.player_id))),theirIds=new Set(their.map(p=>Number(p.player_id))),shared=my.filter(p=>theirIds.has(Number(p.player_id))),mine=my.filter(p=>!theirIds.has(Number(p.player_id))).sort((a,b)=>score(b)-score(a)),theirs=their.filter(p=>!myIds.has(Number(p.player_id)));const qualityMine=mine.filter(p=>score(p)>=10||n(p.availability,1)>=.9&&score(p)>=8);const plan=saved()?.moves?.[0],soldShared=plan?.out&&theirIds.has(Number(plan.out.player_id));const gap=n(r.total_points)-n(d.me?.total_points),gw=n(d.current_gw,1);let posture=gap<=0?'PROTECT':gw<=5&&gap>15?'CONTROLLED CHASE':gap>30?'CHASE':'BALANCED';let status='ON PLAN',tone='#34d399',issues=[];
 if(soldShared){status='OFF PLAN';tone='#fb7185';issues.push(`working move sells shared shield ${playerName(plan.out)}`)}
 if(posture==='CONTROLLED CHASE'){
   if(qualityMine.length<1){status=status==='OFF PLAN'?status:'NEEDS EDGE';tone=status==='OFF PLAN'?tone:'#fbbf24';issues.push('no clear high-quality XI difference')}
   if(qualityMine.length>3){status=status==='OFF PLAN'?status:'TOO OPEN';tone=status==='OFF PLAN'?tone:'#fbbf24';issues.push(`${qualityMine.length} quality XI differences may be more variance than needed`)}
 }
 if(shared.length<3&&posture!=='CHASE'){status=status==='OFF PLAN'?status:'LIGHT SHIELDING';tone=status==='OFF PLAN'?tone:'#fbbf24';issues.push('limited shared core')}
 const edgeNames=qualityMine.slice(0,3).map(playerName).filter(Boolean),shieldNames=shared.slice().sort((a,b)=>score(b)-score(a)).slice(0,4).map(playerName).filter(Boolean),threatNames=theirs.slice(0,3).map(playerName).filter(Boolean);
 let suggestion='';
 if(soldShared)suggestion=`Reconsider selling ${playerName(plan.out)} unless the incoming player has a clear model and fixture edge.`;
 else if(posture==='CONTROLLED CHASE'&&qualityMine.length>=1&&qualityMine.length<=3)suggestion=`Keep the shared core; your XI already has ${qualityMine.length} credible difference${qualityMine.length===1?'':'s'}${edgeNames.length?` (${edgeNames.join(', ')})`:''}. Add variance only if the football case is stronger.`;
 else if(posture==='CONTROLLED CHASE'&&qualityMine.length<1)suggestion=`Look for one strong transfer or captaincy edge rather than several speculative changes.`;
 else if(qualityMine.length>3)suggestion=`You already have enough divergence. Prioritise reliability and shields over another differential.`;
 else suggestion=`Current structure broadly matches the posture. Prefer quality upgrades over forced uniqueness.`;
 return {r,posture,status,tone,shared,qualityMine,mine,theirs,issues,edgeNames,shieldNames,threatNames,suggestion};
}
function render(){const d=window.FPLCoreData,host=document.getElementById('dc-intel-view');if(!d||!host)return;host.querySelector('[data-rival-adherence]')?.remove();const card=host.querySelector('[data-gap-rival]');if(!card)return;const e=evaluate(d);if(!e)return;const box=document.createElement('div');box.dataset.rivalAdherence='1';box.style.cssText=`margin-top:10px;padding:10px 11px;border-radius:11px;background:#101a2d;border:1px solid ${e.tone}55;border-left:4px solid ${e.tone}`;const details=[`${e.shared.length} shared XI shields`,`${e.qualityMine.length} quality XI difference${e.qualityMine.length===1?'':'s'}`,`${e.theirs.length} rival-only starters`];box.innerHTML=`<div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><strong>Does your squad follow this?</strong><span style="font-size:8px;font-weight:900;color:${e.tone};border:1px solid ${e.tone}55;border-radius:999px;padding:4px 7px;white-space:nowrap">${esc(e.status)}</span></div><div class="subtle" style="margin-top:5px">${details.join(' · ')}</div>${e.shieldNames.length?`<div class="subtle" style="margin-top:4px"><b style="color:#60a5fa">Core protected:</b> ${esc(e.shieldNames.join(', '))}</div>`:''}${e.edgeNames.length?`<div class="subtle" style="margin-top:3px"><b style="color:#34d399">Current edges:</b> ${esc(e.edgeNames.join(', '))}</div>`:''}<div class="subtle" style="margin-top:5px"><b style="color:${e.tone}">Suggestion:</b> ${esc(e.suggestion)}</div>`;card.appendChild(box);document.documentElement.dataset.rivalAdherenceBuild=BUILD}
function settle(){[120,500,1100].forEach(ms=>setTimeout(render,ms))}
function bind(){document.querySelector('#decision-nav button[data-view="intel"]')?.addEventListener('click',settle,{passive:true});window.addEventListener('fplCoreDataReady',settle,{passive:true});window.addEventListener('fplSafePlanUpdated',settle,{passive:true});if(window.FPLCoreData)settle()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();