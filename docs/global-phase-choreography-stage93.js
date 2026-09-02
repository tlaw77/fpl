(()=>{
const BUILD='global-phase-choreography-stage93-20260902-1514';
const q=(s,r=document)=>r.querySelector(s);
function data(){return window.FPLCoreData||{}}
function phase(d){const fs=Array.isArray(d?.current_gw_fixtures)?d.current_gw_fixtures:[];if(fs.some(f=>f.started&&!f.finished&&!f.finished_provisional))return'live';if(fs.some(f=>!f.finished&&!f.finished_provisional))return'pre';return'post'}
const COPY={
 transfer:{pre:['PRE-GW DECISION','Decide only when the evidence clears the gate. Decision state and deadline information come first.'],live:['LIVE GW · OBSERVE','Avoid manufacturing transfers during live play. Monitor workload, injuries and decision stability first.'],post:['POST-GW · REASSESS','Review what changed, then reopen the next-GW decision with fresh evidence.']},
 team:{pre:['PRE-GW SELECTION','XI, captain and availability decisions come first before the deadline.'],live:['LIVE XI','Follow captaincy, players in action and bench consequences while the round is live.'],post:['POST-GW SELECTION REVIEW','Review captain and XI execution, then use new evidence to shape the next team.']},
 shape:{pre:['PRE-GW STRUCTURE','Prioritise squad balance, fixtures and useful leverage before locking the week.'],live:['LIVE STRUCTURAL EXPOSURE','Ownership, leverage and role exposure matter most while points are landing.'],post:['POST-GW STRUCTURE REVIEW','See what the squad structure revealed, then reassess roles and forward strength.']},
 pool:{pre:['PRE-GW PLAYER MARKET','Actionable targets first; role, fixtures and price context support the shortlist.'],live:['LIVE EVIDENCE','Minutes, roles and new information matter more than raw rankings while matches are being played.'],post:['POST-GW DISCOVERY','New roles, emerging options and updated evidence lead; rankings follow after the review.']}
};
const RULES={
 transfer:{
  pre:[[/SINCE YOUR LAST CHECK/,0],[/DECISION TIMELINE|HOW THE DECISION HAS EVOLVED/,10],[/CURRENT ACTION|DECISION SIGNAL|GAMEWEEK DECISION|TRANSFER PHASE/,20],[/PRESSURE INDEX/,30],[/WEEKEND WATCHLIST|WORKLOAD/,40],[/WHY HOLD|DECISION LENS/,50],[/CONTINGENC|ALTERNATIVE|ROUTE|SHORTLIST/,60],[/HISTORY|JOURNAL/,80]],
  live:[[/SINCE YOUR LAST CHECK/,0],[/WEEKEND WATCHLIST|WORKLOAD|AVAILABILITY|MINUTES/,10],[/TRANSFER PHASE|CURRENT ACTION|DECISION SIGNAL/,20],[/DECISION TIMELINE/,30],[/PRESSURE INDEX/,40],[/WHY HOLD/,50],[/CONTINGENC|ALTERNATIVE|ROUTE|SHORTLIST/,80]],
  post:[[/SINCE YOUR LAST CHECK/,0],[/DECISION TIMELINE/,10],[/TRANSFER PHASE|CURRENT ACTION|DECISION SIGNAL/,20],[/PRESSURE INDEX/,30],[/WEEKEND WATCHLIST|WORKLOAD/,40],[/WHY HOLD/,50],[/CONTINGENC|ALTERNATIVE|ROUTE|SHORTLIST/,60],[/HISTORY|JOURNAL/,70]]
 },
 team:{
  pre:[[/RECOMMENDED XI|PICK TEAM|STARTING XI|XI FOR/,0],[/CAPTAIN/,10],[/WEEKEND WATCHLIST|WORKLOAD|AVAILABILITY|MINUTES/,20],[/BENCH|SUBSTITUTE/,30],[/FIXTURE|OUTLOOK/,40],[/CHIP/,50]],
  live:[[/CAPTAIN|LIVE/,0],[/WEEKEND WATCHLIST|WORKLOAD|MINUTES|AVAILABILITY/,10],[/BENCH|SUBSTITUTE/,20],[/XI|PICK TEAM/,30],[/OUTLOOK|FIXTURE/,40],[/CHIP/,60]],
  post:[[/REVIEW|OUTCOME|RESULT/,0],[/CAPTAIN/,10],[/BENCH|XI EFFICIENCY|SELECTION/,20],[/WEEKEND WATCHLIST|WORKLOAD|AVAILABILITY/,30],[/OUTLOOK|NEXT/,40],[/CHIP/,50]]
 },
 shape:{
  pre:[[/SQUAD SHAPE|STRUCTURE|BALANCE|FORMATION/,0],[/FIXTURE|OUTLOOK/,10],[/DIFFERENTIAL|LEVERAGE|OWNERSHIP/,20],[/ATTACKING ROLE|OOP|ADVANCED ROLE/,30],[/DEFENSIVE CONTRIBUT|DC /,40],[/CHIP/,50]],
  live:[[/DIFFERENTIAL|LEVERAGE|OWNERSHIP|EXPOSURE/,0],[/ATTACKING ROLE|OOP|ADVANCED ROLE/,10],[/DEFENSIVE CONTRIBUT|DC /,20],[/STRUCTURE|SQUAD SHAPE|BALANCE/,30],[/FIXTURE|OUTLOOK/,40]],
  post:[[/REVIEW|RESULT|OUTCOME/,0],[/STRUCTURE|SQUAD SHAPE|BALANCE/,10],[/ATTACKING ROLE|OOP|ADVANCED ROLE|ROLE/,20],[/DIFFERENTIAL|LEVERAGE|OWNERSHIP/,30],[/FIXTURE|OUTLOOK/,40],[/CHIP/,50]]
 },
 pool:{
  pre:[[/SHORTLIST|TARGET|TRANSFER|TOP PICKS|PLAYER RANKINGS/,0],[/POST-WINDOW|NEW OPTION|ROLE WINNER|ROLE PRESSURE/,10],[/ATTACKING ROLE|OOP|ADVANCED ROLE/,20],[/FIXTURE|SCHEDULE/,30],[/MARKET|PRICE/,40],[/CONFIDENCE|SCOUT/,50]],
  live:[[/MINUTES|WORKLOAD|AVAILABILITY|ROLE|ATTACKING ROLE|OOP/,0],[/POST-WINDOW|NEW OPTION/,10],[/FIXTURE|SCHEDULE/,20],[/MARKET|PRICE/,30],[/PLAYER RANKINGS|SHORTLIST|TARGET/,40],[/SCOUT|CONFIDENCE/,50]],
  post:[[/POST-WINDOW|NEW OPTION|ROLE WINNER|ROLE PRESSURE|EMERGING/,0],[/ATTACKING ROLE|OOP|ADVANCED ROLE|ROLE/,10],[/PLAYER RANKINGS|SHORTLIST|TARGET/,20],[/FIXTURE|SCHEDULE/,30],[/MARKET|PRICE/,40],[/SCOUT|CONFIDENCE/,50]]
 }
};
function text(el){return String(el?.textContent||'').replace(/\s+/g,' ').trim().toUpperCase()}
function priority(el,rules,index){const t=text(el);for(const [re,p] of rules){if(re.test(t))return p}return 500+index}
function sortChildren(host,rules){if(!host)return;const kids=[...host.children].filter(x=>x.nodeType===1&&!x.dataset.phaseModeStrip);if(kids.length<2)return;const ranked=kids.map((el,i)=>({el,i,p:priority(el,rules,i)})).sort((a,b)=>a.p-b.p||a.i-b.i);ranked.forEach(x=>host.appendChild(x.el))}
function strip(view,name,p){view.querySelector(':scope > [data-phase-mode-strip]')?.remove();const [title,body]=COPY[name]?.[p]||['GAMEWEEK MODE',''];const s=document.createElement('section');s.className=`phase93-strip ${p}`;s.dataset.phaseModeStrip='1';s.innerHTML=`<div><span>${title}</span><strong>${body}</strong></div><b>${p==='pre'?'BEFORE':p==='live'?'LIVE':'AFTER'}</b>`;view.prepend(s)}
function organise(name){if(name==='intel')return;const d=data();if(!d.current_gw)return;const p=phase(d),view=q(`#view-${name}`);if(!view)return;strip(view,name,p);const rules=RULES[name]?.[p]||[];if(name==='transfer'){sortChildren(view,rules);sortChildren(q('#dc-transfer-view'),rules)}else if(name==='team')sortChildren(q('#dc-team-view'),rules);else if(name==='shape')sortChildren(q('#dc-shape-view'),rules);else if(name==='pool')sortChildren(q('#dc-pool-view'),rules);view.dataset.phaseOrganisation=p;document.documentElement.dataset.globalPhaseChoreographyBuild=BUILD}
function active(){return q('.dashboard-view.active')?.id?.replace('view-','')}
function schedule(name){[40,180,520].forEach(ms=>setTimeout(()=>organise(name),ms))}
function bind(){['transfer','team','shape','pool'].forEach(name=>q(`#decision-nav button[data-view="${name}"]`)?.addEventListener('click',()=>schedule(name),{passive:true}));window.addEventListener('fplCoreDataReady',()=>{const a=active();if(a&&a!=='intel')schedule(a)},{passive:true});window.addEventListener('fplViewSettled',e=>{const name=e.detail?.viewName;if(name&&name!=='intel')schedule(name)},{passive:true});window.addEventListener('fplSafePlanUpdated',()=>{const a=active();if(a&&a!=='intel')schedule(a)},{passive:true});const a=active();if(a&&a!=='intel')schedule(a)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
