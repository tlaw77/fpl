(()=>{
const BUILD='transfer-impact-clarity-stage44-20260829-1158';
function q(s,r=document){return r.querySelector(s)}
function qa(s,r=document){return [...r.querySelectorAll(s)]}
function txt(el){return String(el?.textContent||'').trim()}
function addPlus(el){if(!el)return;const t=txt(el);if(/^\d+(?:\.\d+)?$/.test(t))el.textContent=`+${t}`}
function apply(){const view=q('#view-transfer');if(!view)return;const sec=qa('section',view).find(s=>/WHAT THE MODEL IMPROVES/i.test(txt(q('.eyebrow',s))));if(!sec)return;const eye=q('.eyebrow',sec);if(eye)eye.textContent='IMPACT OF CURRENT MODEL LEADER';const cards=qa(':scope > div > div, :scope > div[style*="grid"] > div',sec).filter(x=>x.querySelector('div')&&x.textContent.trim());let found=0;for(const c of cards){const kids=[...c.children];if(kids.length<2)continue;const label=kids[0],value=kids[1],l=txt(label).toLowerCase();if(l.includes('lower-variance uplift')){label.textContent='Projected model gain';addPlus(value);found++}else if(l.includes('leverage uplift')){label.textContent='Projected leverage gain';addPlus(value);found++}else if(l.includes('nearest-rival ownership')){label.textContent='Incoming player rival ownership';found++}else if(l.includes('bank now')){label.textContent='Bank after this transfer';found++}}
let note=q('[data-impact-explainer]',sec);if(!note){note=document.createElement('p');note.dataset.impactExplainer='1';note.className='subtle';note.style.cssText='margin:9px 0 0;font-size:9px;line-height:1.45';note.textContent='The green gain figures are projected improvements versus keeping the current squad. Ownership describes the incoming player; bank is the money left after the transfer.';sec.appendChild(note)}
document.documentElement.dataset.transferImpactClarityBuild=BUILD}
function run(){[100,350,900,1600].forEach(ms=>setTimeout(apply,ms))}
function bind(){run();q('#decision-nav button[data-view="transfer"]')?.addEventListener('click',run,{passive:true});window.addEventListener('fplSafePlanUpdated',run,{passive:true});window.addEventListener('fplCoreDataReady',run,{passive:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
