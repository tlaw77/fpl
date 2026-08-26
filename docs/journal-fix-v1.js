(()=>{
const BUILD='journal-fix-v1-20260826-1842';
function css(el,styles){if(!el)return;Object.assign(el.style,styles)}
function patch(){
  const panel=document.querySelector('#decision-history-panel');
  if(!panel)return;
  panel.dataset.journalFixBuild=BUILD;
  panel.querySelectorAll('.history-decision').forEach(card=>css(card,{position:'relative',background:'linear-gradient(180deg,rgba(24,43,72,.96),rgba(20,36,61,.96))',borderRadius:'16px',padding:'14px',margin:'8px 0 10px',overflow:'hidden'}));
  panel.querySelectorAll('.history-decision.pending').forEach(card=>css(card,{border:'1px dashed rgba(250,204,21,.46)'}));
  panel.querySelectorAll('.history-rec-head').forEach(el=>css(el,{display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:'10px'}));
  panel.querySelectorAll('.history-rec-head>div').forEach(el=>css(el,{minWidth:'0'}));
  panel.querySelectorAll('.history-rec-head>div>strong').forEach(el=>css(el,{display:'block',fontSize:'13px',lineHeight:'1.25',fontWeight:'850',color:'#f8fafc'}));
  panel.querySelectorAll('.history-rec-meta').forEach(el=>css(el,{marginTop:'5px',fontSize:'9px',color:'#9fb0c8'}));
  panel.querySelectorAll('.history-rec-head>span').forEach(el=>css(el,{display:'inline-flex',alignItems:'center',padding:'6px 9px',borderRadius:'999px',background:'rgba(250,204,21,.12)',border:'1px solid rgba(250,204,21,.18)',color:'#fde68a',fontSize:'8px',lineHeight:'1',fontWeight:'850',whiteSpace:'nowrap'}));
  panel.querySelectorAll('.history-evidence').forEach(el=>css(el,{marginTop:'11px',paddingTop:'11px',borderTop:'1px solid rgba(255,255,255,.08)'}));
  panel.querySelectorAll('.history-evidence-head').forEach(el=>css(el,{display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:'10px',marginBottom:'8px'}));
  panel.querySelectorAll('.history-evidence-head strong').forEach(el=>css(el,{fontSize:'9px',fontWeight:'850',color:'#e2e8f0'}));
  panel.querySelectorAll('.history-evidence-head span').forEach(el=>css(el,{fontSize:'8px',lineHeight:'1.3',color:'#9fb0c8',textAlign:'right'}));
  panel.querySelectorAll('.history-metrics').forEach(el=>css(el,{display:'grid',gridTemplateColumns:'repeat(2,minmax(0,1fr))',gap:'7px',marginTop:'0'}));
  panel.querySelectorAll('.history-metric').forEach(el=>css(el,{display:'block',minWidth:'0',padding:'9px 10px',border:'1px solid rgba(148,163,184,.18)',borderRadius:'11px',background:'rgba(7,20,39,.30)'}));
  panel.querySelectorAll('.history-metric-icon').forEach(el=>css(el,{display:'none'}));
  panel.querySelectorAll('.history-metric-copy').forEach(el=>css(el,{display:'block',minWidth:'0'}));
  panel.querySelectorAll('.history-metric b').forEach(el=>css(el,{display:'block',fontSize:'7px',lineHeight:'1.2',color:'#aebbd0',fontWeight:'750',marginBottom:'4px',whiteSpace:'normal'}));
  panel.querySelectorAll('.history-metric strong').forEach(el=>css(el,{display:'block',fontSize:'14px',lineHeight:'1',color:'#f8fafc',fontWeight:'900',letterSpacing:'-.02em'}));
  panel.querySelectorAll('.history-fixture-case').forEach(el=>css(el,{display:'block',marginTop:'9px',paddingTop:'9px',borderTop:'1px solid rgba(255,255,255,.07)'}));
  panel.querySelectorAll('.history-fixture-case>b').forEach(el=>css(el,{display:'block',fontSize:'8px',color:'#dce9fb',fontWeight:'850',marginBottom:'7px'}));
  panel.querySelectorAll('.history-fixtures').forEach(el=>css(el,{display:'grid',gridTemplateColumns:'repeat(3,minmax(0,1fr))',gap:'6px',alignItems:'stretch'}));
  panel.querySelectorAll('.history-fixture').forEach(el=>css(el,{display:'flex',alignItems:'center',gap:'5px',minWidth:'0',padding:'6px 7px',border:'0',borderRadius:'9px',background:'rgba(255,255,255,.035)',fontSize:'8px',lineHeight:'1.2',color:'#e5edf8',whiteSpace:'normal'}));
  panel.querySelectorAll('.history-fixture span').forEach(el=>css(el,{minWidth:'0',overflowWrap:'anywhere'}));
  panel.querySelectorAll('.history-fdr').forEach(el=>css(el,{display:'inline-block',flex:'0 0 8px',width:'8px',height:'8px',borderRadius:'999px'}));
  panel.querySelectorAll('.history-reasoning').forEach(el=>css(el,{marginTop:'9px',paddingTop:'8px',borderTop:'1px solid rgba(255,255,255,.07)'}));
  panel.querySelectorAll('.history-reasoning summary').forEach(el=>css(el,{display:'block',fontSize:'8px',color:'#dce9fb',fontWeight:'850'}));
  panel.querySelectorAll('.history-model-note').forEach(el=>css(el,{fontSize:'7px',color:'#9fb0c8',marginTop:'6px'}));
}
function loadSemantic(){if(window.FPLSemanticMetrics||document.querySelector('script[data-semantic-metrics]'))return;const s=document.createElement('script');s.src='semantic-metrics.js?v=20260826-1840';s.dataset.semanticMetrics='1';document.body.appendChild(s)}
function start(){patch();loadSemantic();setTimeout(patch,300);setTimeout(patch,900);const root=document.querySelector('#decision-history-panel');if(root)new MutationObserver(()=>patch()).observe(root,{childList:true,subtree:true});window.addEventListener('fplPlanChanged',()=>setTimeout(patch,80));}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start);else start();
window.FPLJournalFix={build:BUILD,patch};
})();