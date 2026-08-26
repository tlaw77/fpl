(()=>{
  const BUILD='transfer-uplift-disabled-20260826-2145';
  // Emergency safety stub. The previous uplift module could repeatedly write
  // localStorage and dispatch fplPlanChanged when persistence failed, which
  // could lock Safari's main thread before the dashboard finished rendering.
  // Keep this file harmless so even a stale cached loader cannot reintroduce
  // the freeze. The uplift feature will be rebuilt without event recursion.
  window.FPLTransferUplift={build:BUILD,disabled:true};
})();
