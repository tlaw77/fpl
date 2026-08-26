(()=>{
// Legacy loader retained only for compatibility. The Decision Journal is now
// owned by journal-standalone-v1.js. Do not render into #decision-history-panel
// from this bundle, otherwise the legacy renderer can overwrite the standalone
// mobile-safe markup after it has already been drawn.
function render(){
  if(window.FPLJournalStandalone?.render){
    return window.FPLJournalStandalone.render();
  }
}
window.FPLDecisionJournal={render,legacyDisabled:true};
})();