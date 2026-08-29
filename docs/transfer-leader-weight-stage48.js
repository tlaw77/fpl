(()=>{
const BUILD='transfer-leader-weight-20260829-1225';
function q(s,r=document){return r.querySelector(s)}
function qa(s,r=document){return [...r.querySelectorAll(s)]}
function text(el){return String(el?.textContent||'').trim()}
function pctFrom(card){const note=card&&q('[data-relative-strength]',card);const m=text(note).match(/(\d+)% of best/i);return m?Number(m[1]):null}
function metricCard(sec,re){return qa(':scope > div',sec).find(c=>re.test(text(c)))||null}
function apply(){
 const view=q('#view-transfer');if(!view)return;
 const hero=q('.transfer-hero',view),metrics=q('.transfer-metrics',view);if(!hero||!metrics)return;
 const modelCard=metricCard(metrics,/projected model gain|model score uplift|lower-variance uplift/i);
 const levCard=metricCard(metrics,/projected leverage gain|leverage uplift/i);
 const bankCard=metricCard(metrics,/bank after this transfer|bank now/i);
 const ownCard=metricCard(metrics,/incoming player rival ownership|nearest-rival ownership/i);
 const modelPct=pctFrom(modelCard),levPct=pctFrom(levCard);
 const ev=q('.transfer-evidence,[data-stage9-evidence]',hero);
 const evTitle=text(ev&&q('h3',ev));
 const evLevel=/strong/i.test(evTitle)?'Strong':/moderate/i.test(evTitle)?'Moderate':/cautious|limited/i.test(evTitle)?'Cautious':'Unrated';
 const modelStrong=modelPct!=null&&modelPct>=90,modelGood=modelPct!=null&&modelPct>=75;
 let label='MODEL LEADER',colour='#60a5fa',note='Top-ranked route, but the size of the model edge and external evidence should decide how strongly to act.';
 if(modelStrong&&evLevel==='Strong'){label='STRONG LEADING CASE';colour='#34d399';note='Large relative model edge with strong independent corroboration.'}
 else if(modelGood&&(evLevel==='Strong'||evLevel==='Moderate')){label='SUPPORTED LEADER';colour='#fbbf24';note='The model lead is meaningful and external evidence is supportive, but this is not a must-do move.'}
 else if(evLevel==='Cautious'||(modelPct!=null&&modelPct<75)){label='TENTATIVE LEADER';colour='#94a3b8';note='It ranks first, but either the model edge is modest or corroborating evidence is weak.'}
 const tag=q('.transfer-hero-tag',hero);if(tag){tag.textContent=label;tag.style.setProperty('color',colour,'important');tag.style.setProperty('border-color',`${colour}66`,'important')}
 let weight=q('[data-leader-weight]',hero);if(!weight){weight=document.createElement('div');weight.dataset.leaderWeight='1';weight.style.cssText='margin:12px 0 0;padding:10px 11px;border-radius:12px;background:#101a2d;border:1px solid #2b3d58';const evNode=q('.transfer-evidence,[data-stage9-evidence]',hero);if(evNode)evNode.insertAdjacentElement('beforebegin',weight);else hero.appendChild(weight)}
 const bits=[];if(modelPct!=null)bits.push(`Model uplift ${Math.round(modelPct)}% of best`);if(levPct!=null)bits.push(`Leverage ${Math.round(levPct)}% of best`);if(evLevel!=='Unrated')bits.push(`${evLevel.toLowerCase()} evidence`);
 const bank=text(bankCard).match(/£\s?[0-9.]+m/i)?.[0];if(bank)bits.push(`${bank.replace(/\s/g,'')} bank`);
 const own=text(ownCard).match(/[0-9.]+%/)?.[0];if(own)bits.push(`${own} rival own`);
 weight.innerHTML=`<div style="display:flex;justify-content:space-between;gap:8px;align-items:center"><strong style="font-size:10px;color:${colour}">WHY THIS ROUTE LEADS</strong><span style="font-size:9px;color:${colour};font-weight:850">${label}</span></div><div class="subtle" style="margin-top:5px;font-size:9px">${bits.join(' · ')}</div><div class="subtle" style="margin-top:4px;font-size:9px">${note}</div>`;
 if(!hero.contains(metrics)){
   metrics.classList.remove('dc-card');
   metrics.style.cssText='margin:12px 0 0;padding:10px 0 0;border:0;border-top:1px solid #285547;background:transparent;border-radius:0;box-shadow:none;display:grid;grid-template-columns:1fr 1fr;gap:8px';
   const eye=q('.eyebrow',metrics);if(eye)eye.textContent='LEADER IMPACT';
   const expl=q('[data-relative-explainer]',metrics);if(expl)expl.style.display='none';
   const ps=qa('p.subtle',metrics);ps.forEach(p=>{if(/green gain figures|projected improvements|ownership describes/i.test(text(p)))p.style.display='none'});
   const evNode=q('.transfer-evidence,[data-stage9-evidence]',hero);if(evNode)evNode.insertAdjacentElement('beforebegin',metrics);else hero.appendChild(metrics);
 }
 document.documentElement.dataset.transferLeaderWeightBuild=BUILD;
}
function run(){[350,900,1700,2600].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',run,{passive:true});window.addEventListener('fplCoreDataReady',run,{passive:true});window.addEventListener('fplSafePlanUpdated',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
