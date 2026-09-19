(()=>{
const BUILD='position-aware-kpis-stage116-20260919-4';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
const signed=v=>`${v>0?'+':v<0?'−':''}${Math.abs(v)}`;
const kpi=(label,value,note='',kind='')=>`<div class="kpi"${kind?` data-kpi-kind="${kind}"`:''}><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(value)}</div><div class="kpi-note">${esc(note)}</div></div>`;
let rendering=false,lastSignature='';
function rows(d){const me=d?.me||{},rivals=Array.isArray(d?.rivals)?d.rivals:[],mine=n(me.total_points),rank=n(me.rank,99),live=n(me.live_calculated_points??me.gw_points),avg=d?.league?.average_live_calculated_points,bank=n(d?.current_bank??me.bank),bankNote=d?.current_bank!=null&&n(d.current_bank)!==n(me.bank)?'Post-transfer bank':`TV £${n(me.team_value).toFixed(1)}m`,sorted=[...rivals].sort((a,b)=>n(b.total_points)-n(a.total_points)),leader=sorted[0],second=sorted[0],above=sorted.filter(x=>n(x.total_points)>mine).sort((a,b)=>n(a.total_points)-n(b.total_points))[0],isLeader=rank===1&&(!leader||mine>=n(leader.total_points));
const common=[kpi('Rank',`#${me.rank??'—'}`,`${d?.league?.manager_count||0} managers`),kpi('Live GW',live||live===0?live:'—',avg!=null?`League avg ${n(avg).toFixed(1)}`:'')];
if(isLeader){const lead=second?mine-n(second.total_points):0,secondLive=second?n(second.live_calculated_points??second.gw_points):0,gwDelta=live-secondLive,trend=gwDelta>0?'↑':gwDelta<0?'↓':'→';return {mode:'leader',html:[...common,kpi(lead===0?'Joint lead':'Lead',lead===0?'Level':`+${lead}`,second?.team_name||'No rival','lead'),kpi('GW vs #2',`${signed(gwDelta)} ${trend}`,gwDelta>0?'Lead growing':gwDelta<0?'Lead shrinking':'Holding level',gwDelta>0?'growing':gwDelta<0?'shrinking':'level'),kpi('Bank',`£${bank.toFixed(1)}m`,bankNote)].join('')};}
const leaderPoints=Math.max(mine,...rivals.map(x=>n(x.total_points))),gapLeader=Math.max(0,leaderPoints-mine);return {mode:'chasing',html:[...common,kpi('Gap to leader',gapLeader,gapLeader===0?'Level on points':'points'),kpi('Gap to next',above?n(above.total_points)-mine:0,above?.team_name||'No one above'),kpi('Bank',`£${bank.toFixed(1)}m`,bankNote)].join('')};}
function render(d=window.FPLCoreData){const host=document.getElementById('kpi-grid');if(!host||!d||rendering)return;const out=rows(d),signature=`${out.mode}|${out.html}`;if(signature===lastSignature&&host.dataset.positionKpis===BUILD&&host.innerHTML===out.html)return;rendering=true;host.innerHTML=out.html;host.dataset.positionKpis=BUILD;host.dataset.positionMode=out.mode;document.documentElement.dataset.positionKpisBuild=BUILD;lastSignature=signature;rendering=false;}
window.addEventListener('fplCoreDataReady',e=>render(e.detail));
if(window.FPLCoreData)render();
const host=document.getElementById('kpi-grid');if(host)new MutationObserver(()=>{if(!rendering&&window.FPLCoreData)render();}).observe(host,{childList:true});
window.FPLPositionKpis={render,rows};
})();
