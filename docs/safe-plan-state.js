(()=>{
const BUILD='safe-plan-state-v1-20260827-1515';
const KEY='fplWorkingPlanV2';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
let state={status:'not-read',plan:null,error:null};
function cleanPlayer(p){if(!p||typeof p!=='object')return null;return {player_id:Number(p.player_id)||null,player:String(p.player||p.name||''),club:String(p.club||''),position:String(p.position||''),price:Number.isFinite(Number(p.price))?Number(p.price):null};}
function sanitize(raw){if(!raw||typeof raw!=='object')return null;const moves=Array.isArray(raw.moves)?raw.moves.slice(0,8).map(m=>({out:cleanPlayer(m?.out),in:cleanPlayer(m?.in),status:String(m?.status||m?.state||'committed'),created_at:m?.created_at||m?.timestamp||null})).filter(m=>m.out||m.in):[];return {version:raw.version||null,moves,captain:cleanPlayer(raw.captain),vice_captain:cleanPlayer(raw.vice_captain),bank:Number.isFinite(Number(raw.bank))?Number(raw.bank):null};}
function readOnce(){try{const text=localStorage.getItem(KEY);if(!text){state={status:'empty',plan:null,error:null};return state}if(text.length>200000)throw new Error('Saved plan is unexpectedly large');const raw=JSON.parse(text);state={status:'ok',plan:sanitize(raw),error:null};return state}catch(e){state={status:'error',plan:null,error:e?.message||String(e)};return state}}
function moveText(m){const out=m.out?.player||'—',inn=m.in?.player||'—';return `${out} → ${inn}`}
function card(){const s=state;if(s.status==='ok'){
 const moves=s.plan?.moves||[];
 const rows=moves.length?moves.map(m=>`<div style="display:flex;justify-content:space-between;gap:10px;padding:9px 0;border-top:1px solid #243451"><strong>${esc(moveText(m))}</strong><span style="color:#9fb0c8;font-size:11px">${esc(m.status)}</span></div>`).join(''):'<p class="subtle">No committed moves in the saved plan.</p>';
 return `<section class="dc-card" id="safe-plan-state-card"><p class="eyebrow">STAGE 7 · SAVED PLAN (READ ONLY)</p><h3>${moves.length?`${moves.length} saved move${moves.length===1?'':'s'}`:'Saved plan available'}</h3>${rows}<p class="subtle" style="margin-top:10px">Read once from this device. No writes, no custom events, no observers, no automatic backfill.</p></section>`;
 }
 if(s.status==='empty')return `<section class="dc-card" id="safe-plan-state-card"><p class="eyebrow">STAGE 7 · SAVED PLAN</p><h3>No saved working plan on this device</h3><p class="subtle">The localStorage read completed safely.</p></section>`;
 return `<section class="dc-card" id="safe-plan-state-card"><p class="eyebrow">STAGE 7 · SAVED PLAN</p><h3>Saved plan could not be read</h3><p class="subtle">${esc(s.error||'Unknown read error')}</p></section>`;
}
function inject(attempt=0){const host=document.getElementById('dc-transfer-view');if(!host)return;if(document.getElementById('safe-plan-state-card'))return;if(!host.children.length&&attempt<12){setTimeout(()=>inject(attempt+1),250);return}host.insertAdjacentHTML('beforeend',card());}
function boot(){readOnce();inject();document.documentElement.dataset.safePlanBuild=BUILD;window.FPLSafePlan={build:BUILD,getState:()=>state};}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
})();