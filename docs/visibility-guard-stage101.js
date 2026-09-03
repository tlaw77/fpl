(()=>{
const BUILD='visibility-guard-stage101-20260903-2048';
const q=(s,r=document)=>r.querySelector(s),qa=(s,r=document)=>[...r.querySelectorAll(s)];
function teamGuard(){const host=q('#dc-team-view');if(!host)return;const authoritative=!!q('[data-authoritative-pick-team]',host);const legacy=qa('[data-pick-orientations],[data-consolidation-group="gw-selection"],.pitch-panel,.pitch-impact,.pitch-bench-panel,.selection-rationale,.captain-rationale',host);if(authoritative){legacy.forEach(el=>{el.style.display='none'})}else{legacy.forEach(el=>{if(el.style.display==='none')el.style.removeProperty('display')});const best=qa('[data-pick-orientations] > div',host).find(el=>/Best Expected XI/i.test(el.querySelector('strong')?.textContent||''));if(best&&best.style.display==='none')best.style.removeProperty('display')}}
function transferGuard(){const view=q('#view-transfer');if(!view)return;const phase=q('[data-transfer-phase]',view);if(!phase)qa('.tx-completed-duplicate',view).forEach(el=>el.classList.remove('tx-completed-duplicate'))}
function run(){teamGuard();transferGuard();document.documentElement.dataset.visibilityGuardBuild=BUILD}
function schedule(){requestAnimationFrame(run);setTimeout(run,180);setTimeout(run,650)}
function bind(){schedule();qa('#decision-nav button[data-view]').forEach(b=>b.addEventListener('click',schedule,{passive:true}));window.addEventListener('fplCoreDataReady',schedule,{passive:true});window.addEventListener('fplSafePlanUpdated',schedule,{passive:true});window.addEventListener('fplViewSettled',schedule,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
