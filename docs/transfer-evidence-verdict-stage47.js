(()=>{
const BUILD='transfer-evidence-verdict-20260829-1216';
function q(s,r=document){return r.querySelector(s)}
function qa(s,r=document){return [...r.querySelectorAll(s)]}
function text(el){return String(el?.textContent||'').trim()}
function toneBox(label,body,colour){return `<div style="margin-top:10px;padding:9px 10px;border-radius:10px;border:1px solid ${colour}55;background:#101a2d"><strong style="color:${colour};font-size:10px">${label}</strong><div class="subtle" style="margin-top:4px;font-size:9px;line-height:1.45">${body}</div></div>`}
function apply(){
 const view=q('#view-transfer');if(!view)return;
 const hero=q('.transfer-hero',view),ev=hero&&q('.transfer-evidence,[data-stage9-evidence]',hero);if(!hero||!ev)return;
 const cards=qa('[style*="border-left"]',ev);
 const scout=cards.find(c=>/SCOUT CONSENSUS/i.test(text(c)));
 const market=cards.find(c=>/^MARKET/i.test(text(c)));
 const minutes=cards.find(c=>/MINUTES \/ NEWS/i.test(text(c)));
 const rival=cards.find(c=>/RIVAL CONTEXT/i.test(text(c)));
 if(!cards.length)return;
 const scoutText=text(scout),marketText=text(market),minutesText=text(minutes),rivalText=text(rival);
 const scoutMatched=!!scout&&!/No matched Scout consensus/i.test(scoutText);
 const marketPositive=/strong rise pressure|rise pressure/i.test(marketText)&&!/fall/i.test(marketText);
 const minutesClear=/Availability clear/i.test(minutesText);
 const marketNegative=/fall pressure|strong fall pressure/i.test(marketText);
 const minutesConcern=/concern|uncertainty/i.test(minutesText);
 const positives=[];const caveats=[];
 if(scoutMatched)positives.push('Scout coverage supports the incoming player');else caveats.push('no matched Scout consensus');
 if(marketPositive)positives.push('market movement is supportive');else if(marketNegative)caveats.push('market movement is negative');
 if(minutesClear)positives.push('minutes/availability look clear');else if(minutesConcern)caveats.push('minutes or availability are uncertain');
 if(/0%|1%|2%|3%|4%|5%/i.test(rivalText))positives.push('very low rival ownership offers leverage');
 let level='Cautious confidence',verdict='The model leads, but the external evidence is not yet strong enough to make this an obvious transfer.';
 if(positives.length>=3&&scoutMatched&&!marketNegative&&!minutesConcern){level='Strong confidence';verdict='The football case is reinforced by multiple independent signals. This is a well-supported transfer, although rolling can still be valid if the immediate model edge is small.'}
 else if(positives.length>=2&&!marketNegative&&!minutesConcern){level='Moderate confidence';verdict='The evidence leans in favour of the transfer, but it is supportive rather than decisive. The missing or neutral evidence should stop this being treated as a must-do move.'}
 const h=ev.querySelector('.panel-head h3')||ev.querySelector('h3');if(h)h.textContent=level;
 ev.querySelector('[data-evidence-verdict]')?.remove();
 const box=document.createElement('div');box.dataset.evidenceVerdict='1';
 const colour=level.startsWith('Strong')?'#34d399':level.startsWith('Moderate')?'#fbbf24':'#94a3b8';
 const detail=[positives.length?`Supports: ${positives.join(' · ')}.`:'',caveats.length?`Caveat${caveats.length>1?'s':''}: ${caveats.join(' · ')}.`:''].filter(Boolean).join(' ');
 box.innerHTML=toneBox('WHAT THE EVIDENCE MEANS',`${verdict}${detail?` ${detail}`:''}`,colour);
 const grid=cards[0]?.parentElement;if(grid)grid.insertAdjacentElement('afterend',box);else ev.appendChild(box);
 const old=[...ev.querySelectorAll('p.subtle')].find(p=>/Model, Scout, market and availability broadly reinforce|External evidence is corroboration/i.test(text(p)));if(old)old.style.display='none';
 document.documentElement.dataset.transferEvidenceVerdictBuild=BUILD;
}
function run(){[350,900,1600,2400].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',run,{passive:true});window.addEventListener('fplSafePlanUpdated',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
