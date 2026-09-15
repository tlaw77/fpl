(()=>{
const KEY='fplWorkingPlanV2';
const norm=s=>String(s||'').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
const read=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}};
const moves=(plan=read())=>(Array.isArray(plan?.moves)?plan.moves:[]).filter(m=>m?.out&&m?.in);
const matches=(p,ref)=>{const id=Number(ref?.player_id);return !!p&&((id&&Number(p.player_id)===id)||norm(p.player||p.web_name)===norm(ref?.player||ref?.web_name))};
const find=(rows,ref)=>(rows||[]).find(p=>matches(p,ref));
function state(base,plan=read()){
 const ms=moves(plan),rows=base||[];
 return ms.map(move=>({move,hasOut:!!find(rows,move.out),hasIn:!!find(rows,move.in)}));
}
function pending(base,plan=read()){return state(base,plan).some(x=>x.hasOut&&!x.hasIn)}
function apply(base,catalog=[],plan=read()){
 const original=(base||[]).map(p=>({...p,_cap:false,_vice:false})),steps=state(original,plan);
 if(!steps.length||steps.some(x=>!x.hasOut&&!x.hasIn))return original;
 let rows=original;
 for(const {move,hasOut,hasIn} of steps){
  const outgoing=find(rows,move.out);
  if(hasOut)rows=rows.filter(p=>!matches(p,move.out));
  if(!hasIn&&!find(rows,move.in)){
   const resolved=find(catalog,move.in)||move.in;
   const selection=outgoing?{slot:outgoing.slot,starter:outgoing.starter,multiplier:outgoing.multiplier}:{};
   rows.push({...move.in,...resolved,...selection,_planned:true,_cap:false,_vice:false});
  }else rows=rows.map(p=>matches(p,move.in)?{...p,_planned:true}:p);
 }
 return rows;
}
function label(plan=read()){return moves(plan).map(m=>`${m.out.player||'—'} → ${m.in.player||'—'}`).join(' + ')}
function priceDelta(plan=read()){return moves(plan).reduce((sum,m)=>sum+(Number(m.out?.price)||0)-(Number(m.in?.price)||0),0)}
function ids(side,plan=read()){return new Set(moves(plan).map(m=>Number(m?.[side]?.player_id)).filter(Boolean))}
window.FPLWorkingPlan={KEY,read,moves,matches,find,state,pending,apply,label,priceDelta,ids};
function setText(el,value){if(el&&el.textContent!==value)el.textContent=value}
function syncPresentation(){
 const ms=moves();if(ms.length<2)return;
 const team=document.getElementById('dc-team-view'),full=label();if(!team)return;
 [...team.querySelectorAll('section')].forEach(sec=>{
  const eyebrow=sec.querySelector('.eyebrow');
  if(eyebrow?.textContent.trim()==='YOUR SELECTED TRANSFER'){
   setText(eyebrow,'YOUR SELECTED TRANSFERS');setText(sec.querySelector('h2'),full);
  }
 });
 const outcome=team.querySelector('#selected-transfer-outcome');
 if(outcome){
  setText(outcome.querySelector('.eyebrow'),'YOUR WORKING TRANSFERS · THIS GW');
  setText(outcome.querySelector('h3'),`${full} applied`);
  setText(outcome.querySelector('span'),`${ms.length} MOVES`);
  const cards=[...team.querySelectorAll('.pitch-player-card')],statuses=ms.map(m=>{
   const name=norm(m.in.player),card=cards.find(x=>norm(x.textContent).includes(name));
   return `${m.in.player}: ${card?.closest('.pitch-bench')?'benched':card?'starts':'in squad'}`;
  });
  setText(outcome.querySelector('p.subtle'),`The complete selected route is applied to the effective squad. ${statuses.join(' · ')}.`);
 }
}
function bind(){syncPresentation();new MutationObserver(()=>syncPresentation()).observe(document.body,{childList:true,subtree:true});window.addEventListener('fplSafePlanUpdated',()=>setTimeout(syncPresentation,80))}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
document.documentElement.dataset.workingPlanMultiBuild='stage118-20260915-1';
})();
