(()=>{
const BUILD='league-squad-profile-stage74-20260831-0034';
const SHAPES={'HIGH VARIANCE':'#fbbf24','BALANCED':'#60a5fa','TEMPLATE CORE':'#60a5fa','EXPOSED':'#fb7185','STRONG':'#34d399'};
let timer=null,observer=null;
function styleLabel(el,label,color){el.dataset.squadProfileLabel='1';el.style.fontSize='8px';el.style.fontWeight='900';el.style.letterSpacing='.08em';el.style.lineHeight='1';el.style.textTransform='uppercase';el.style.color=color;el.style.border=`1px solid ${color}66`;el.style.borderRadius='999px';el.style.padding='5px 8px';el.style.whiteSpace='nowrap';el.style.display='inline-flex';el.style.alignItems='center'}
function apply(){const host=document.getElementById('dc-intel-view');if(!host)return;
 host.querySelectorAll('span,strong,b').forEach(el=>{const txt=(el.textContent||'').trim().toUpperCase();if(SHAPES[txt])styleLabel(el,txt,SHAPES[txt])});
 host.querySelectorAll('h3,h2').forEach(h=>{if(h.dataset.squadProfileHeading)return;const raw=(h.textContent||'').trim();const upper=raw.toUpperCase();const shape=Object.keys(SHAPES).find(s=>upper===s||upper.startsWith(`${s} ·`)||upper.startsWith(`${s} -`));if(!shape)return;const rest=raw.slice(shape.length).replace(/^\s*[·-]\s*/,'').trim();if(!rest)return;h.dataset.squadProfileHeading='1';h.innerHTML=`<span data-squad-profile-label="1">${shape}</span><span style="font:inherit;color:inherit;margin-left:7px">${rest}</span>`;styleLabel(h.querySelector('[data-squad-profile-label]'),shape,SHAPES[shape])});
 document.documentElement.dataset.leagueSquadProfileBuild=BUILD}
function schedule(){clearTimeout(timer);timer=setTimeout(apply,80)}
function bind(){const host=document.getElementById('dc-intel-view');if(host){observer=new MutationObserver(schedule);observer.observe(host,{childList:true,subtree:true})}document.querySelector('#decision-nav button[data-view="intel"]')?.addEventListener('click',()=>setTimeout(apply,180),{passive:true});window.addEventListener('fplCoreDataReady',()=>setTimeout(apply,500),{passive:true});[220,700,1500].forEach(ms=>setTimeout(apply,ms))}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();