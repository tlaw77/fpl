(()=>{
const KEY='fplWorkingPlanV2';
const norm=s=>String(s||'').trim().toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'');
const read=()=>{try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}};
const moves=(plan=read())=>(Array.isArray(plan?.moves)?plan.moves:[]).filter(m=>m?.out&&m?.in);
const matches=(p,ref)=>{const id=Number(ref?.player_id),name=norm(ref?.player||ref?.web_name);return !!p&&(id?Number(p.player_id)===id:!!name&&norm(p.player||p.web_name)===name)};
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

let transferBudget=null;
const money=v=>Number.isFinite(Number(v))?Math.round(Number(v)*10):null;
function affordability(ms,core=window.FPLCoreData,budget=transferBudget,catalog=window.FPLPlayerPoolData?.players||[]){
 if(!ms.length)return{ok:true,known:true,remaining:core?.current_bank??core?.me?.bank??0,message:'No spend this gameweek'};
 if(!budget||Number(budget.next_gw)!==Number(core?.next_gw))return{ok:false,known:false,message:'Checking current selling prices…'};
 const held=core?.current_squad_next5||core?.squad_next5||core?.squad||[],sold=new Set(),bought=new Set();
 let balance=money(core?.current_bank??core?.me?.bank??budget.bank);
 if(balance===null)return{ok:false,known:false,message:'Bank balance unavailable'};
 for(const m of ms){
  const out=find(held,m.out),alreadyIn=find(held,m.in);
  if(!out&&alreadyIn)continue;
  const sale=(budget.players||[]).find(p=>matches(p,m.out)),incoming=find(catalog,m.in)||m.in;
  const proceeds=money(sale?.selling_price),cost=money(incoming?.price);
  const oi=Number(m.out?.player_id),ii=Number(m.in?.player_id);
  if(!out||alreadyIn||sold.has(oi)||bought.has(ii)||proceeds===null||cost===null)return{ok:false,known:false,message:'Refresh prices and squad before choosing this route'};
  sold.add(oi);bought.add(ii);balance+=proceeds-cost;
 }
 const remaining=balance/10;
 return{ok:balance>=0,known:true,remaining,shortfall:Math.max(0,-remaining),message:balance<0?`£${(-remaining).toFixed(1)}m short · choose a cheaper route`:`£${remaining.toFixed(1)}m left after transfers`};
}
function decisionBudget(core=window.FPLCoreData){
 const syn=core?.decision_synthesis||{},a=syn.current_action||{};
 if(a.action!=='TRANSFER')return{ok:true,message:''};
 const route=syn.robustness?.active_route||a.headline;
 const option=(syn.transfer_options||[]).find(x=>x.first_action?.route===route);
 const step=option?.first_action;
 if(!step)return{ok:false,known:false,message:'Transfer budget needs revalidation'};
 const transfers=step.transfers?.length?step.transfers:[step];
 return affordability(transfers.map(t=>({out:{player_id:t.out_id},in:{player_id:t.in_id}})),core);
}
window.FPLTransferBudget={evaluate:affordability,decision:decisionBudget,get:()=>transferBudget};
async function loadTransferBudget(){
 try{const r=await fetch('https://raw.githubusercontent.com/tlaw77/fpl/main/data/budget_state.json?budget='+Date.now(),{cache:'no-store'});if(!r.ok)throw new Error('budget');transferBudget=await r.json();window.dispatchEvent(new CustomEvent('fplTransferBudgetReady'))}catch{}
}
window.addEventListener('fplCoreDataReady',loadTransferBudget,{passive:true});
loadTransferBudget();

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
