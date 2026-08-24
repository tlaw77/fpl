const Explainability = (()=>{
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
  const pct=v=>`${Number(v||0).toFixed(0)}%`;
  const confidence=(p,extra=0)=>{
    const availability=Number(p?.availability??1);
    const fixtures=Number(p?.fixture_ease_next5??3);
    const score=Number(p?.decision_score??0);
    const newsPenalty=p?.news?18:0;
    const raw=50+(availability*20)+((fixtures-3)*8)+Math.min(15,score)+extra-newsPenalty;
    return Math.max(5,Math.min(95,Math.round(raw)));
  };
  const tone=c=>c>=80?'high':c>=60?'medium':'low';
  const fixtureReason=p=>{
    const fs=(p?.fixtures||[]).slice(0,3);
    if(!fs.length)return 'Fixture run unavailable';
    const avg=fs.reduce((a,f)=>a+Number(f.difficulty||3),0)/fs.length;
    return avg<=2.4?'Strong short-term fixtures':avg>=3.6?'Difficult short-term fixtures':'Mixed short-term fixtures';
  };
  const moveWhy=(m,mode)=>{
    const p=m?.in||{}; const reasons=[];
    reasons.push(fixtureReason(p));
    if((p.availability??1)<0.9) reasons.push(`Availability ${pct((p.availability||0)*100)}`); else reasons.push('Availability looks good');
    if(Number(m?.score_improvement||0)>0) reasons.push(`Model uplift +${Number(m.score_improvement).toFixed(1)}`);
    const targetOwn=p.target_rival_ownership_pct;
    if(targetOwn!==undefined) reasons.push(mode==='protect'?`${pct(targetOwn)} owned by target rivals`:`${pct(targetOwn)} owned by target rivals`);
    if(p.ownership_pct!==undefined) reasons.push(`${pct(p.ownership_pct)} mini-league ownership`);
    return reasons;
  };
  function renderMove(id,moves,mode){
    const el=document.querySelector(id); if(!el) return;
    el.innerHTML=(moves||[]).length?(moves||[]).map(m=>{
      const c=confidence(m.in,Math.min(12,Number(m.score_improvement||0)*2));
      const fragile=(m.in?.news||Number(m.in?.availability??1)<0.75||((m.in?.fixtures||[])[0]?.difficulty||3)>=5);
      return `<div class="explain-card"><div class="explain-head"><div><span class="out">${esc(m.out?.player)}</span> → <strong>${esc(m.in?.player)}</strong></div><span class="confidence ${tone(c)}">${c}% confidence</span></div><div class="why-grid">${moveWhy(m,mode).map(x=>`<span>${esc(x)}</span>`).join('')}</div>${fragile?'<div class="fragile">⚠ High-upside but fragile: re-check team news before deadline.</div>':''}</div>`;
    }).join(''):'<div class="subtle">No positive move currently clears the confidence threshold.</div>';
  }
  function renderCaptain(id,items,mode){
    const el=document.querySelector(id); if(!el)return;
    el.innerHTML=(items||[]).length?(items||[]).slice(0,5).map((p,i)=>{
      const c=confidence(p,mode==='protect'?8:0);
      const f=(p.fixtures||[])[0]||p.next_fixture;
      const rival=p.target_rival_ownership_pct;
      const reasons=[f?`GW${f.gw||''} ${f.opponent} ${f.venue} · FDR ${f.difficulty}`:'Fixture unavailable',`Form ${p.form??'—'} · PPG ${p.points_per_game??'—'}`,rival!==undefined?`${pct(rival)} target-rival ownership`:null,p.news?`News: ${p.news}`:'No current availability flag'].filter(Boolean);
      return `<div class="explain-card"><div class="explain-head"><div><strong>${i+1}. ${esc(p.player)}</strong></div><span class="confidence ${tone(c)}">${c}%</span></div><div class="why-grid">${reasons.map(x=>`<span>${esc(x)}</span>`).join('')}</div></div>`;
    }).join(''):'<div class="subtle">No captain shortlist available yet.</div>';
  }
  async function init(){
    try{
      const r=await fetch(`https://raw.githubusercontent.com/tlaw77/fpl/main/data/latest.json?t=${Date.now()}`,{cache:'no-store'}); if(!r.ok)return;
      const d=await r.json(); const dec=d.next_gw_decisions||{};
      const targets=dec.target_rivals||dec.nearest_rivals||[];
      const t=document.querySelector('#target-rivals');
      if(t) t.innerHTML=targets.length?targets.map((x,i)=>`<div class="target-chip"><strong>${i+1}. ${esc(x.team_name||x.manager||'Rival')}</strong><span>${x.gap_to_me!==undefined?`${x.gap_to_me>0?'+':''}${x.gap_to_me} pts`:''}</span></div>`).join(''):'<div class="subtle">Target rivals are derived from the managers immediately above you.</div>';
      renderCaptain('#protect-captains',dec.protect_captains||dec.protective_captains||dec.captain_candidates,'protect');
      renderCaptain('#chase-captains',dec.chase_captains||dec.aggressive_captains||dec.captain_candidates,'chase');
      renderMove('#protect-moves',dec.protective_transfer_moves||dec.safe_transfer_moves,'protect');
      renderMove('#chase-moves',dec.chase_transfer_moves||dec.aggressive_transfer_moves,'chase');
    }catch(e){console.warn('Explainability layer unavailable',e)}
  }
  return {init};
})();
window.addEventListener('DOMContentLoaded',()=>Explainability.init());
