/* 回測引擎（純函式，可在 node 測試）。資料列＝data/log.csv 的每個時段。 */
(function(root){
'use strict';
var SLOTS=['09:30','10:00','10:30','11:00','11:30','12:00','12:30','13:00','13:30','14:00','14:30','15:00','15:30','16:00'];
var TICKERS=['SVIX','SVXY','GLD','VXZ','QLD','QQQ','XLU','SPY','IYR','KO','CAOS'];
function num(x){var v=parseFloat(x);return isNaN(v)?null:v}
function prep(raw){return raw.map(function(r){var o={date:r.date,slot:r.slot,late:r.late==='1',b:num(r.barometer),cov:num(r.coverage),ts:num(r.tail_score),P:{}};TICKERS.forEach(function(t){o.P[t]=num(r[t])});return o})
 .sort(function(a,b){return a.date<b.date?-1:a.date>b.date?1:SLOTS.indexOf(a.slot)-SLOTS.indexOf(b.slot)})}
/* 利率週期：events=[{date,dir}]；回傳該日所屬週期 'cut'|'hike' */
function regimeAt(events,date){var r='cut';(events||[]).forEach(function(e){if(e.date<=date)r=e.dir});return r}
/* 各策略的持倉決策。st 為可變狀態(Defensive 磁滯鎖定) */
function decide(strat,row,opt,st){
 if(strat==='defensive'){var b=row.b;if(b<0.20)st.low=true;else if(b>=0.30)st.low=false;
  if(st.low)return 'CASH';return b>=0.85?'CASH':(b>=0.66?'XLU':'QLD')}
 if(strat==='tactical'){var b2=row.b;return b2<0.60?opt.tacLow:(b2<0.95?'GLD':'VXZ')}
 var s=row.ts;if(s==null)s=row.b;
 if(s<0.60)return 'SPY';if(s<0.90){var rg=opt.regime==='auto'?regimeAt(opt.events,row.date):opt.regime;return rg==='hike'?'KO':'IYR'}return 'CAOS'}
/* opt:{start, freq:'ALL'|slot, delay:'same'|'next', cost(bps/邊), minCov, tacLow, regime, events, bench} */
function run(rows,strat,opt){
 var R=rows.filter(function(r){return r.date>=opt.start});if(R.length<2)return null;
 var st={low:false},pos='CASH',pend=null,v=1,eq=[],trades=[],fee=(opt.cost||0)/1e4,last={};
 var bench=1,bq=[],bl={};
 TICKERS.forEach(function(t){last[t]=null});
 var held={};
 for(var i=0;i<R.length;i++){var r=R[i],pr=i?R[i-1]:null;
  if(i&&pos!=='CASH'){var a=pr.P[pos],b=r.P[pos];if(a!=null&&b!=null)v*=b/a}
  // 基準：買進持有（價格缺漏時沿用上一價）
  var bp=r.P[opt.bench];if(bp!=null){if(bl.base==null)bl.base=bp;bl.cur=bp}
  bench=bl.base?bl.cur/bl.base:1;
  function sw(np,why){var sides=(pos!=='CASH'?1:0)+(np!=='CASH'?1:0);v*=1-fee*sides;trades.push({date:r.date,slot:r.slot,from:pos,to:np,price:np==='CASH'?null:r.P[np],b:r.b});pos=np}
  if(pend!==null){if(pend!==pos)sw(pend);pend=null}
  var isDec=(opt.freq==='ALL'||r.slot===opt.freq)&&r.b!=null&&(opt.minCov==null||r.cov==null||r.cov>=opt.minCov)&&!(opt.minCov!=null&&r.late);
  if(isDec){var np=decide(strat,r,opt,st);if(np!==pos){if(opt.delay==='next'&&i<R.length-1)pend=np;else sw(np)}}
  held[pos]=(held[pos]||0)+1;
  eq.push({date:r.date,slot:r.slot,v:v,bench:bench,pos:pos})}
 var peak=0,mdd=0,bpeak=0,bmdd=0;eq.forEach(function(e){peak=Math.max(peak,e.v);mdd=Math.min(mdd,e.v/peak-1);bpeak=Math.max(bpeak,e.bench);bmdd=Math.min(bmdd,e.bench/bpeak-1)});
 var days={};R.forEach(function(r){days[r.date]=1});
 return {eq:eq,trades:trades,ret:v-1,bret:bench-1,mdd:mdd,bmdd:bmdd,ntrades:trades.length-(trades.length&&trades[0].from==='CASH'?1:0),held:held,nrows:R.length,ndays:Object.keys(days).length}}
var api={SLOTS:SLOTS,TICKERS:TICKERS,prep:prep,regimeAt:regimeAt,decide:decide,run:run};
if(typeof module!=='undefined')module.exports=api;else root.BTE=api;
})(this);
