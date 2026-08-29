(()=>{
const BUILD='transfer-hero-evidence-stage45-20260829-1204';
function q(s,r=document){return r.querySelector(s)}
function compact(){
 const view=q('#view-transfer');if(!view)return;
 const hero=q('.transfer-hero',view),ev=q('.transfer-evidence,[data-stage9-evidence]',view);if(!hero||!ev||ev===hero||hero.contains(ev))return;
 const head=q('.panel-head',ev),conf=q('.dc-confidence',ev),toggle=q('.tx-evidence-toggle',ev);
 const level=(conf?.textContent||'Evidence').trim();
 if(head){
   const eye=q('.eyebrow',head),h=q('h3',head);
   if(eye)eye.textContent='EVIDENCE';
   if(h)h.textContent=level;
   if(conf)conf.remove();
   if(toggle){toggle.textContent='Evidence details';toggle.style.marginLeft='auto'}
 }
 ev.classList.remove('dc-card');
 ev.style.cssText='margin:14px 0 0;padding:12px 0 0;border:0;border-top:1px solid #285547;background:transparent;border-radius:0;box-shadow:none';
 hero.appendChild(ev);
 const old=q('[data-shortlist-note]',hero);if(old)old.remove();
 const desc=[...hero.querySelectorAll('p')].find(p=>/Recommended from the current model/i.test(p.textContent||''));
 if(desc)desc.textContent='Current model leader from fixtures, availability, model and mini-league context. Evidence below shows how strongly the incoming player is corroborated.';
 document.documentElement.dataset.transferHeroEvidenceBuild=BUILD;
}
function run(){[180,600,1200,2000].forEach(ms=>setTimeout(compact,ms))}
function bind(){run();q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',run,{passive:true});window.addEventListener('fplSafePlanUpdated',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
