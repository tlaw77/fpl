(()=>{
  const xEsc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const xPct=v=>v==null?'—':`${Number(v).toFixed(1)}%`;
  function exposureFor(d,p){
    const e=(d.player_exposure||[]).find(x=>x.player_id===p.player_id);
    if(e)return e;
    const own=Number(p.mini_league_ownership_pct??p.ownership_pct);
    if(Number.isFinite(own))return {player_id:p.player_id,ownership_pct:own,effective_ownership_pct:own,owned_by:Math.round((d.league?.manager_count||8)*own/100),classification:own>=75?'shield':own>=40?'neutral':'leverage'};
    return {};
  }
  function renderExposureSquad(d){
    const el=document.querySelector('#squad-grid');if(!el)return;
    const n=Number(d.league?.manager_count||8);
    el.innerHTML=(d.squad||[]).map(p=>{
      const e=exposureFor(d,p);const eo=e.effective_ownership_pct;const own=e.ownership_pct;const owned=e.owned_by;
      const active=Number(e.my_multiplier??(p.starter?1:0))>0;
      let label=e.classification||'neutral';let roleText,roleClass;
      if(!active&&p.position!=='GKP'){
        roleText='Bench differential';roleClass='neutral';
      }else if(!active){
        roleText='Bench';roleClass='neutral';
      }else{
        roleClass=typeof badgeClass==='function'?badgeClass(label):'neutral';
        roleText=typeof labelText==='function'?labelText(label):label;
      }
      const gw=p.live_points??e.live_points;
      return `<div class="player-card exposure-card ${p.captain?'captain-ring':''}">
        <div class="player-name">${p.captain?'© ':''}${xEsc(p.player)}</div>
        <div class="player-meta">${xEsc(p.position)} · ${xEsc(p.club)} · £${Number(p.price||0).toFixed(1)}m</div>
        <div class="exposure-primary"><strong>${xPct(eo)}</strong><span>EO</span></div>
        <div class="exposure-secondary">${owned!=null?`${owned}/${n} own · `:''}${own!=null?`${xPct(own)} owned · `:''}${gw!=null?`GW ${gw} pts`:''}</div>
        <span class="badge ${roleClass}">${xEsc(roleText)}</span>
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