(()=>{
  const xEsc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const xPct=v=>v==null?'—':`${Number(v).toFixed(1)}%`;
  function exposureFor(d,p){
    const e=(d.player_exposure||[]).find(x=>x.player_id===p.player_id);
    if(e)return e;
    const own=Number(p.mini_league_ownership_pct??p.ownership_pct);
    if(Number.isFinite(own))return {player_id:p.player_id,ownership_pct:own,effective_ownership_pct:own,owned_by:Math.round((d.league?.manager_count||8)*own/100)};
    return {};
  }
  function renderExposureSquad(d){
    const el=document.querySelector('#squad-grid');if(!el)return;
    const M=window.FPLExposureModel,n=Number(d.league?.manager_count||8),xiIds=new Set((M?.startingXI(d.squad||[])||[]).map(p=>p.player_id));
    el.innerHTML=(d.squad||[]).map(p=>{
      const e=exposureFor(d,p),eo=Number(e.effective_ownership_pct??e.ownership_pct??0),own=e.ownership_pct,owned=e.owned_by,active=xiIds.has(p.player_id);
      const role=M?.roleFor(p,new Map([[p.player_id,e]]),active)||{label:active?(eo>=75?'Shield':eo>=40?'Neutral':'Leverage'):'Bench differential',family:active?(eo>=75?'shield':eo<40?'leverage':'neutral'):'neutral'};
      const roleClass=role.family==='shield'?'shield':role.family==='leverage'?'leverage':role.family==='danger'?'danger':'neutral',gw=p.live_points??e.live_points;
      return `<div class="player-card exposure-card ${p.captain?'captain-ring':''}">
        <div class="player-name">${p.captain?'© ':''}${xEsc(p.player)}</div>
        <div class="player-meta">${xEsc(p.position)} · ${xEsc(p.club)} · £${Number(p.price||0).toFixed(1)}m</div>
        <div class="exposure-primary"><strong>${xPct(eo)}</strong><span>EO</span></div>
        <div class="exposure-secondary">${owned!=null?`${owned}/${n} own · `:''}${own!=null?`${xPct(own)} owned · `:''}${gw!=null?`GW ${gw} pts`:''}</div>
        <span class="badge ${roleClass}">${xEsc(role.label)}</span>
      </div>`;
    }).join('');
  }
  try{window.renderSquad=renderExposureSquad;}catch{}
  window.FPLExposureUI={render:renderExposureSquad};
  window.addEventListener('effectiveSquadRendered',()=>{if(window.__effectiveData)renderExposureSquad(window.__effectiveData)});
  window.addEventListener('fplPlanChanged',()=>setTimeout(()=>{if(window.__effectiveData)renderExposureSquad(window.__effectiveData)},70));
  window.addEventListener('load',()=>setTimeout(()=>{if(window.__effectiveData)renderExposureSquad(window.__effectiveData)},1100));
  if(!document.querySelector('script[data-metrics-consistency]')){const s=document.createElement('script');s.src='metrics-consistency.js';s.dataset.metricsConsistency='1';document.body.appendChild(s)}
})();