(()=>{
const BUILD='league-matrix-pending-stage66-20260830-0018';
let observer=null,timer=null;
function matrix(){return [...document.querySelectorAll('#view-intel .dc-card')].find(s=>/MANAGER MATRIX/i.test(s.querySelector('.eyebrow')?.textContent||''))}
function isZeroActiveTitle(t){if(!t||/bench/i.test(t))return false;return /:\s*0\s*pts\b/i.test(t)||/·\s*0\s*raw pts\b/i.test(t)}
function paint(){const sec=matrix();if(!sec)return;sec.querySelectorAll('[title]').forEach(el=>{const t=el.getAttribute('title')||'';if(!isZeroActiveTitle(t))return;el.dataset.pendingReturn='1';el.style.background='#1e293b';el.style.color='#cbd5e1';if(!/captain/i.test(t))el.style.border='1px solid #64748b';});const legend=[...sec.querySelectorAll('div')].find(el=>/low/i.test(el.textContent||'')&&/high/i.test(el.textContent||''));if(legend&&!legend.querySelector('[data-pending-legend]')){const item=document.createElement('span');item.dataset.pendingLegend='1';item.style.color='#cbd5e1';item.textContent='■ 0 / no return yet';legend.insertBefore(item,legend.children[1]||null)}document.documentElement.dataset.leagueMatrixPendingBuild=BUILD}
function schedule(){clearTimeout(timer);timer=setTimeout(paint,80)}
function watch(){const view=document.getElementById('view-intel');if(!view||observer)return;observer=new MutationObserver(schedule);observer.observe(view,{childList:true,subtree:true});schedule()}
function bind(){watch();document.querySelector('#decision-nav button[data-view="intel"]')?.addEventListener('click',()=>setTimeout(paint,180),{passive:true});window.addEventListener('fplCoreDataReady',()=>setTimeout(paint,500),{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();