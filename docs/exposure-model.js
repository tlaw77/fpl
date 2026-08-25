(()=>{
  const SHIELD_EO=75;
  const NEUTRAL_EO=40;
  const STYLE_WEIGHTS={leverageShare:.60,differentiation:.20,captainUniqueness:.10,shieldScarcity:.10};
  const num=(v,d=0)=>Number.isFinite(Number(v))?Number(v):d;
  const clamp=(v,a=0,b=100)=>Math.max(a,Math.min(b,v));

  function startingXI(picks){
    const rows=picks||[];
    const slotted=rows.filter(p=>num(p.slot,99)<=11);
    if(slotted.length===11)return slotted;
    return rows.filter(p=>num(p.multiplier,0)>0).slice(0,11);
  }

  function band(eo,{owned=false,active=false,captain=false,ownership=0}={}){
    eo=num(eo); ownership=num(ownership);
    if(owned){
      if(!active)return {key:'bench_differential',label:'Bench differential',family:'neutral'};
      if(eo>=SHIELD_EO)return {key:'shield',label:'Shield',family:'shield'};
      if(eo>=NEUTRAL_EO)return {key:'neutral',label:'Neutral',family:'neutral'};
      return {key:captain?'aggressive_leverage':'leverage',label:captain?'Captain leverage':'Leverage',family:'leverage'};
    }
    if(eo>=SHIELD_EO)return {key:'major_danger',label:'Major danger',family:'danger'};
    if(eo>=NEUTRAL_EO)return {key:'danger',label:'Danger',family:'danger'};
    if(ownership>=25)return {key:'risk',label:'Risk',family:'danger'};
    return {key:'differential_against',label:'Differential against',family:'neutral'};
  }

  function exposureMap(data){return new Map((data?.player_exposure||[]).map(x=>[x.player_id,x]));}

  function roleFor(player,expMap,activeOverride){
    const x=expMap?.get(player.player_id)||{};
    const eo=num(x.effective_ownership_pct,x.ownership_pct??player.effective_ownership_pct??player.ownership_pct??0);
    const ownership=num(x.ownership_pct,player.ownership_pct??0);
    const active=activeOverride!==undefined?!!activeOverride:(num(player.slot,99)<=11||num(player.multiplier,0)>0);
    const captain=!!player.captain||!!player.is_captain||num(player.multiplier,0)>1;
    return {...band(eo,{owned:true,active,captain,ownership}),eo,ownership,active,captain};
  }

  function ratingBand(score){
    if(score<=25)return'Protective';
    if(score<=45)return'Balanced';
    if(score<=65)return'Controlled leverage';
    if(score<=80)return'Aggressive';
    return'High variance';
  }

  function styleRating(picks,expMap){
    const xi=startingXI(picks);
    if(!xi.length)return{score:0,band:'—',leverage:0,neutral:0,shields:0,avgEo:0,captain:'—',captaincy:0,components:{}};
    const rows=xi.map(p=>{
      const x=expMap?.get(p.player_id)||{};
      const eo=num(x.effective_ownership_pct,x.ownership_pct??0);
      const capPct=num(x.captaincy_pct,0);
      const role=roleFor(p,expMap,true);
      return {...p,eo,capPct,role};
    });
    const avgEo=rows.reduce((s,x)=>s+clamp(x.eo),0)/rows.length;
    const differentiation=100-avgEo;
    const leverage=rows.filter(x=>x.role.family==='leverage').length;
    const shields=rows.filter(x=>x.role.family==='shield').length;
    const neutral=rows.length-leverage-shields;
    const leverageShare=100*leverage/rows.length;
    const cap=rows.find(x=>x.captain)||rows.find(x=>num(x.multiplier,0)>1);
    const captainUniqueness=100-clamp(cap?.capPct||0);
    const shieldScarcity=Math.max(0,100-Math.min(3,shields)/3*100);
    const components={leverageShare,differentiation,captainUniqueness,shieldScarcity};
    const score=Math.round(clamp(
      STYLE_WEIGHTS.leverageShare*leverageShare+
      STYLE_WEIGHTS.differentiation*differentiation+
      STYLE_WEIGHTS.captainUniqueness*captainUniqueness+
      STYLE_WEIGHTS.shieldScarcity*shieldScarcity
    ));
    return {score,band:ratingBand(score),leverage,neutral,shields,avgEo:Math.round(avgEo*10)/10,captain:cap?.player||'—',captaincy:cap?.capPct||0,components};
  }

  function normalizeExposure(data){
    const xiIds=new Set(startingXI(data?.squad||[]).map(p=>p.player_id));
    for(const x of data?.player_exposure||[]){
      if(x.in_my_team){
        const active=xiIds.has(x.player_id);
        const b=band(x.effective_ownership_pct,{owned:true,active,captain:num(x.my_multiplier,0)>1,ownership:x.ownership_pct});
        x.classification=b.key;
      }
    }
    return data;
  }

  window.FPLExposureModel={SHIELD_EO,NEUTRAL_EO,STYLE_WEIGHTS,startingXI,band,exposureMap,roleFor,ratingBand,styleRating,normalizeExposure};
})();
