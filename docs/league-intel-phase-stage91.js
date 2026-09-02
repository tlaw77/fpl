(()=>{
const BUILD='league-intel-phase-stage91-20260902-1510';
const q=(s,r=document)=>r.querySelector(s);
let timer=null;
function phase(d){const fs=Array.isArray(d?.current_gw_fixtures)?d.current_gw_fixtures:[];if(!fs.length)return'pre';if(fs.some(f=>f.started&&!f.finished&&!f.finished_provisional))return'live';if(fs.some(f=>!f.finished&&!f.finished_provisional))return'pre';return'complete'}
function matrix(host){return [...host.querySelectorAll(':scope > section, :scope > .dc-card')].find(x=>/MANAGER MATRIX/i.test(x.querySelector('.eyebrow')?.textContent||''))||null}
function nodes(host){return{
 session:q('[data-monitor-session="intel"]',host),
 narrative:q('[data-monitor="narrative"]',host),
 mission:q('[data-monitor-mission]',host),
 swing:q('[data-monitor="swing"]',host),
 scorecards:q('[data-gw-scorecards]',host),
 standings:q('[data-live-standings-card]',host),
 matrix:matrix(host),
 threats:q('[data-threats-leverage-board]',host),
 target:q('[data-target-rival-effective]',host),
 probability:q('[data-monitor="probability"]',host),
 heat:q('[data-monitor="heatmap"]',host)
}}
function label(p){return p==='live'?['LIVE GW','Follow swings and exposure as points land.']:p==='complete'?['POST-GW REVIEW','Review what happened first, then translate it into the next decision window.']:['PRE-GW INTEL','Strategy and exposure first; live-result surfaces move down until kickoff.']}
function mode(host,p){host.querySelector('[data-intel-phase-mode]')?.remove();const [name,copy]=label(p),s=document.createElement('div');s.className=`intel91-mode ${p}`;s.dataset.intelPhaseMode='1';s.innerHTML=`<span>INTEL MODE · ${name}</span><small>${copy}</small>`;const session=q('[data-monitor-session="intel"]',host);if(session)session.insertAdjacentElement('afterend',s);else host.prepend(s);return s}
function order(){const d=window.FPLCoreData,host=document.getElementById('dc-intel-view');if(!d||!host)return;const p=phase(d),x=nodes(host);const desired=p==='live'?
 [x.session,x.swing,x.standings,x.matrix,x.threats,x.target,x.mission,x.probability,x.heat,x.narrative,x.scorecards]:
 p==='complete'?
 [x.session,x.narrative,x.scorecards,x.swing,x.standings,x.matrix,x.mission,x.target,x.threats,x.probability,x.heat]:
 [x.session,x.narrative,x.mission,x.target,x.threats,x.probability,x.heat,x.standings,x.matrix,x.scorecards,x.swing];
 desired.filter(Boolean).reverse().forEach(el=>host.prepend(el));mode(host,p);document.documentElement.dataset.intelPhase=p;document.documentElement.dataset.leagueIntelPhaseBuild=BUILD}
function schedule(){clearTimeout(timer);timer=setTimeout(order,60);[220,650,1400,2800].forEach(ms=>setTimeout(order,ms))}
function bind(){document.querySelector('#decision-nav button[data-view="intel"]')?.addEventListener('click',schedule,{passive:true});window.addEventListener('fplCoreDataReady',schedule,{passive:true});window.addEventListener('fplLeagueIntelRendered',schedule,{passive:true});window.addEventListener('fplViewSettled',e=>{if(e.detail?.viewName==='intel')schedule()},{passive:true});window.addEventListener('fplSafePlanUpdated',schedule,{passive:true});if(document.querySelector('.dashboard-view.active')?.id==='view-intel')schedule()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
