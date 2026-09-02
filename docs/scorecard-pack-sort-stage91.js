(()=>{
const BUILD='scorecard-pack-sort-stage91-20260902-1242';
function score(row){const b=row.querySelector(':scope > b');const v=Number((b?.textContent||'').trim());return Number.isFinite(v)?v:-999}
function sortGroup(group){const rows=[...group.children].filter(x=>x.classList?.contains('gw87-pack-row'));rows.sort((a,b)=>score(b)-score(a));rows.forEach(r=>group.appendChild(r))}
function apply(){const host=document.getElementById('dc-intel-view');if(!host)return;host.querySelectorAll('[data-gw-scorecards] .gw87-pack-cols').forEach(cols=>{[...cols.children].forEach(sortGroup)});document.documentElement.dataset.scorecardPackSortBuild=BUILD}
function schedule(){[40,140,400].forEach(ms=>setTimeout(apply,ms))}
function bind(){window.addEventListener('fplViewSettled',e=>{if(e.detail?.viewName==='intel')schedule()},{passive:true});window.addEventListener('fplCoreDataReady',schedule,{passive:true});document.querySelector('#decision-nav button[data-view="intel"]')?.addEventListener('click',schedule,{passive:true});schedule()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
