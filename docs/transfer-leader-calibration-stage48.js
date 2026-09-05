(()=>{
const BUILD='transfer-leader-calibration-20260905-2052';
function q(s,r=document){return r.querySelector(s)}
function qa(s,r=document){return [...r.querySelectorAll(s)]}
function txt(el){return String(el?.textContent||'').trim()}
function pctFrom(card){const note=card&&q('[data-relative-strength]',card);const m=txt(note).match(/(\d+)% of best/i);return m?Number(m[1]):null}
function metricCard(sec,re){return qa(':scope > div',sec).find(c=>re.test(txt(c)))||null}
function isHold(){return String(window.FPLCoreData?.decision_synthesis?.current_action?.action||'').toUpperCase()==='HOLD'}
function compactMetrics(metrics){
 metrics.classList.remove('dc-card');
 metrics.style.cssText='margin:8px 0 0;padding:8px 0 0;border:0;border-top:1px solid rgba(255,255,255,.07);background:transparent;border-radius:0;box-shadow:none;display:grid;grid-template-columns:1fr 1fr;gap:7px';
 const eye=q('.eyebrow',metrics);if(eye)eye.style.display='none';
 const expl=q('[data-relative-explainer]',metrics);if(expl)expl.style.display='none';
 qa('p.subtle',metrics).forEach(p=>{if(/green gain figures|projected improvements|ownership describes/i.test(txt(p)))p.style.display='none'});
 qa(':scope > div',metrics).forEach(c=>{c.style.setProperty('padding','8px','important');c.style.setProperty('border-radius','10px','important')});
}
function apply(){
 const view=q('#view-transfer');if(!view)return;
 const hero=q('.transfer-hero',view),metrics=q('.transfer-metrics',view);if(!hero||!metrics)return;
 const evidence=q('.transfer-evidence,[data-stage9-evidence]',hero)||q('.transfer-evidence,[data-stage9-evidence]',view);
 const ev=txt(evidence&&q('h3',evidence)).toLowerCase();
 const evLevel=ev.includes('strong')?'Strong':ev.includes('moderate')?'Moderate':ev.includes('cautious')||ev.includes('limited')?'Cautious':'Unrated';
 const modelCard=metricCard(metrics,/projected model gain|model score uplift|lower-variance uplift/i);
 const levCard=metricCard(metrics,/projected leverage gain|leverage uplift/i);
 const bankCard=metricCard(metrics,/bank after this transfer|bank now/i);
 const ownCard=metricCard(metrics,/incoming player rival ownership|nearest-rival ownership/i);
 const modelPct=pctFrom(modelCard),levPct=pctFrom(levCard);
 const modelStrong=modelPct!=null&&modelPct>=90,modelGood=modelPct!=null&&modelPct>=75;
 let label='MODEL LEADER',colour='#60a5fa',note='Top-ranked route, but the size of the model edge and external evidence should determine how strongly to act.';
 if(modelStrong&&evLevel==='Strong'){label='STRONG LEADING CASE';colour='#34d399';note='Large relative model edge with strong independent corroboration.'}
 else if(modelGood&&(evLevel==='Strong'||evLevel==='Moderate')){label='SUPPORTED LEADER';colour='#fbbf24';note='The model lead is meaningful and external evidence is supportive, but this is not a must-do move.'}
 else if(evLevel==='Cautious'||(modelPct!=null&&modelPct<75)){label='TENTATIVE LEADER';colour='#94a3b8';note='It ranks first, but either the model edge is modest or corroborating evidence is weak.'}
 const holding=isHold();
 const tag=q('.transfer-hero-tag',hero);if(tag){tag.textContent=holding?'MODEL ALTERNATIVE':label;const tc=holding?'#94a3b8':colour;tag.style.setProperty('color',tc,'important');tag.style.setProperty('border-color',tc+'66','important');tag.style.setProperty('background',tc+'12','important')}
 let box=q('[data-leader-calibration]',hero)||q('[data-leader-calibration]',view);
 if(!box){box=document.createElement('div');box.dataset.leaderCalibration='1';box.style.cssText='margin-top:10px;padding:10px 11px;border-radius:12px;background:#101a2d;border:1px solid #2b3d58';hero.appendChild(box)}
 const bits=[];if(modelPct!=null)bits.push(`Model uplift ${Math.round(modelPct)}% of best`);if(levPct!=null)bits.push(`Leverage ${Math.round(levPct)}% of best`);if(evLevel!=='Unrated')bits.push(`${evLevel.toLowerCase()} evidence`);const bank=txt(bankCard).match(/£\s?[0-9.]+m/i)?.[0];if(bank)bits.push(`${bank.replace(/\s/g,'')} bank`);const own=txt(ownCard).match(/[0-9.]+%/)?.[0];if(own)bits.push(`${own} rival own`);
 box.innerHTML=`<div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><strong style="font-size:10px;color:${holding?'#94a3b8':colour}">${holding?'WHY A MODEL ROUTE STILL LEADS':'WHY THIS ROUTE LEADS'}</strong><span style="font-size:9px;color:${holding?'#94a3b8':colour};font-weight:850">${holding?'NOT ACTIVE ACTION':label}</span></div><div class="subtle" style="margin-top:5px;font-size:9px">${bits.join(' · ')}</div><div class="subtle" style="margin-top:4px;font-size:9px">${holding?'HOLD is authoritative. This only explains the highest-ranked alternative if the decision gate changes.':note}</div>`;
 if(holding){
   const signal=q('[data-decision-signal]',view);if(!signal)return;
   let discussion=q('[data-model-leader-discussion]',signal);
   if(!discussion){discussion=document.createElement('details');discussion.dataset.modelLeaderDiscussion='1';discussion.className='txs-details model-leader-discussion';discussion.innerHTML='<summary><span>Current model leader · discussion</span><small>Why a route can lead while HOLD remains preferred</small></summary><div data-model-leader-body></div>';signal.appendChild(discussion)}
   const body=q('[data-model-leader-body]',discussion);compactMetrics(metrics);if(body){if(box.parentElement!==body)body.appendChild(box);if(metrics.parentElement!==body)body.appendChild(metrics)}discussion.open=false;
 }else{
   const discussion=q('[data-model-leader-discussion]',view);if(discussion)discussion.remove();
   if(!hero.contains(box))hero.appendChild(box);
   if(!hero.contains(metrics)){metrics.classList.remove('dc-card');metrics.style.cssText='margin:12px 0 0;padding:10px 0 0;border:0;border-top:1px solid #285547;background:transparent;border-radius:0;box-shadow:none;display:grid;grid-template-columns:1fr 1fr;gap:8px';const eye=q('.eyebrow',metrics);if(eye){eye.style.display='';eye.textContent='LEADER IMPACT'}const expl=q('[data-relative-explainer]',metrics);if(expl)expl.style.display='none';qa('p.subtle',metrics).forEach(p=>{if(/green gain figures|projected improvements|ownership describes/i.test(txt(p)))p.style.display='none'});hero.appendChild(metrics)}
 }
 document.documentElement.dataset.transferLeaderCalibrationBuild=BUILD;
}
function run(){[250,650,1200,2200,3400].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',run,{passive:true});window.addEventListener('fplCoreDataReady',run,{passive:true});window.addEventListener('fplSafePlanUpdated',run,{passive:true});window.addEventListener('fplViewSettled',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
