const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const window={},document={readyState:'loading',addEventListener(){}};
vm.runInNewContext(fs.readFileSync('docs/gw-scorecard-carousel-stage87.js','utf8'),{window,document});
const {captainScore,card}=window.FPLScorecardTest;
const d={current_gw:8,me:{captain:'João Pedro'},squad:[
{player_id:165,player:'João Pedro',captain:true,multiplier:2,live_points:0},
{player_id:411,player:'Haaland',vice_captain:true,multiplier:1,live_points:8}]};
const o={players:[{player_id:165,minutes:0,total_points:0},{player_id:411,minutes:90,total_points:8}]};
assert.equal(captainScore(d,o).name,'Haaland');assert.equal(captainScore(d,o).points,16);
assert.match(card({snap:d,outcomes:o}),/Haaland · 16 pts · VC promoted \(João Pedro DNP\)/);
o.players[0].minutes=1;
assert.equal(captainScore(d,o).name,'João Pedro');
o.players[0].minutes=0;o.players[1].minutes=0;o.players[1].total_points=0;
assert.equal(captainScore(d,o).points,0);assert.equal(captainScore(d,o).handover,false);
assert.equal(captainScore(d,null).handover,false);
o.players[1].minutes=90;o.players[1].total_points=8;d.me.active_chip='3xc';
assert.equal(captainScore(d,o).points,24);
d.squad[1].multiplier=2;
assert.equal(captainScore(d,null).name,'Haaland');assert.equal(captainScore(d,null).points,16);
console.log('Scorecard captain handover regression checks passed');
