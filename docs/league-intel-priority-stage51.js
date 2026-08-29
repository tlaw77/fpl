(()=>{
const BUILD='league-intel-priority-stage51-20260829-1408';
function matrix(){return [...document.querySelectorAll('#dc-intel-view > section, #dc-intel-view .dc-card')].find(s=>/MANAGER MATRIX/i.test(s.querySelector('.eyebrow')?.textContent||''))}
function apply(){const host=document.getElementById('dc-intel-view'),m=matrix();if(!host||!m)return;if(host.firstElementChild!==m)host.prepend(m);document.documentElement.dataset.leagueIntelPriorityBuild=BUILD}
function run(){[250,700,1400,2300].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();document.querySelector('#decision-nav button[data-view="intel"]')?.addEventListener('click',run,{passive:true});window.addEventListener('fplCoreDataReady',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();