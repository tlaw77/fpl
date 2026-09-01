(()=>{
const BUILD='league-gw-status-stage81-20260901-2245';
let data=window.FPLCoreData||null;
const q=(s,r=document)=>r.querySelector(s);
function phase(d){
 const fs=Array.isArray(d?.current_gw_fixtures)?d.current_gw_fixtures:[];
 if(!fs.length)return{key:'unknown',label:`GW${d?.current_gw||'—'} status`,title:'League table'};
 const live=fs.some(f=>f.started&&!f.finished&&Number(f.minutes||0)>0&&Number(f.minutes||0)<90);
 const unfinished=fs.some(f=>!f.finished&&!f.finished_provisional);
 if(live)return{key:'live',label:`GW${d.current_gw} LIVE`,title:'Live league table'};
 if(unfinished)return{key:'active',label:`GW${d.current_gw} ACTIVE`,title:'Live league table'};
 return{key:'complete',label:`GW${d.current_gw} COMPLETE`,title:`Final GW${d.current_gw} league table`};
}
function apply(){
 const card=q('[data-live-standings-card]');
 if(!card||!data)return;
 const p=phase(data),head=q('.panel-head',card),status=head?.querySelector('.subtle'),title=head?.querySelector('h3');
 if(status)status.textContent=p.label;
 if(title)title.textContent=p.title;
 const expl=[...card.querySelectorAll('p.subtle')].find(x=>/Overall = completed total before this GW/i.test(x.textContent||''));
 if(expl&&p.key==='complete')expl.textContent=`Overall includes the final GW${data.current_gw} score. Rank arrows compare the final position with the previous completed gameweek. Tap a rival to see their squad analysis.`;
 card.dataset.gwStatus=p.key;
 document.documentElement.dataset.leagueGwStatusBuild=BUILD;
}
function later(){requestAnimationFrame(apply);setTimeout(apply,180)}
function bind(){
 data=window.FPLCoreData||data;later();
 window.addEventListener('fplLeagueIntelRendered',later,{passive:true});
 window.addEventListener('fplCoreDataReady',e=>{data=e.detail||window.FPLCoreData||data;later()},{passive:true});
 window.addEventListener('fplViewSettled',e=>{if(e.detail?.viewName==='intel')later()},{passive:true});
 q('#decision-nav button[data-view="intel"]')?.addEventListener('click',later,{passive:true});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
