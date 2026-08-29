(()=>{
const BUILD='transfer-leader-calibration-20260829-1222';
function q(s,r=document){return r.querySelector(s)}
function txt(el){return String(el?.textContent||'').trim()}
function apply(){
 const view=q('#view-transfer');if(!view)return;
 const hero=q('.transfer-hero',view);if(!hero)return;
 const evidence=q('.transfer-evidence,[data-stage9-evidence]',hero)||q('.transfer-evidence,[data-stage9-evidence]',view);
 const heading=evidence?.querySelector('h3');
 const ev=txt(heading).toLowerCase();
 const level=ev.includes('strong')?'strong':ev.includes('moderate')?'moderate':ev.includes('cautious')?'cautious':ev.includes('limited')?'limited':'unknown';
 const tag=q('.transfer-hero-tag',hero);
 const tone=level==='strong'?'#34d399':level==='moderate'?'#60a5fa':level==='cautious'||level==='limited'?'#fbbf24':'#94a3b8';
 if(tag){
   tag.textContent=level==='unknown'?'MODEL LEADER':`MODEL LEADER · ${level.toUpperCase()} EVIDENCE`;
   tag.style.setProperty('color',tone,'important');
   tag.style.setProperty('border-color',tone+'66','important');
   tag.style.setProperty('background',tone+'12','important');
 }
 let note=q('[data-leader-calibration]',hero);
 if(!note){note=document.createElement('div');note.dataset.leaderCalibration='1';note.className='subtle';note.style.cssText='margin-top:8px;font-size:9px;line-height:1.4';hero.appendChild(note)}
 if(level==='strong')note.innerHTML='<b style="color:#34d399">Model + evidence align:</b> this is the strongest current case, though the shortlist and roll option remain valid comparisons.';
 else if(level==='moderate')note.innerHTML='<b style="color:#60a5fa">Top-ranked by the model, not a strong recommendation:</b> evidence is only moderate, so compare the shortlist and the value of rolling before acting.';
 else if(level==='cautious'||level==='limited')note.innerHTML='<b style="color:#fbbf24">Model leader with weak corroboration:</b> treat this as a candidate, not a transfer signal. Rolling or another route may be preferable.';
 else note.textContent='This is the top-ranked model route. Evidence strength is shown separately and should determine how strongly you act on it.';
 document.documentElement.dataset.transferLeaderCalibrationBuild=BUILD;
}
function run(){[250,800,1500,2400].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',run,{passive:true});window.addEventListener('fplCoreDataReady',run,{passive:true});window.addEventListener('fplSafePlanUpdated',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
