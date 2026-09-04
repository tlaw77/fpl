(()=>{
const BUILD='pick-team-delta-stage103-20260904-0106';
const KEY='fplPickTeamCheckpointV1';
const BASE='https://raw.githubusercontent.com/tlaw77/fpl/main/data/';
const q=(s,r=document)=>r.querySelector(s),n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot',"'":'&#039;'}[c]));
let current=null,store={history:[]},persistTimer=null,loading=null;
try{const x=JSON.parse(localStorage.getItem(KEY)||'null');if(x?.history)store=x}catch{}
function loadCalendarWatch(){if(!q('link[data-calendar-watch-css]')){const l=document.createElement('link');l.rel='stylesheet';l.href='calendar-watch-stage106.css?v=20260904-0104';l.dataset.calendarWatchCss='1';document.head.appendChild(l)}if(!q('script[data-calendar-watch-js]')){const s=document.createElement('script');s.src='calendar-watch-stage106.js?v=20260904-0104';s.defer=true;s.dataset.calendarWatchJs='1';document.body.appendChild(s)}}
async function get(name){try{const r=await fetch(`${BASE}${name}?pt103=${Date.now()}`,{cache:'no-store'});return r.ok?await r.json():null}catch{return null}}
function byId(rows){return new Map((rows||[]).map(x=>[Number(x.player_id),x]))}
function snap(latest,review,pool,tc){
 const ids=(review?.recommended_xi_ids||[]).map(Number),bench=(review?.bench_order_ids||[]).map(Number),rows=latest?.current_squad_next5||latest?.squad_next5||latest?.current_squad||latest?.squad||[],pm=byId([...(pool?.players||[]),...rows]);
 const all=[...new Set([...ids,...bench])],players={};
 for(const id of all){const p=pm.get(id)||{},xp=(review?.xi_projection||[]).find(x=>Number(x.player_id)===id),br=(review?.selection_rationale||[]).find(x=>Number(x.player_id)===id);players[id]={id,name:p.player||xp?.player||br?.player||String(id),position:p.position||xp?.position||br?.position||'',xpts:n(xp?.expected_points??br?.expected_points,NaN),availability:n(p.availability,1),news:String(p.news||''),schedule_risk:String(p.schedule_risk||''),midweek_minutes:p.midweek_minutes==null?null:n(p.midweek_minutes)};}
 const formation=['DEF','MID','FWD'].map(pos=>ids.filter(id=>players[id]?.position===pos).length).join('-');
 return{saved_at:new Date().toISOString(),next_gw:n(review?.next_gw||latest?.next_gw),formation,xi:ids,bench,captain:Number(review?.captain?.player_id||0),vice:Number(review?.vice_captain?.player_id||0),confidence:n(review?.confidence),tc_status:String(tc?.decision?.status||''),tc_candidate:Number((tc?.decision?.candidate||tc?.decision?.haaland_current_gw||{}).player_id||0),players};
}
function name(s,id){return s?.players?.[id]?.name||String(id)}
function age(ts){const t=new Date(ts||0).getTime();if(!Number.isFinite(t))return'';const m=Math.max(0,Math.round((Date.now()-t)/60000));if(m<1)return'just now';if(m<60)return`${m}m ago`;const h=Math.floor(m/60);return h<24?`${h}h ago`:`${Math.floor(h/24)}d ago`}
function sameWindow(x){return Number(x?.next_gw)===Number(current?.next_gw)}
function base(){const h=(store.history||[]).filter(x=>x?.saved_at&&sameWindow(x));return h.length?h[h.length-1]:null}
function setDiff(a,b){const B=new Set(b||[]);return (a||[]).filter(x=>!B.has(x))}
function changes(cur,old){
 if(!old)return[{tone:'neutral',label:'Baseline',text:'First Pick Team checkpoint saved for this Gameweek.'}];
 const out=[];
 const promoted=setDiff(cur.xi,old.xi),benched=setDiff(old.xi,cur.xi);
 if(promoted.length||benched.length){const pairs=[];for(let i=0;i<Math.max(promoted.length,benched.length);i++)pairs.push(`${benched[i]?name(old,benched[i]):'—'} → ${promoted[i]?name(cur,promoted[i]):'—'}`);out.push({tone:'watch',label:'Starting XI',text:pairs.join(' · ')});}
 if(cur.formation!==old.formation)out.push({tone:'watch',label:'Formation',text:`${old.formation||'—'} → ${cur.formation}`});
 if(cur.captain!==old.captain)out.push({tone:'strong',label:'Captain',text:`${name(old,old.captain)} → ${name(cur,cur.captain)}`});
 if(cur.vice!==old.vice)out.push({tone:'watch',label:'Vice',text:`${name(old,old.vice)} → ${name(cur,cur.vice)}`});
 if(JSON.stringify(cur.bench)!==JSON.stringify(old.bench)){const order=cur.bench.map(id=>name(cur,id)).join(' · ');out.push({tone:'watch',label:'Bench order',text:order});}
 const pids=[...new Set([...cur.xi,...cur.bench])];
 for(const id of pids){const a=cur.players[id],b=old.players?.[id];if(!a||!b)continue;const dx=Number.isFinite(a.xpts)&&Number.isFinite(b.xpts)?a.xpts-b.xpts:0;if(Math.abs(dx)>=.25)out.push({tone:dx>0?'good':'bad',label:`${a.name} projection`,text:`${dx>0?'+':''}${dx.toFixed(2)} xPts since last check`});if(Math.abs(n(a.availability,1)-n(b.availability,1))>=.05)out.push({tone:a.availability<b.availability?'bad':'good',label:`${a.name} availability`,text:`${Math.round(n(b.availability,1)*100)}% → ${Math.round(n(a.availability,1)*100)}%`});if(a.schedule_risk!==b.schedule_risk&&a.schedule_risk)out.push({tone:/high/i.test(a.schedule_risk)?'bad':'watch',label:`${a.name} workload`,text:`${b.schedule_risk||'clear'} → ${a.schedule_risk}`});if(a.midweek_minutes!==b.midweek_minutes&&a.midweek_minutes!=null)out.push({tone:a.midweek_minutes>60?'watch':'neutral',label:`${a.name} minutes`,text:`${Math.round(a.midweek_minutes)} midweek mins now recorded`});if(a.news!==b.news&&a.news)out.push({tone:'watch',label:`${a.name} news`,text:a.news.slice(0,100)});}
 if(cur.tc_status!==old.tc_status||cur.tc_candidate!==old.tc_candidate){out.push({tone:/consider/i.test(cur.tc_status)?'strong':'watch',label:'Triple Captain',text:`${old.tc_status||'—'} → ${cur.tc_status||'—'}${cur.tc_candidate?` · ${name(cur,cur.tc_candidate)}`:''}`});}
 if(!out.length)out.push({tone:'good',label:'Selection stable',text:'No material XI, bench, captaincy, workload or TC change.'});
 return out.slice(0,6);
}
function summary(ch){if(ch.length===1&&ch[0].label==='Selection stable')return'STABLE';if(ch.length===1&&ch[0].label==='Baseline')return'BASELINE';return `${ch.length} CHANGE${ch.length===1?'':'S'}`}
function render(){const host=q('#dc-team-view'),auth=q('[data-authoritative-pick-team]',host);if(!host||!auth||!current)return;host.querySelector('[data-pick-team-delta]')?.remove();const old=base(),ch=changes(current,old),sec=document.createElement('section');sec.className='pt103-card';sec.dataset.pickTeamDelta='1';const rows=ch.map(x=>`<div class="pt103-change ${x.tone}"><span>${esc(x.label)}</span><strong>${esc(x.text)}</strong></div>`).join('');sec.innerHTML=`<div class="pt103-head"><div><p class="eyebrow">SINCE YOUR LAST PICK TEAM CHECK${old?` · ${esc(age(old.saved_at))}`:''}</p><h3>${ch[0].text}</h3></div><span class="pt103-pill">${esc(summary(ch))}</span></div><div class="pt103-grid">${rows}</div><p class="pt103-note">Deadline monitor: XI/bench swaps, C/VC, projected-points moves, availability, workload/team-news changes and Triple Captain status are compared with your previous Pick Team visit.</p>`;auth.insertAdjacentElement('beforebegin',sec);document.documentElement.dataset.pickTeamDeltaBuild=BUILD}
function persist(){if(!current)return;try{const h=[...(store.history||[])],last=h[h.length-1];if(!last||JSON.stringify({...last,saved_at:''})!==JSON.stringify({...current,saved_at:''}))h.push({...current,saved_at:new Date().toISOString()});else last.saved_at=new Date().toISOString();store={history:h.slice(-32)};localStorage.setItem(KEY,JSON.stringify(store))}catch{}}
async function run(){if(loading)return loading;loading=Promise.all([get('latest.json'),get('captaincy_review.json'),get('player_pool.json'),get('triple_captain_review.json')]).then(([l,r,p,t])=>{if(r?.status!=='SUCCESS')return;current=snap(l,r,p,t);render();clearTimeout(persistTimer);persistTimer=setTimeout(persist,60000)}).finally(()=>loading=null);return loading}
function bind(){loadCalendarWatch();q('#decision-nav button[data-view="team"]')?.addEventListener('click',()=>setTimeout(run,120),{passive:true});window.addEventListener('fplViewSettled',e=>{if(e.detail?.viewName==='team')setTimeout(run,100)},{passive:true});window.addEventListener('fplCoreDataReady',()=>{if(q('.dashboard-view.active')?.id==='view-team')setTimeout(run,180)},{passive:true});window.addEventListener('pagehide',persist,{passive:true});document.addEventListener('visibilitychange',()=>{if(document.visibilityState==='hidden')persist()},{passive:true});if(q('.dashboard-view.active')?.id==='view-team')setTimeout(run,400)}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
