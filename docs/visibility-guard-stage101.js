(()=>{
const BUILD='visibility-guard-stage101-20260903-2346';
const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)];
function hideBestOrientation(host){const sec=q('[data-pick-orientations]',host);if(!sec)return;const best=qa(':scope > div',sec).find(el=>/Best Expected XI/i.test(el.querySelector('strong')?.textContent||''));if(best)best.style.display='none'}
function teamGuard(){const host=q('#dc-team-view');if(!host)return;const authoritative=!!q('[data-authoritative-pick-team]',host);const conflicting=qa('.pitch-panel,.pitch-bench-panel,.selection-rationale',host);const supporting=qa('[data-pick-orientations],.pitch-impact,.captain-rationale,[data-consolidation-group="gw-selection"]',host);if(authoritative){conflicting.forEach(el=>{el.style.display='none'});supporting.forEach(el=>el.style.removeProperty('display'));hideBestOrientation(host)}else{conflicting.concat(supporting).forEach(el=>{if(el.style.display==='none')el.style.removeProperty('display')})}}
function transferGuard(){const view=q('#view-transfer');if(!view)return;const phase=q('[data-transfer-phase]',view);if(!phase)qa('.tx-completed-duplicate',view).forEach(el=>el.classList.remove('tx-completed-duplicate'))}
function run(){teamGuard();transferGuard();document.documentElement.dataset.visibilityGuardBuild=BUILD}
function schedule(){requestAnimationFrame(run);setTimeout(run,180);setTimeout(run,650)}
function bind(){schedule();qa('#decision-nav button[data-view]').forEach(b=>b.addEventListener('click',schedule,{passive:true}));window.addEventListener('fplCoreDataReady',schedule,{passive:true});window.addEventListener('fplSafePlanUpdated',schedule,{passive:true});window.addEventListener('fplViewSettled',schedule,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();