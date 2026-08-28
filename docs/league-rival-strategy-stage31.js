(()=>{
const BUILD='league-rival-strategy-stage31-20260828-2216';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
function starters(rows){return (rows||[]).filter(p=>(p.slot||99)<=11||p.starter||n(p.multiplier)>0).slice(0,11)}
function captain(rows){return (rows||[]).find(p=>p.captain||n(p.multiplier)>1)||null}
function pct(v){return `${Math.round(n(v))}%`}
function actionFor(gap,overlap,capDiff,gwSwing){
  if(gap<=0)return ['PROTECT','#60a5fa','You are ahead of this rival. Keep strong shared coverage and avoid unnecessary variance.'];
  if(gap<=8&&overlap>=65)return ['MATCH CORE','#34d399','The gap is small. Protect the strongest shared players and look for only one quality edge.'];
  if(gap<=20)return ['SELECTIVE EDGE','#fbbf24',capDiff||overlap<65?'A measured difference can move the gap. Prefer a stronger player/fixture edge over forced uniqueness.':'High overlap means transfers matter more than wholesale divergence.'];
  if(gap>30)return ['CONTROLLED CHASE','#fb7185','A larger gap needs more routes to gain, but still only where player quality, fixtures and minutes support the risk.'];
  return ['SELECTIVE CHASE','#fbbf24',gwSwing>5?'This rival is currently gaining this GW. Create selective upside without breaking your core.':'Use 1–2 justified differences while retaining the best shields.'];
}
function profile(d,r){
  const me=d.me||{},my=starters(d.squad||d.squad_next5||[]),rp=starters(r.picks||[]),myIds=new Set(my.map(p=>Number(p.player_id))),rIds=new Set(rp.map(p=>Number(p.player_id)));const shared=[...myIds].filter(id=>rIds.has(id)).length,diffs=rp.filter(p=>!myIds.has(Number(p.player_id))).length,overlap=n(r.overlap_pct,shared/11*100),mc=captain(my),rc=captain(rp),capDiff=!!(mc&&rc&&Number(mc.player_id)!==Number(rc.player_id)),gap=n(r.total_points)-n(me.total_points),myGw=n(me.live_calculated_points??me.gw_points),rGw=n(r.live_calculated_points??r.gw_points),gwSwing=rGw-myGw,[action,color,why]=actionFor(gap,overlap,capDiff,gwSwing);
  return {r,gap,overlap,shared,diffs,capDiff,mc,rc,gwSwing,action,color,why};
}
function row(p){
  const gap=p.gap>0?`+${p.gap}`:`${p.gap}`,swing=p.gwSwing>0?`+${p.gwSwing}`:`${p.gwSwing}`;return `<div style="padding:10px 0;border-top:1px solid #243451"><div style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:start"><div><strong>${esc(p.r.team_name||p.r.manager||'Rival')}</strong><div class="subtle" style="margin-top:2px">${esc(p.r.manager||'')} · gap ${gap} · GW swing ${swing}</div></div><span style="font-size:8px;font-weight:900;color:${p.color};border:1px solid ${p.color}55;border-radius:999px;padding:4px 7px;white-space:nowrap">${p.action}</span></div><div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:7px;font-size:9px;color:#cbd5e1"><span style="background:#101a2d;border:1px solid #243451;border-radius:999px;padding:4px 6px">Overlap ${pct(p.overlap)}</span><span style="background:#101a2d;border:1px solid #243451;border-radius:999px;padding:4px 6px">${p.diffs} XI differences</span><span style="background:#101a2d;border:1px solid #243451;border-radius:999px;padding:4px 6px">Captain ${p.capDiff?'different':'matched'}</span></div><div class="subtle" style="margin-top:6px">${esc(p.why)}</div></div>`
}
function render(){
  const d=window.FPLCoreData,host=document.getElementById('dc-intel-view');if(!d||!host)return;host.querySelector('[data-gap-style]')?.remove();host.querySelector('[data-rival-strategy-map]')?.remove();const rivals=(d.rivals||[]).map(r=>profile(d,r)).sort((a,b)=>{const aa=a.gap>0?0:1,bb=b.gap>0?0:1;if(aa!==bb)return aa-bb;return Math.abs(a.gap)-Math.abs(b.gap)});if(!rivals.length)return;const sec=document.createElement('section');sec.className='dc-card';sec.dataset.rivalStrategyMap='1';sec.innerHTML=`<div class="panel-head"><div><p class="eyebrow">RIVAL STRATEGY MAP</p><h3>Who matters and how to play them</h3></div><div class="subtle">No opaque score</div></div><p class="subtle">Use gap, current-GW swing, XI overlap and captain divergence together. The aim is to identify where to protect coverage and where a justified difference can actually move your mini-league position.</p><div style="margin-top:7px">${rivals.map(row).join('')}</div>`;const target=host.querySelector('[data-gap-rival]');if(target)target.insertAdjacentElement('afterend',sec);else host.appendChild(sec);document.documentElement.dataset.rivalStrategyBuild=BUILD;
}
function settle(){setTimeout(render,120);setTimeout(render,550);setTimeout(render,1100)}
function bind(){document.querySelector('#decision-nav button[data-view="intel"]')?.addEventListener('click',settle,{passive:true});window.addEventListener('fplCoreDataReady',settle,{passive:true});window.addEventListener('fplSafePlanUpdated',settle,{passive:true});if(window.FPLCoreData)settle()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();