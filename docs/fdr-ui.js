(()=>{
  const cls=n=>`fdr-${Math.max(1,Math.min(5,Number(n)||3))}`;
  const badge=(n,compact=false)=>`<span class="fdr-decal ${cls(n)}${compact?' compact':''}" title="Fixture Difficulty Rating ${Number(n)||3}" aria-label="Fixture Difficulty Rating ${Number(n)||3}"></span>`;
  function decorate(root=document){
    const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode(node){
      if(!node.nodeValue||!/(?:FDR\s*[1-5]|\([1-5]\))/.test(node.nodeValue))return NodeFilter.FILTER_REJECT;
      const p=node.parentElement;if(!p||p.closest('.fdr-decal,script,style,textarea'))return NodeFilter.FILTER_REJECT;
      if(/\([1-5]\)/.test(node.nodeValue)&&!p.closest('.fixture-mini,.fixture-chip,.decision-row,.why-grid,.dc-player,.dc-rec-meta,.dc-rec-card,.eo-panel'))return NodeFilter.FILTER_REJECT;
      return NodeFilter.FILTER_ACCEPT;
    }});
    const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
    for(const node of nodes){
      const text=node.nodeValue;const frag=document.createDocumentFragment();let last=0;
      const re=/FDR\s*([1-5])|\(([1-5])\)/g;let m;
      while((m=re.exec(text))){
        if(m.index>last)frag.append(document.createTextNode(text.slice(last,m.index)));
        const n=Number(m[1]||m[2]);const span=document.createElement('span');span.className=`fdr-decal ${cls(n)}`;span.title=`Fixture Difficulty Rating ${n}`;span.setAttribute('aria-label',`Fixture Difficulty Rating ${n}`);frag.append(span);last=re.lastIndex;
      }
      if(last<text.length)frag.append(document.createTextNode(text.slice(last)));node.replaceWith(frag);
    }
  }
  let queued=false;const queue=()=>{if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;decorate(document.body)})};
  window.FDRUI={badge,decorate,queue};
  window.addEventListener('DOMContentLoaded',queue);
  window.addEventListener('fplPlanChanged',queue);
  window.addEventListener('effectiveSquadRendered',queue);
  const observer=new MutationObserver(queue);window.addEventListener('DOMContentLoaded',()=>observer.observe(document.body,{subtree:true,childList:true}));
})();