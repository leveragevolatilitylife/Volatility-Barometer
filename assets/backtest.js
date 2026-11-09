(function(){
'use strict';
var E=window.BTE,B=window.BARO,$=function(i){return document.getElementById(i)};
var NS='http://www.w3.org/2000/svg';
function el(t,a,x){var e=document.createElementNS(NS,t);for(var k in a)e.setAttribute(k,a[k]);if(x!=null)e.textContent=x;return e}
var STR=[['defensive','Defensive Rotation','QLD'],['tactical','Tactical Volatility','SVIX'],['tail','Strategic Tail Risk','SPY']];
var rows=[],events=[];
function opts(sel,list,def){$(sel).innerHTML=list.map(function(x){return '<option'+(x===def?' selected':'')+'>'+x+'</option>'}).join('')}
STR.forEach(function(s){opts('b_'+s[0],E.TICKERS,s[2])});
$('freq').innerHTML='<option value="ALL">每個時段（盤中即時調倉）</option>'+E.SLOTS.map(function(s){return '<option value="'+s+'">每日 '+s+' ET 單次決策'+(s==='10:30'?'（作者時點）':s==='16:00'?'（收盤）':s==='09:30'?'（開盤）':'')+'</option>'}).join('');
$('freq').value='ALL';
function pct(x){return (x>=0?'+':'')+(x*100).toFixed(2)+'%'}
function cls(x){return x>=0?'up':'dn'}
function params(){var g=function(i){return $(i).value};
 return {start:g('start'),freq:g('freq'),delay:g('delay'),cost:+g('cost')||0,minCov:$('mincov').checked?.95:null,tacLow:g('tacLow'),regime:g('regime'),events:events}}
function chart(svg,eq,name){svg.innerHTML='';var W=600,H=170,pl=40,pr=8,pt=8,pb=18;
 var vs=eq.map(function(e){return e.v}).concat(eq.map(function(e){return e.bench}));var lo=Math.min.apply(null,vs),hi=Math.max.apply(null,vs);if(hi-lo<.004){lo-=.002;hi+=.002}
 var X=function(i){return pl+i*(W-pl-pr)/Math.max(1,eq.length-1)},Y=function(v){return pt+(1-(v-lo)/(hi-lo))*(H-pt-pb)};
 for(var k=0;k<=3;k++){var v=lo+(hi-lo)*k/3;svg.appendChild(el('line',{x1:pl,x2:W-pr,y1:Y(v),y2:Y(v),stroke:'#171e26'}));svg.appendChild(el('text',{x:pl-4,y:Y(v)+3,'text-anchor':'end',fill:'#55626f','font-family':'JetBrains Mono','font-size':9},((v-1)*100).toFixed(1)+'%'))}
 svg.appendChild(el('line',{x1:pl,x2:W-pr,y1:Y(1),y2:Y(1),stroke:'#2a323c','stroke-dasharray':'3 3'}));
 var path=function(f){return eq.map(function(e,i){return (i?'L':'M')+X(i).toFixed(1)+' '+Y(f(e)).toFixed(1)}).join('')};
 svg.appendChild(el('path',{d:path(function(e){return e.bench}),fill:'none',stroke:'#8a97a6','stroke-width':1.3,'stroke-dasharray':'4 3'}));
 svg.appendChild(el('path',{d:path(function(e){return e.v}),fill:'none',stroke:'#c9805f','stroke-width':2}));
 var seen={};eq.forEach(function(e,i){if(!seen[e.date]){seen[e.date]=1;if(Object.keys(seen).length%Math.ceil(Object.keys(seen).length/1+0)===0||true){}}});
 var ds=Object.keys(seen),step=Math.max(1,Math.ceil(ds.length/6));ds.forEach(function(d,j){if(j%step)return;var i=eq.findIndex(function(e){return e.date===d});svg.appendChild(el('text',{x:X(i),y:H-4,'text-anchor':'middle',fill:'#55626f','font-family':'JetBrains Mono','font-size':9},d.slice(5)))})}
function render(){
 if(!rows.length){$('msg').innerHTML='<div class="warn">尚無紀錄資料（data/log.csv）。美股開盤後排程第一次執行完，這裡就會有數據。</div>';return}
 var p=params(),out=$('res');out.innerHTML='';var anyShort=false;
 $('cyc').textContent='目前利率週期判定：'+(function(){var d=rows[rows.length-1].date,r=E.regimeAt(events,d),last=events.length?events[events.length-1]:null;return (r==='hike'?'升息週期 → Tail 中間區間用 KO':'降息週期 → Tail 中間區間用 IYR')+(last?'（最近一次調整：'+last.date+' '+(last.dir==='hike'?'升息':'降息')+'，目標區間 '+last.range+'%）':'')})();
 STR.forEach(function(s){var o=Object.assign({},p,{bench:$('b_'+s[0]).value}),r=E.run(rows,s[0],o);
  var c=document.createElement('div');c.className='card';
  if(!r){c.innerHTML='<h2 style="font-size:17px;color:var(--heading)">'+s[1]+'</h2><p class="desc">所選開始日期之後的資料不足 2 筆。</p>';out.appendChild(c);anyShort=true;return}
  var held=Object.keys(r.held).map(function(k){return k+' '+(r.held[k]/r.nrows*100).toFixed(0)+'%'}).join(' · ');
  c.innerHTML='<div class="tick">'+s[1]+'</div><h2 style="font-size:17px;color:var(--heading);margin:4px 0">'+(r.ret>=r.bret?'領先':'落後')+'基準 '+pct(r.ret-r.bret)+'</h2>'+
   '<div class="stat"><div><small>策略總報酬</small><b class="'+cls(r.ret)+'">'+pct(r.ret)+'</b></div><div><small>基準 '+o.bench+'</small><b class="'+cls(r.bret)+'">'+pct(r.bret)+'</b></div>'+
   '<div><small>最大回撤</small><b>'+(r.mdd*100).toFixed(2)+'%</b></div><div><small>基準最大回撤</small><b>'+(r.bmdd*100).toFixed(2)+'%</b></div>'+
   '<div><small>調倉次數</small><b>'+r.ntrades+'</b></div><div><small>樣本</small><b>'+r.ndays+' 日 / '+r.nrows+' 筆</b></div></div><svg class="chart" viewBox="0 0 600 170" preserveAspectRatio="none"></svg><div class="desc" style="margin-top:6px">持有：'+held+'<br><span class="pill">橘實線＝策略</span> <span class="pill" style="color:#8a97a6;border-color:#2a323c">灰虛線＝基準</span></div>';
  out.appendChild(c);chart(c.querySelector('svg'),r.eq,s[1]);
  s.result=r});
 // 時段比較
 var variants=['ALL'].concat(E.SLOTS),h='<tr><th></th>'+variants.map(function(v){return '<th>'+(v==='ALL'?'每時段':v)+'</th>'}).join('')+'</tr>';
 var best={};
 STR.forEach(function(s){var o0=Object.assign({},p,{bench:$('b_'+s[0]).value}),rets=variants.map(function(v){var r=E.run(rows,s[0],Object.assign({},o0,{freq:v}));return r?r.ret:null});
  var mx=Math.max.apply(null,rets.filter(function(x){return x!=null}));
  h+='<tr><td>'+s[1]+'</td>'+rets.map(function(x){return x==null?'<td>–</td>':'<td class="'+cls(x)+'" style="'+(x===mx?'font-weight:700;text-decoration:underline':'')+'">'+pct(x)+'</td>'}).join('')+'</tr>';
  var br=E.run(rows,s[0],Object.assign({},o0,{freq:'ALL'}));if(br)h+='<tr><td class="desc">　基準 '+o0.bench+'</td><td class="desc" colspan="'+variants.length+'" style="text-align:left">'+pct(br.bret)+'</td></tr>'});
 $('cmp').innerHTML=h;
 // 調倉明細（目前頻率）
 var th='<tr><th>策略</th><th>日期</th><th>時段</th><th>由</th><th>至</th><th>成交價</th><th>溫度計</th></tr>',n=0;
 STR.forEach(function(s){var r=E.run(rows,s[0],Object.assign({},p,{bench:$('b_'+s[0]).value}));if(!r)return;r.trades.forEach(function(t){n++;th+='<tr><td>'+s[1].split(' ')[0]+'</td><td>'+t.date+'</td><td>'+t.slot+'</td><td>'+t.from+'</td><td>'+t.to+'</td><td>'+(t.price==null?'–':t.price.toFixed(2))+'</td><td>'+(t.b==null?'–':(t.b*100).toFixed(1)+'%')+'</td></tr>'})});
 $('trades').innerHTML=n?th:'<tr><td>無調倉</td></tr>';
 $('msg').innerHTML=anyShort?'':(rows.length<60?'<div class="warn">⚠ 目前僅累積 '+rows.length+' 筆時段資料（約 '+Math.ceil(rows.length/14)+' 個交易日），報酬差異可能只是雜訊；建議累積數週後再解讀。</div>':'')}
function load(){Promise.all([B.get('log.csv',1),B.get('rate_cycle.json')]).then(function(r){
 rows=r[0]?E.prep(B.parseCSV(r[0])):[];events=r[1]?r[1].events:[];
 var days=Array.from(new Set(rows.map(function(x){return x.date}))).sort();
 var cur=$('start').value;$('start').innerHTML=days.map(function(d){return '<option>'+d+'</option>'}).join('');if(cur&&days.indexOf(cur)>=0)$('start').value=cur;
 render()})}
['start','freq','delay','cost','tacLow','regime','mincov','b_defensive','b_tactical','b_tail'].forEach(function(i){$(i).addEventListener('change',render);$(i).addEventListener('input',render)});
B.initUpdate($('updmount'),load);
load();
})();
