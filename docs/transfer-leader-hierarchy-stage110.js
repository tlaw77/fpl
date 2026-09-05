(()=>{
const BUILD='transfer-leader-hierarchy-20260905-2052';
const q=(s,r=document)=>r.querySelector(s);
const txt=el=>String(el?.textContent||'').trim();
function holding(){return String(window.FPLCoreData?.decision_synthesis?.current_action?.action||'').toUpperCase()==='HOLD'}
function compact(metrics){
  metrics.classList.remove('dc-card');
  metrics.style.cssText='margin:8px 0 0;padding:8px 0 0;border:0;border-top:1px solid rgba(255,255,255,.07);background:transparent;border-radius:0;box-shadow:none;display:grid;grid-template-columns:1fr 1fr;gap:7px';
  const eye=q('.eyebrow',metrics);if(eye)eye.style.display='none';
  metrics.querySelectorAll('p.subtle').forEach(p=>{if(/green gain figures|projected improvements|ownership describes/i.test(txt(p)))p.style.display='none'});
  metrics.querySelectorAll(':scope > div').forEach(c=>{c.style.setProperty('padding','8px','important');c.style.setProperty('border-radius','10px','important')});
}
function apply(){
  const view=q('#view-transfer');if(!view)return;
  const metrics=q('.transfer-metrics',view);if(!metrics)return;
  let discussion=q('[data-model-leader-discussion]',view);
  if(holding()){
    const signal=q('[data-decision-signal]',view);
    if(!signal)return;
    if(!discussion){
      discussion=document.createElement('details');
      discussion.dataset.modelLeaderDiscussion='1';
      discussion.className='txs-details model-leader-discussion';
      discussion.innerHTML='<summary><span>Current model leader · discussion</span><small>Why a route can lead while HOLD remains preferred</small></summary><div data-model-leader-body></div>';
      const signalDetails=signal.querySelector('.txs-details:last-of-type');
      if(signalDetails)signalDetails.insertAdjacentElement('afterend',discussion);else signal.appendChild(discussion);
    }
    const body=q('[data-model-leader-body]',discussion);
    compact(metrics);
    if(body&&metrics.parentElement!==body)body.appendChild(metrics);
    discussion.open=false;
  }else if(discussion){
    const hero=q('.transfer-hero',view);
    if(hero&&metrics.parentElement!==hero)hero.appendChild(metrics);
    discussion.remove();
  }
  document.documentElement.dataset.transferLeaderHierarchyBuild=BUILD;
}
function run(){[120,350,800,1600,2800].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();['fplCoreDataReady','fplSafePlanUpdated','fplViewSettled'].forEach(ev=>window.addEventListener(ev,run,{passive:true}));q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
