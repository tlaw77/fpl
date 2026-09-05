(()=>{
const BUILD='scorecard-pack-sort-stage91-20260905-1414';
function score(row){const b=row.querySelector(':scope > b');const v=Number((b?.textContent||'').trim());return Number.isFinite(v)?v:-999}
function sortGroup(group){const rows=[...group.children].filter(x=>x.classList?.contains('gw87-pack-row'));rows.sort((a,b)=>score(b)-score(a));rows.forEach(r=>group.appendChild(r))}
function apply(){document.querySelectorAll('[data-gw-scorecards] .gw87-pack-cols').forEach(cols=>{[...cols.children].forEach(sortGroup)});document.documentElement.dataset.scorecardPackSortBuild=BUILD}
function schedule(){[40,140,400].forEach(ms=>setTimeout(apply,ms))}
function bind(){window.addEventListener('fplViewSettled',e=>{if(e.detail?.viewName==='intel'||e.detail?.viewName==='shape')schedule()},{passive:true});window.addEventListener('fplCoreDataReady',schedule,{passive:true});['intel','shape'].forEach(name=>document.querySelector(`#decision-nav button[data-view="${name}"]`)?.addEventListener('click',schedule,{passive:true}));schedule()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
