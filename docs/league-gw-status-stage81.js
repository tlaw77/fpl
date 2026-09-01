(()=>{
const BUILD='league-gw-status-stage81-20260901-2310';
let data=window.FPLCoreData||null;
const q=(s,r=document)=>r.querySelector(s);
const qa=(s,r=document)=>[...r.querySelectorAll(s)];
function phase(d){
 const fs=Array.isArray(d?.current_gw_fixtures)?d.current_gw_fixtures:[];
 if(!fs.length)return{key:'unknown',label:`GW${d?.current_gw||'—'} status`,title:'League table'};
 const live=fs.some(f=>f.started&&!f.finished&&!f.finished_provisional);
 const unfinished=fs.some(f=>!f.finished&&!f.finished_provisional);
 if(live)return{key:'live',label:`GW${d.current_gw} LIVE`,title:'Live league table'};
 if(unfinished)return{key:'active',label:`GW${d.current_gw} ACTIVE`,title:'Live league table'};
 return{key:'complete',label:`GW${d.current_gw} COMPLETE`,title:`Final GW${d.current_gw} league table`};
}
function normalizeStandings(card,p){
 const head=q('.panel-head',card),status=head?.querySelector('.subtle'),title=head?.querySelector('h3');
 if(status)status.textContent=p.label;
 if(title)title.textContent=p.title;
 const expl=qa('p.subtle',card).find(x=>/Overall = completed total before this GW|Overall includes the final GW/i.test(x.textContent||''));
 if(expl){
   expl.textContent=p.key==='complete'
    ?`Overall includes the final GW${data.current_gw} score. Rank arrows compare the final position with the previous completed gameweek. Tap a rival to see their squad analysis.`
    :`Overall = completed total before this GW + current GW score. Rank arrows compare the current position with the previous completed gameweek. Tap a rival to see their squad analysis.`;
 }
 const cols=qa('div',card).find(x=>x.children?.length===5&&/POS/i.test(x.children?.[0]?.textContent||'')&&/TEAM/i.test(x.children?.[1]?.textContent||''));
 if(cols?.children?.[2])cols.children[2].textContent=p.key==='complete'?`GW${data.current_gw}`:'Live';
 card.dataset.gwStatus=p.key;
}
function normalizeMatrix(p){
 const sec=qa('#view-intel .dc-card').find(s=>/MANAGER MATRIX/i.test(q('.eyebrow',s)?.textContent||''));
 if(!sec)return;
 const complete=p.key==='complete';
 qa('[title]',sec).forEach(el=>{
   const t=el.getAttribute('title')||'';
   if(/^Live GW score\b/i.test(t))el.setAttribute('title',complete?t.replace(/^Live GW score/i,`GW${data.current_gw} score`):t.replace(/^GW\d+ score/i,'Live GW score'));
 });
 qa('[data-pending-legend]',sec).forEach(el=>{
   el.hidden=complete;
   if(!complete)el.textContent='■ yet to return';
 });
 const progress=qa('[data-live-xi-progress]',sec);
 if(complete)progress.forEach(el=>{if(/complete/i.test(el.textContent||''))el.textContent=el.textContent.replace(/\s*·\s*complete/i,' · final')});
 sec.dataset.gwStatus=p.key;
}
function apply(){
 if(!data)return;
 const p=phase(data),card=q('[data-live-standings-card]');
 if(card)normalizeStandings(card,p);
 normalizeMatrix(p);
 document.documentElement.dataset.leagueGwStatus=p.key;
 document.documentElement.dataset.leagueGwStatusBuild=BUILD;
}
function later(){requestAnimationFrame(apply);setTimeout(apply,180);setTimeout(apply,600)}
function bind(){
 data=window.FPLCoreData||data;later();
 window.addEventListener('fplLeagueIntelRendered',later,{passive:true});
 window.addEventListener('fplCoreDataReady',e=>{data=e.detail||window.FPLCoreData||data;later()},{passive:true});
 window.addEventListener('fplViewSettled',e=>{if(e.detail?.viewName==='intel')later()},{passive:true});
 q('#decision-nav button[data-view="intel"]')?.addEventListener('click',later,{passive:true});
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
