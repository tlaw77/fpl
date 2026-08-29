(()=>{
const BUILD='section-consolidation-stage49-20260829-1236';
const q=(s,r=document)=>r.querySelector(s), qa=(s,r=document)=>[...r.querySelectorAll(s)];
const txt=e=>String(e?.textContent||'').trim();
function eyebrow(sec){return txt(q('.eyebrow',sec)).toUpperCase()}
function topSections(view){return qa(':scope > section',view).filter(s=>!s.dataset.consolidationGroup)}
function innerify(sec){sec.classList.remove('dc-card','dc-recommendation');sec.style.margin='0';sec.style.boxShadow='none';sec.style.border='0';sec.style.borderRadius='0';sec.style.background='transparent';sec.style.padding='0';return sec}
function group(view,key,title,subtitle,pred){
 if(!view||q(`[data-consolidation-group="${key}"]`,view))return;
 const matches=topSections(view).filter(pred);if(matches.length<2)return;
 const shell=document.createElement('section');shell.className='dc-card';shell.dataset.consolidationGroup=key;
 shell.style.cssText='padding:14px 14px 10px';
 shell.innerHTML=`<div style="margin-bottom:10px"><p class="eyebrow">${title}</p>${subtitle?`<p class="subtle" style="margin:3px 0 0;font-size:9px">${subtitle}</p>`:''}</div><div data-consolidation-body="1"></div>`;
 matches[0].insertAdjacentElement('beforebegin',shell);const body=q('[data-consolidation-body]',shell);
 matches.forEach((sec,i)=>{if(i){const d=document.createElement('div');d.style.cssText='height:1px;background:#243451;margin:12px 0';body.appendChild(d)}body.appendChild(innerify(sec))});
}
function team(){const v=q('#dc-team-view');if(!v)return;group(v,'gw-selection','GW SELECTION','XI, bench, captaincy and the reasons behind the close calls belong to one gameweek decision.',s=>{const e=eyebrow(s);return /RECOMMENDED XI|XI AFTER YOUR CHOICE|LEAGUE IMPACT|BENCH|SELECTION RATIONALE|CAPTAINCY RATIONALE/.test(e)||s.classList.contains('pitch-panel')||s.classList.contains('pitch-impact')||s.classList.contains('pitch-bench-panel')||s.classList.contains('selection-rationale')||s.classList.contains('captain-rationale')});}
function shape(){const v=q('#dc-shape-view');if(!v)return;
 group(v,'squad-health','SQUAD HEALTH','Structure, concentration, availability and immediate workload are one health check.',s=>{const e=eyebrow(s),t=txt(s).toUpperCase();return /POSITION SPEND|CLUB CONCENTRATION|AVAILABILITY|WORKLOAD|CONGESTION/.test(e)||/SHORT-TERM WORKLOAD|NEXT-GW WORKLOAD/.test(t)});
 group(v,'forward-plan','FORWARD PLAN','Fixture stress and league-pack positioning show where the squad may need intervention next.',s=>{const e=eyebrow(s),t=txt(s).toUpperCase();return /DECISION TIMELINE|LEAGUE PACK|SQUAD VS|PACK POSITION/.test(e)||/DECISION TIMELINE|SQUAD VS LEAGUE|LEAGUE PACK/.test(t)});
}
function intel(){const v=q('#dc-intel-view');if(!v)return;
 group(v,'league-squad-intel','LEAGUE SQUAD INTELLIGENCE','Rival strengths, weaknesses, recent direction and pack patterns are analysed together.',s=>{const e=eyebrow(s),t=txt(s).toUpperCase();return /RIVAL SQUAD|PACK PATTERN|LEAGUE POSITIONING|SQUAD ANALYSIS/.test(e)||/RIVAL SQUAD ANALYSIS|LEAGUE PACK PATTERN/.test(t)});
}
function pool(){const v=q('#dc-pool-view');if(!v)return;const timing=topSections(v).find(s=>/TIMING WATCH/.test(eyebrow(s)));if(!timing||q('[data-timing-details]',v))return;const d=document.createElement('details');d.dataset.timingDetails='1';d.style.cssText='margin:10px 0;border:1px solid #243451;border-radius:12px;background:#101a2d;padding:10px 12px';const sum=document.createElement('summary');sum.style.cssText='cursor:pointer;font-weight:850;color:#cbd5e1;font-size:10px;letter-spacing:.04em';sum.textContent='Timing Watch · market movement';timing.insertAdjacentElement('beforebegin',d);d.appendChild(sum);d.appendChild(innerify(timing));timing.style.marginTop='10px';}
function transfer(){const v=q('#dc-transfer-view');if(!v)return;const routes=q('[data-safe-routes]',v);if(routes){const eye=q('.eyebrow',routes);if(eye)eye.textContent='DECISION OPTIONS';const h=q('h3',routes);if(h)h.textContent='Transfer now or bank the move';}}
function apply(){transfer();team();shape();pool();intel();document.documentElement.dataset.sectionConsolidationBuild=BUILD}
function run(){[250,750,1450,2400].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();qa('#decision-nav button').forEach(b=>b.addEventListener('click',run,{passive:true}));window.addEventListener('fplCoreDataReady',run,{passive:true});window.addEventListener('fplSafePlanUpdated',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
