(()=>{
const BUILD='transfer-hold-authority-20260906-1056';
const q=(s,r=document)=>r.querySelector(s);
const qa=(s,r=document)=>[...r.querySelectorAll(s)];
const text=el=>String(el?.textContent||'').trim();
function action(){return String(window.FPLCoreData?.decision_synthesis?.current_action?.action||'').toUpperCase()}
function hold(){return action()==='HOLD'}
function replaceText(el,re,value){if(!el)return;const s=text(el);if(re.test(s))el.textContent=value}
function enforce(){
  const view=q('#view-transfer');
  if(!view||!hold())return;
  const act=window.FPLCoreData?.decision_synthesis?.current_action||{};
  const syn=window.FPLCoreData?.decision_synthesis||{};
  const edge=Number(syn?.robustness?.single_step_edge_over_hold_6gw);

  const routes=q('[data-safe-routes]',view);
  if(routes){
    const eye=q('.eyebrow',routes),h=q('h3',routes),intro=q('p.subtle',routes);
    if(eye)eye.textContent='ALTERNATIVE ROUTES';
    if(h)h.textContent='Contingencies to the current hold';
    if(intro)intro.textContent='HOLD is the active recommendation. These routes are alternatives only and become actionable if the evidence gate changes.';
    const first=q('.dc-player',routes);
    if(first){
      const strong=q('strong',first);
      if(strong){
        strong.innerHTML=strong.innerHTML
          .replace(/Current model leader\s*[·:-]?\s*/ig,'Best contingency · ')
          .replace(/Model leader\s*[·:-]?\s*/ig,'Best contingency · ')
          .replace(/Decision preferred\s*[·:-]?\s*/ig,'Best contingency · ');
      }
    }
    qa('.dc-player',routes).forEach((card,i)=>{
      const s=q('strong',card);
      if(i===0&&s&&!/best contingency/i.test(text(s)))s.innerHTML=`Best contingency · ${s.innerHTML}`;
    });
    let note=q('[data-hold-authority-note]',routes);
    if(!note){
      note=document.createElement('div');
      note.dataset.holdAuthorityNote='1';
      note.style.cssText='margin:10px 0;padding:9px 10px;border-radius:10px;background:#201a0f;border:1px solid #f59e0b55;color:#fde68a;font-size:10px;line-height:1.45';
      const list=q('.dc-player-list',routes);
      if(list)list.insertAdjacentElement('beforebegin',note);else routes.prepend(note);
    }
    note.textContent=`HOLD gate active${Number.isFinite(edge)?` despite a raw ${edge.toFixed(1)}-point model edge`:''}: the leading route has not cleared the required evidence and cross-model agreement threshold.`;
  }

  const roll=q('[data-roll-choice]',view);
  if(roll){
    const spans=qa('span',roll);
    const badge=spans.find(s=>/TRANSFER HAS EDGE|VIABLE ROLL|STRONG ROLL|VIABLE OPTION/i.test(text(s)));
    if(badge){badge.textContent='HOLD PREFERRED';badge.style.setProperty('color','#34d399','important')}
    const copy=qa('.subtle',roll).find(p=>/current model leader|banking keeps|there is a useful move|rolling still/i.test(text(p)));
    if(copy)copy.textContent=`The raw model has a leading alternative${Number.isFinite(edge)?` (+${edge.toFixed(1)} over hold)`:''}, but it has not cleared the evidence/consensus gate. HOLD remains the recommendation.`;
    const btn=q('[data-roll-button]',roll);
    if(btn&&!/selected/i.test(text(btn)))btn.textContent='Choose hold / bank';
  }

  const hero=q('.transfer-hero',view);
  if(hero){
    const tag=q('.transfer-hero-tag',hero);if(tag)tag.textContent='MODEL ALTERNATIVE';
    const shortlist=q('[data-shortlist-note]',hero);if(shortlist)shortlist.textContent='Highest-ranked alternative only. HOLD remains the active recommendation unless the decision gate changes.';
  }

  qa('[data-leader-calibration]',view).forEach(box=>{
    const strong=q('strong',box);if(strong)strong.textContent='WHY THIS ALTERNATIVE RANKS HIGHEST';
    const status=qa('span',box).find(s=>/STRONG LEADING CASE|SUPPORTED LEADER|MODEL LEADER|TENTATIVE LEADER|NOT ACTIVE ACTION/i.test(text(s)));
    if(status)status.textContent='NOT ACTIVE ACTION';
  });

  document.documentElement.dataset.transferHoldAuthorityBuild=BUILD;
}
function run(){[80,220,500,1000,1800,3000,5000].forEach(ms=>setTimeout(enforce,ms))}
function bind(){
  run();
  ['fplCoreDataReady','fplSafePlanUpdated','fplViewSettled','effectiveSquadRendered'].forEach(ev=>window.addEventListener(ev,run,{passive:true}));
  q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',run,{passive:true});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
