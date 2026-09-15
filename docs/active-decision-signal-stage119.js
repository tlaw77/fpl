(()=>{
const n=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
function fromSynthesis(syn={}){
 const a=syn.current_action||{},r=syn.robustness||{};
 const action=String(a.action||'HOLD').toUpperCase();
 const inferredMulti=action==='TRANSFER'&&!!r.multi_transfer_clears_gate&&!r.transfer_clears_gate;
 const type=r.active_route_type||(inferredMulti?'multi_transfer':action==='TRANSFER'?'single_transfer':'single_transfer_challenger');
 const multi=type==='multi_transfer';
 const route=r.active_route||(multi?r.multi_transfer_route:r.single_step_leader)||a.headline||'—';
 const edge=n(r.active_edge_over_hold_6gw,multi?n(r.multi_transfer_edge_over_roll):n(r.single_step_edge_over_hold_6gw));
 const required=n(r.active_required_edge,multi?n(r.multi_transfer_required_edge):n(r.required_edge));
 const edgeClear=required>0&&edge>=required;
 const validationKind=r.active_validation_kind||(multi?'adaptive_rival':'model_agreement');
 const validationLabel=r.active_validation_label||(multi?'Adaptive-rival test':'Model agreement');
 const support=n(r.measured_leader_support_models),supportNeed=Math.max(1,n(r.required_consensus_models,2));
 const validationClear=r.active_validation_clear!==undefined?!!r.active_validation_clear:(multi?!!r.multi_transfer_clears_gate:support>=supportNeed);
 const gateClear=r.active_transfer_gate_clear!==undefined?!!r.active_transfer_gate_clear:(action==='TRANSFER'&&(multi?!!r.multi_transfer_clears_gate:!!r.transfer_clears_gate));
 const validationValue=validationKind==='adaptive_rival'?(validationClear?'PASS':'FAIL'):`${support}/${supportNeed}`;
 const ratio=validationKind==='adaptive_rival'?(validationClear?1:0):Math.min(1,support/supportNeed);
 const score=gateClear?100:Math.min(99,Math.round((Math.min(1,edge/Math.max(1,required))*72+ratio*28)*10)/10);
 return{action,type,multi,route,edge,required,edgeClear,validationKind,validationLabel,validationValue,validationClear,gateClear,score,transferCount:n(a.transfer_count,multi?n(r.multi_transfer_count,2):action==='TRANSFER'?1:0)};
}
function fromSnapshot(x={}){
 const action=String(x.action||'HOLD').toUpperCase(),route=x.active_route||x.leader||x.single_step_leader||'—';
 const edge=n(x.active_edge_over_hold_6gw,x.edge_over_hold_6gw??x.single_step_edge_over_hold_6gw);
 const required=n(x.active_required_edge,x.required_edge);
 const gateClear=x.active_transfer_gate_clear!==undefined?!!x.active_transfer_gate_clear:!!x.transfer_clears_gate;
 return{...x,action,route,edge,required,gateClear,type:x.active_route_type||'legacy',validationLabel:x.active_validation_label||'Model agreement',validationClear:x.active_validation_clear!==undefined?!!x.active_validation_clear:gateClear};
}
function execution(d={},signal=fromSynthesis(d.decision_synthesis||{})){
 const hours=n(d.hours_to_deadline,d.deadline_context?.hours_to_deadline),phase=String(d.deadline_context?.phase||'normal').toLowerCase();
 if(signal.action!=='TRANSFER'||!signal.gateClear)return{state:'hold',label:'HOLD',title:'NO CALL TO ACTION YET',canExecute:false,copy:'Keep the transfer banked unless the full active-route gate clears.'};
 if(phase==='locked')return{state:'closed',label:'WINDOW CLOSED',title:'DECISION WINDOW CLOSED',canExecute:false,copy:'The deadline has passed; keep the route as review evidence only.'};
 if(hours>24)return{state:'plan',label:`PLAN ${signal.transferCount||1} TRANSFER${signal.transferCount===1?'':'S'}`,title:'PLAN READY · WAIT TO EXECUTE',canExecute:false,copy:'The route has cleared its decision gate, but wait for team news, workload and material price information before committing.'};
 if(hours>6)return{state:'check',label:'FINAL CHECKS',title:'FINAL CHECKS · THEN TRANSFER',canExecute:false,copy:'The route remains recommended. Confirm availability, price and deadline timing before executing.'};
 return{state:'execute',label:'TRANSFER AFTER CHECKS',title:'EXECUTION WINDOW',canExecute:true,copy:'The route is actionable if the final availability, price and deadline checks remain clear.'};
}
function sameRouteTail(rows=[]){if(!rows.length)return[];const normalized=rows.map(fromSnapshot),last=normalized[normalized.length-1],tail=[];for(let i=normalized.length-1;i>=0;i--){const x=normalized[i];if(x.route!==last.route||x.type!==last.type)break;tail.unshift(x)}return tail}
window.FPLActiveDecisionSignal={fromSynthesis,fromSnapshot,execution,sameRouteTail};
if(typeof module!=='undefined')module.exports=window.FPLActiveDecisionSignal;
document.documentElement.dataset.activeDecisionSignalBuild='stage119-20260915-1';
})();
