const DATA_URL = 'https://raw.githubusercontent.com/tlaw77/fpl/main/data/latest.json';

const fmt = (v, fallback='—') => (v === null || v === undefined ? fallback : v);
const pct = v => `${Number(v || 0).toFixed(1)}%`;
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));

function intensity(v){ const n=Number(v||0); return n>=80?5:n>=60?4:n>=40?3:n>=20?2:n>0?1:0; }
function badgeClass(label=''){ const x=label.toLowerCase(); if(x.includes('shield'))return 'shield'; if(x.includes('leverage'))return 'leverage'; if(x.includes('danger')||x.includes('risk')||x.includes('against'))return 'danger'; return 'neutral'; }
function labelText(label='neutral'){ return String(label).replaceAll('_',' '); }

function kpi(label,value,note=''){
  return `<div class="kpi"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(value)}</div><div class="kpi-note">${esc(note)}</div></div>`;
}

function renderKpis(d){
  const me=d.me||{}; const rivals=d.rivals||[];
  const leader=Math.max(...[me.total_points||0,...rivals.map(r=>r.total_points||0)]);
  const above=rivals.filter(r=>(r.total_points||0)>(me.total_points||0)).sort((a,b)=>(a.total_points||0)-(b.total_points||0))[0];
  const avgLive=d.live_summary?.league_average_live ?? d.live_summary?.league_average ?? null;
  const live=me.live_points ?? d.live_summary?.my_live_points ?? me.gw_points;
  const gapNext=above ? (above.total_points||0)-(me.total_points||0) : 0;
  document.querySelector('#kpi-grid').innerHTML=[
    kpi('Rank',`#${fmt(me.rank)}`,`${d.league?.manager_count||0} managers`),
    kpi('GW / Live',fmt(live),`Official GW: ${fmt(me.gw_points)}`),
    kpi('Gap to leader',leader-(me.total_points||0),leader===me.total_points?'You lead':'points'),
    kpi('Gap to next place',gapNext,above?above.team_name:'No one above'),
    kpi('Captain',fmt(me.captain),avgLive!==null?`League avg ${Number(avgLive).toFixed(1)}`:`VC ${fmt(me.vice_captain)}`)
  ].join('');
}

function renderStandings(d){
  const me={...(d.me||{}),overlap_pct:100,captain:d.me?.captain,active_chip:d.me?.active_chip};
  const rows=[me,...(d.rivals||[])].sort((a,b)=>(a.rank||999)-(b.rank||999));
  const myTotal=d.me?.total_points||0;
  document.querySelector('#rivals-table tbody').innerHTML=rows.map(r=>{
    const mine=r.entry_id===d.me?.entry_id;
    const gap=(r.total_points||0)-myTotal;
    return `<tr class="${mine?'you-row':''}"><td><span class="rank-chip">${fmt(r.rank)}</span></td><td><strong>${esc(r.team_name)}</strong><br><span class="subtle">${esc(r.manager||'')}</span></td><td>${fmt(r.live_points ?? r.gw_points)}</td><td>${fmt(r.total_points)}</td><td>${mine?'—':gap>0?`+${gap}`:gap}</td><td>${esc(r.captain||'—')}</td><td>${esc(r.active_chip||'—')}</td><td>${mine?'100%':pct(r.overlap_pct)}</td></tr>`;
  }).join('');
}

function topExposure(d, predicate, max=5){ return (d.player_exposure||[]).filter(predicate).slice(0,max); }
function signalCard(title,items,metric){
  return `<div class="signal-card"><h3>${esc(title)}</h3>${items.length?items.map(p=>`<div class="signal-item"><span>${esc(p.player)}</span><strong>${esc(metric(p))}</strong></div>`).join(''):'<div class="subtle">None currently</div>'}</div>`;
}

function renderSignals(d){
  const ex=[...(d.player_exposure||[])];
  const threats=ex.filter(p=>!p.in_my_team && (p.classification||'').match(/danger|risk|against/)).sort((a,b)=>(b.effective_ownership_pct??b.ownership_pct)-(a.effective_ownership_pct??a.ownership_pct));
  const leverage=ex.filter(p=>p.in_my_team && (p.classification||'').includes('leverage')).sort((a,b)=>(a.ownership_pct||0)-(b.ownership_pct||0));
  const shields=ex.filter(p=>p.in_my_team && (p.classification||'').includes('shield')).sort((a,b)=>(b.ownership_pct||0)-(a.ownership_pct||0));
  const swings=ex.filter(p=>p.points_swing_vs_league!==undefined).sort((a,b)=>Math.abs(b.points_swing_vs_league)-Math.abs(a.points_swing_vs_league));
  document.querySelector('#signals').innerHTML=[
    signalCard('🔥 Biggest threats',threats.slice(0,5),p=>pct(p.effective_ownership_pct??p.ownership_pct)),
    signalCard('🎯 Your leverage',leverage.slice(0,5),p=>pct(p.ownership_pct)),
    signalCard('🛡️ Your shields',shields.slice(0,5),p=>pct(p.ownership_pct)),
    signalCard('↕ Biggest swings',swings.slice(0,5),p=>`${Number(p.points_swing_vs_league).toFixed(1)}`)
  ].join('');
}

function renderSquad(d){
  const exposure=new Map((d.player_exposure||[]).map(p=>[p.player_id,p]));
  const squad=d.squad||[];
  document.querySelector('#squad-grid').innerHTML=squad.map(p=>{
    const e=exposure.get(p.player_id)||{};
    const live=p.live_points ?? e.live_points ?? '—';
    const label=e.classification||'neutral';
    return `<div class="player-card ${p.captain?'captain-ring':''}"><div class="player-name">${p.captain?'© ':''}${esc(p.player)}</div><div class="player-meta">${esc(p.position)} · ${esc(p.club)} · £${fmt(p.price)}</div><div class="player-points">${esc(live)}</div><div><span class="badge ${badgeClass(label)}">${esc(labelText(label))}</span></div></div>`;
  }).join('');
}

function renderHeatmap(d){
  const players=[...(d.player_exposure||[])].sort((a,b)=>(b.effective_ownership_pct??b.ownership_pct)-(a.effective_ownership_pct??a.ownership_pct)).slice(0,30);
  const head=`<div class="heat-row"><div class="heat-name">Player</div><div class="heat-cell">Owned</div><div class="heat-cell">Start</div><div class="heat-cell">Captain</div><div class="heat-cell">EO</div><div class="heat-cell">Signal</div></div>`;
  const rows=players.map(p=>{
    const eo=p.effective_ownership_pct??((p.starter_pct||0)+(p.captaincy_pct||0));
    return `<div class="heat-row"><div class="heat-name">${p.in_my_team?'★ ':''}${esc(p.player)}<br><span class="subtle">${esc(p.club||'')}</span></div><div class="heat-cell" data-intensity="${intensity(p.ownership_pct)}">${pct(p.ownership_pct)}</div><div class="heat-cell" data-intensity="${intensity(p.starter_pct)}">${pct(p.starter_pct)}</div><div class="heat-cell" data-intensity="${intensity(p.captaincy_pct)}">${pct(p.captaincy_pct)}</div><div class="heat-cell" data-intensity="${intensity(eo)}">${pct(eo)}</div><div class="heat-cell"><span class="badge ${badgeClass(p.classification)}">${esc(labelText(p.classification))}</span></div></div>`;
  }).join('');
  document.querySelector('#heatmap').innerHTML=head+rows;
}

function renderOverlap(d){
  const rivals=[...(d.rivals||[])].sort((a,b)=>(b.overlap_pct||0)-(a.overlap_pct||0));
  document.querySelector('#overlap-list').innerHTML=rivals.map(r=>`<div class="overlap-row"><div><strong>${esc(r.team_name)}</strong><div class="subtle">${fmt(r.overlap_count)}/15 shared</div></div><div class="bar"><span style="width:${Math.min(100,r.overlap_pct||0)}%"></span></div><div><strong>${pct(r.overlap_pct)}</strong></div></div>`).join('');
}

async function main(){
  try{
    const res=await fetch(`${DATA_URL}?t=${Date.now()}`,{cache:'no-store'}); if(!res.ok) throw new Error(`HTTP ${res.status}`);
    const d=await res.json();
    document.querySelector('#league-title').textContent=d.league?.name||'FPL Dashboard';
    document.querySelector('#gw-pill').textContent=`GW ${fmt(d.current_gw)}`;
    const stamp=d.generated_at_utc?new Date(d.generated_at_utc).toLocaleString():null;
    document.querySelector('#last-updated').textContent=stamp?`Snapshot updated ${stamp}`:'Latest snapshot';
    renderKpis(d); renderStandings(d); renderSignals(d); renderSquad(d); renderHeatmap(d); renderOverlap(d);
  }catch(err){
    document.body.innerHTML=`<main class="shell"><div class="error"><strong>Dashboard data could not be loaded.</strong><br>${esc(err.message)}<br><br>The dashboard files are present; check that data/latest.json exists in the public repository.</div></main>`;
  }
}
main();
