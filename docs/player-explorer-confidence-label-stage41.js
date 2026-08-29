(()=>{
const BUILD='player-explorer-confidence-label-20260829-1038';
function apply(){const host=document.querySelector('[data-gap-pool]');if(!host)return;[...host.querySelectorAll('.subtle')].forEach(el=>{const t=(el.textContent||'').trim();if(/6-GW view\s*·\s*reliability\s*\d+%/i.test(t))el.textContent=t.replace(/reliability/i,'Model confidence')});document.documentElement.dataset.playerExplorerConfidenceLabelBuild=BUILD}
function settle(){[40,180,500].forEach(ms=>setTimeout(apply,ms))}
function bind(){document.querySelector('#decision-nav button[data-view="pool"]')?.addEventListener('click',settle,{passive:true});window.addEventListener('fplCoreDataReady',settle,{passive:true});if(document.querySelector('.dashboard-view.active')?.id==='view-pool')settle()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
