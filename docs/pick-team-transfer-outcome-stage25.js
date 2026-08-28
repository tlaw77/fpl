(()=>{
const BUILD='pick-team-transfer-outcome-stage25-20260828-0915';
const KEY='fplWorkingPlanV2';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
function plan(){try{return JSON.parse(localStorage.getItem(KEY)||'null')}catch{return null}}
function norm(s){return String(s||'').trim().toLowerCase()}
function cardName(card){return norm(card?.querySelector('.pitch-name')?.childNodes?.length?[...card.querySelector('.pitch-name').childNodes].filter(n=>n.nodeType===3).map(n=>n.textContent).join(' '):card?.querySelector('.pitch-name')?.textContent).replace(/your in/gi,'').trim()}
function render(){
  const host=document.getElementById('dc-team-view'); if(!host)return;
  host.querySelector('#selected-transfer-outcome')?.remove();
  const m=plan()?.moves?.[0]; if(!m?.in?.player||!m?.out?.player)return;
  const target=norm(m.in.player);
  const pitchCards=[...host.querySelectorAll('.fpl-pitch .pitch-player-card')];
  const benchCards=[...host.querySelectorAll('.pitch-bench .pitch-player-card')];
  const starts=pitchCards.some(c=>cardName(c)===target||norm(c.textContent).includes(target));
  const benched=benchCards.some(c=>cardName(c)===target||norm(c.textContent).includes(target));
  if(!starts&&!benched)return;
  let reason='';
  if(benched){
    const row=[...host.querySelectorAll('.selection-rationale-row')].find(r=>norm(r.querySelector('strong')?.textContent)===target);
    const lines=row?[...row.querySelectorAll('.selection-rationale-copy p')].map(p=>p.textContent.trim()).filter(Boolean):[];
    reason=lines.slice(0,2).join(' ');
  }
  const status=starts?'STARTS':'BENCHED';
  const tone=starts?'#34d399':'#fbbf24';
  const title=starts?`${m.in.player} starts after your transfer`:`${m.in.player} is currently benched after your transfer`;
  const copy=starts
    ?`Your selected move ${m.out.player} → ${m.in.player} is applied to the effective squad and the model puts the incoming player in the XI.`
    :`The transfer is applied, but the XI model prefers another starter for this gameweek. ${reason||'The bench decision follows the same model, fixture, availability, form and formation rules used for the rest of the XI.'}`;
  const el=document.createElement('section');
  el.id='selected-transfer-outcome'; el.className='dc-card';
  el.style.cssText=`border:1px solid ${tone}66;border-left:5px solid ${tone};background:${starts?'#102a22':'#2a2210'};margin:0 0 12px`;
  el.innerHTML=`<div style="display:flex;justify-content:space-between;gap:10px;align-items:flex-start"><div><p class="eyebrow" style="color:${tone};margin-bottom:4px">SELECTED TRANSFER · THIS GW</p><h3 style="margin:0 0 6px">${esc(title)}</h3></div><span style="flex:0 0 auto;padding:5px 8px;border-radius:999px;background:${tone}18;color:${tone};font-size:9px;font-weight:900">${status}</span></div><p class="subtle" style="margin:0">${esc(copy)}</p>`;
  const pitch=host.querySelector('.pitch-panel');
  if(pitch)pitch.before(el); else host.prepend(el);
  document.documentElement.dataset.transferOutcomeBuild=BUILD;
}
function schedule(){[120,450,1000,1800].forEach(ms=>setTimeout(render,ms))}
function bind(){document.querySelector('#decision-nav button[data-view="team"]')?.addEventListener('click',schedule,{passive:true});window.addEventListener('fplSafePlanUpdated',schedule);if(document.querySelector('#view-team.active'))schedule()}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();