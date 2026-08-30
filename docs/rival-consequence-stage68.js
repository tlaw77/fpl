(()=>{
const BUILD='rival-consequence-stage68-20260830-1025';
const RAW='https://raw.githubusercontent.com/tlaw77/fpl/main/data/';
const ADAPT=RAW+'adaptive_rival_simulation.json', SYN=RAW+'decision_synthesis.json';
const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
let adaptive=null,synth=null,timer=null,observer=null;
async function get(url){const r=await fetch(`${url}?r68=${Date.now()}`,{cache:'no-store'});if(!r.ok)throw new Error(String(r.status));return r.json()}
function rivalRows(){const rows=window.FPLCoreData?.rivals||[];return rows.slice().sort((a,b)=>n(a.rank,999)-n(b.rank,999))}
function build(){
 const rec=adaptive?.recommendation||{};
 const probs=rec.prob_finish_ahead_each_rival||[];
 const meta=adaptive?.rival_behaviour||[];
 const rivals=rivalRows();
 if(!adaptive||adaptive.status!=='SUCCESS'||!probs.length)return '';
 const paired=probs.map((p,i)=>({prob:n(p),rival:rivals[i]||{},behaviour:meta[i]||{}}));
 const catchable=paired.slice().sort((a,b)=>b.prob-a.prob)[0]||{};
 const target=catchable.rival||{};
 const expectedRank=n(rec.expected_rank_after_path,window.FPLCoreData?.me?.rank||0);
 const gainPct=Math.round(n(rec.prob_gain_league_place)*100);
 const catchPct=Math.round(n(catchable.prob)*100);
 const currentRank=n(window.FPLCoreData?.me?.rank,0);
 const gap=n(target.gap_to_me,0);
 const penalty=n(rec.probabilistic_rival_rank_penalty,0);
 const action=synth?.current_action?.headline||synth?.current_action?.action||'Current Decision';
 const targetLabel=target.team_name||catchable.behaviour?.team_name||'nearest rival';
 return `<section class="outlook-card rival-consequence-card" data-rival-consequence-stage="68"><div class="outlook-refresh"><div><p class="eyebrow">MINI-LEAGUE CONSEQUENCE · 4GW ADAPTIVE SCENARIO</p><h3>${currentRank?`From #${currentRank} toward #${expectedRank.toFixed(1)}`:`Expected rank ${expectedRank.toFixed(1)}`}</h3></div><span class="outlook-chip ${gainPct>=60?'good':'warn'}">${gainPct}% gain-place chance</span></div><div class="rival-consequence-grid"><div class="rival-consequence-metric"><b>#${expectedRank.toFixed(1)}</b><span>expected league position</span></div><div class="rival-consequence-metric"><b>${gainPct}%</b><span>chance to gain ≥1 place</span></div><div class="rival-consequence-metric"><b>${penalty>=0?'+':''}${penalty.toFixed(2)}</b><span>rank drag from rival reactions</span></div></div><div class="rival-consequence-target"><div><strong>Most catchable · ${esc(targetLabel)}</strong><small>${gap>0?`${gap.toFixed(0)} pts ahead now · `:''}adaptive model includes plausible rival transfers rather than assuming they stand still.</small></div><div class="rival-consequence-prob">${catchPct}%</div></div><p class="rival-consequence-note">Context only: this does not override <b>${esc(action)}</b>. League leverage can strengthen or weaken a sound FPL decision, but it is not allowed to manufacture a bad transfer.</p></section>`;
}
function attach(){
 const out=document.querySelector('#dc-team-view .team-outlook');
 if(!out||!adaptive||out.querySelector('[data-rival-consequence-stage="68"]'))return;
 const html=build();if(!html)return;
 const stability=[...out.querySelectorAll('.outlook-card')].find(x=>/PLAN STABILITY/i.test(x.textContent||''));
 const anchor=stability||out.querySelector('.outlook-grid');
 if(anchor)anchor.insertAdjacentHTML('afterend',html);else out.insertAdjacentHTML('beforeend',html);
 document.documentElement.dataset.rivalConsequenceBuild=BUILD;
}
function watch(){
 const host=document.getElementById('dc-team-view');if(!host||observer)return;
 observer=new MutationObserver(()=>{clearTimeout(timer);timer=setTimeout(attach,100)});observer.observe(host,{childList:true,subtree:true});
}
async function load(){try{[adaptive,synth]=await Promise.all([get(ADAPT),get(SYN).catch(()=>null)]);watch();setTimeout(attach,260)}catch(e){console.warn(BUILD,e)}}
window.addEventListener('fplCoreDataReady',load,{passive:true});
document.querySelector('#decision-nav button[data-view="team"]')?.addEventListener('click',()=>setTimeout(()=>{watch();attach()},220),{passive:true});
if(window.FPLCoreData)load();
})();
