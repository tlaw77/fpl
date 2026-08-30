(()=>{
const BUILD='league-intel-priority-stage51-20260831-0043';
function matrix(){return [...document.querySelectorAll('#dc-intel-view > section, #dc-intel-view .dc-card')].find(s=>/MANAGER MATRIX/i.test(s.querySelector('.eyebrow')?.textContent||''))}
function standings(){return document.querySelector('#dc-intel-view [data-live-standings-card]')}
function threats(){return document.querySelector('#dc-intel-view [data-threats-leverage-board]')}
function apply(){
  const host=document.getElementById('dc-intel-view'),m=matrix();
  if(!host||!m)return;
  if(host.firstElementChild!==m)host.prepend(m);
  const s=standings(),t=threats();
  if(s&&t&&t.previousElementSibling!==s)s.insertAdjacentElement('afterend',t);
  document.documentElement.dataset.leagueIntelPriorityBuild=BUILD;
}
function run(){[120,350,800,1500,2400].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();document.querySelector('#decision-nav button[data-view="intel"]')?.addEventListener('click',run,{passive:true});window.addEventListener('fplCoreDataReady',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();