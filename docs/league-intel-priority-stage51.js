(()=>{
const BUILD='league-intel-priority-stage51-20260831-0034';
function matrix(){return [...document.querySelectorAll('#dc-intel-view > section, #dc-intel-view .dc-card')].find(s=>/MANAGER MATRIX/i.test(s.querySelector('.eyebrow')?.textContent||''))}
function standings(){return document.querySelector('#dc-intel-view [data-live-standings-card]')}
function threats(){return document.querySelector('#dc-intel-view [data-threats-leverage-board]')}
function apply(){const host=document.getElementById('dc-intel-view'),m=matrix(),s=standings();if(!host||!m||!s)return;const t=threats();if(t){if(t.previousElementSibling!==s)s.insertAdjacentElement('afterend',t);if(m.previousElementSibling!==t)t.insertAdjacentElement('afterend',m)}else if(m.previousElementSibling!==s)s.insertAdjacentElement('afterend',m);document.documentElement.dataset.leagueIntelPriorityBuild=BUILD}
function run(){[120,350,800,1500,2400].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();document.querySelector('#decision-nav button[data-view="intel"]')?.addEventListener('click',run,{passive:true});window.addEventListener('fplCoreDataReady',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();