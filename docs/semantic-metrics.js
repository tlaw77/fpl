(()=>{
const BUILD='semantic-metrics-v1-20260826-1840';
const P={
  good:{accent:'#34d399',border:'rgba(52,211,153,.44)',bg:'rgba(16,185,129,.085)',label:'#a7f3d0'},
  warn:{accent:'#fbbf24',border:'rgba(251,191,36,.42)',bg:'rgba(245,158,11,.075)',label:'#fde68a'},
  bad:{accent:'#fb7185',border:'rgba(251,113,133,.42)',bg:'rgba(244,63,94,.07)',label:'#fecdd3'},
  neutral:{accent:'#94a3b8',border:'rgba(148,163,184,.20)',bg:'rgba(7,20,39,.30)',label:'#cbd5e1'}
};
function num(s){const m=String(s||'').replace(/,/g,'').match(/-?\d+(?:\.\d+)?/);return m?Number(m[0]):null}
function stateTile(tile,state,why=''){
  if(!tile||!P[state])return;
  const p=P[state];
  tile.dataset.semanticState=state;
  tile.style.border=`1px solid ${p.border}`;
  tile.style.borderLeft=`3px solid ${p.accent}`;
  tile.style.background=p.bg;
  tile.style.boxShadow=`inset 0 0 0 1px rgba(255,255,255,.015)`;
  tile.style.transition='border-color .18s ease,background .18s ease';
  if(why)tile.setAttribute('aria-label',`${tile.innerText.trim()}. ${why}`);
  const value=[...tile.querySelectorAll('strong')].at(-1);
  if(value)value.style.color=p.accent;
}
function upliftState(v){if(v==null)return'neutral';if(v>=25)return'good';if(v>=10)return'warn';return'bad'}
function bankState(v){if(v==null)return'neutral';if(v>=1)return'good';if(v>=.5)return'warn';return'bad'}
function ownershipState(v,lens){if(v==null)return'neutral';if(lens==='leverage')return v<=33?'good':v<=66?'warn':'bad';if(lens==='protect')return v>=67?'good':v>=34?'warn':'bad';return'neutral'}
function journal(){
  document.querySelectorAll('[data-journal-card],.history-decision').forEach(card=>{
    const tiles=[...card.querySelectorAll('[data-journal-metric],.history-metric')];
    if(!tiles.length)return;
    let low=null,lev=null;
    for(const t of tiles){const txt=t.innerText||'';if(/lower-variance uplift/i.test(txt))low=num(txt);if(/leverage uplift/i.test(txt))lev=num(txt)}
    const lens=lev!=null&&low!=null?(lev>=low?'leverage':'protect'):lev!=null?'leverage':low!=null?'protect':null;
    tiles.forEach(t=>{
      const txt=t.innerText||'',v=num(txt);
      if(/lower-variance uplift/i.test(txt))stateTile(t,upliftState(v),v>=25?'Strong historical lower-variance signal.':v>=10?'Moderate historical signal.':'Weak historical signal.');
      else if(/leverage uplift/i.test(txt))stateTile(t,upliftState(v),v>=25?'Strong historical leverage signal.':v>=10?'Moderate historical signal.':'Weak historical signal.');
      else if(/nearest-rival ownership/i.test(txt))stateTile(t,ownershipState(v,lens),lens==='leverage'?'Lower rival ownership is favourable for leverage.':'Higher rival ownership is favourable for protection.');
      else if(/bank then/i.test(txt))stateTile(t,bankState(v),v>=1?'Healthy flexibility retained.':v>=.5?'Some flexibility retained.':'Limited budget flexibility.');
    });
  });
}
function recommendationLens(){
  const route=document.querySelector('#dc-transfer-view .dc-recommendation h2')?.textContent?.replace(/^Make\s+/i,'').trim();
  if(!route)return null;
  const card=[...document.querySelectorAll('#dc-transfer-view .dc-rec-card')].find(x=>x.querySelector('h3')?.textContent?.trim()===route);
  if(card?.classList.contains('aggressive'))return'leverage';
  if(card?.classList.contains('safe'))return'protect';
  return null;
}
function evidence(){
  const lens=recommendationLens();
  document.querySelectorAll('[data-evidence-stack]').forEach(box=>{
    const confidence=[...box.querySelectorAll('.dc-confidence')].find(x=>/confidence/i.test(x.textContent||''));
    if(confidence){const t=(confidence.textContent||'').toLowerCase();const state=t.includes('strong')?'good':t.includes('moderate')?'warn':t.includes('cautious')?'bad':'neutral';const p=P[state];confidence.style.color=p.accent;confidence.style.borderColor=p.border;confidence.style.background=p.bg}
    [...box.querySelectorAll('div')].forEach(tile=>{
      const first=tile.firstElementChild;if(!first||first.tagName!=='SPAN')return;
      const label=(first.textContent||'').trim().toLowerCase();
      const text=(tile.textContent||'').toLowerCase();
      if(label==='scout consensus'){
        const sources=num(text);stateTile(tile,sources==null?'bad':sources>=2?'good':'warn',sources>=2?'Multiple independent sources corroborate the target.':sources===1?'Only one matched source.':'No matched external corroboration.');
      }else if(label==='rival context'){
        const own=num(text);stateTile(tile,ownershipState(own,lens),lens==='leverage'?'Low nearest-rival ownership supports leverage.':lens==='protect'?'High nearest-rival ownership supports protection.':'Ownership is contextual rather than universally good or bad.');
      }else if(label==='market'){
        const state=text.includes('wait for news')||text.includes('strong fall')?'bad':text.includes('strong rise')?'warn':text.includes('no relevant market alert')||text.includes('stable')?'good':'neutral';stateTile(tile,state,state==='warn'?'Price pressure adds urgency, not football quality.':state==='bad'?'Market/news signal argues for caution.':'No material market obstacle.');
      }else if(label==='minutes / news'){
        const state=text.includes('clear')||text.includes('no availability flag')?'good':text.includes('minor')?'warn':text.includes('concern')?'bad':'neutral';stateTile(tile,state,state==='good'?'Minutes/availability evidence is supportive.':state==='warn'?'Some uncertainty remains.':'Minutes/availability risk is material.');
      }
    });
  });
}
function run(){journal();evidence()}
function boot(){run();setTimeout(run,500);setTimeout(run,1400);setTimeout(run,3200);new MutationObserver(()=>requestAnimationFrame(run)).observe(document.body,{childList:true,subtree:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);else boot();
window.FPLSemanticMetrics={build:BUILD,run};
})();