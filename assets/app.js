(function(){
'use strict';
var base=new URLSearchParams(location.search).get('data')||'data';
var $=function(i){return document.getElementById(i)};
var NS='http://www.w3.org/2000/svg';
function get(f,csv){return fetch(base+'/'+f+'?_='+Math.floor(Date.now()/60000)).then(function(r){if(!r.ok)throw 0;return csv?r.text():r.json()}).catch(function(){return null})}
function pct(x){return x==null?'--':(x*100).toFixed(1)+'%'}
function el(t,a,txt){var e=document.createElementNS(NS,t);for(var k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e}
function parseCSV(t){var L=t.trim().split(/\r?\n/);var h=L.shift().split(',');return L.map(function(l){var c=l.split(',');var o={};h.forEach(function(k,i){o[k]=c[i]});return o})}
var ZONES=[[0,.2,'Defensive 低波動 Cash'],[.2,.6,'QLD / SVIX / SPY 區'],[.6,.66,'Tactical 轉 GLD'],[.66,.85,'XLU'],[.85,.95,'Defensive Cash'],[.95,1,'Tactical VXZ']];
function zoneName(b){return b<.2?'低波動（<20%）':b<.6?'偏低風險':b<.66?'中性偏高':b<.85?'警戒':b<.95?'高風險':'極端恐慌（≥95%）'}
function polar(cx,cy,r,v){var a=Math.PI*(1-v);return [cx+r*Math.cos(a),cy-r*Math.sin(a)]}
function arc(cx,cy,r,v0,v1){var p0=polar(cx,cy,r,v0),p1=polar(cx,cy,r,v1);return 'M'+p0[0]+' '+p0[1]+' A'+r+' '+r+' 0 0 1 '+p1[0]+' '+p1[1]}
function gauge(b){var s=$('gauge');s.innerHTML='';var cx=200,cy=205,r=150;
 s.appendChild(el('path',{d:arc(cx,cy,r,0,1),fill:'none',stroke:'#171e26','stroke-width':22,'stroke-linecap':'round'}));
 if(b!=null){s.appendChild(el('path',{d:arc(cx,cy,r,0.001,Math.max(b,0.004)),fill:'none',stroke:'#c9805f','stroke-width':22,'stroke-linecap':'round'}))}
 [.2,.6,.66,.85,.95].forEach(function(v){var a=polar(cx,cy,r-18,v),c=polar(cx,cy,r+18,v),t=polar(cx,cy,r+32,v);
  s.appendChild(el('line',{x1:a[0],y1:a[1],x2:c[0],y2:c[1],stroke:'#55626f','stroke-width':1.2}));
  s.appendChild(el('text',{x:t[0],y:t[1]+3,'text-anchor':'middle','font-family':'JetBrains Mono','font-size':10,fill:'#55626f'},Math.round(v*100)))});
 if(b!=null){var n=polar(cx,cy,r-34,b);s.appendChild(el('line',{x1:cx,y1:cy,x2:n[0],y2:n[1],stroke:'#e7edf3','stroke-width':3,'stroke-linecap':'round'}));s.appendChild(el('circle',{cx:cx,cy:cy,r:7,fill:'#e7edf3'}))}
 s.appendChild(el('text',{x:20,y:228,'font-family':'JetBrains Mono','font-size':10,fill:'#55626f'},'0'));s.appendChild(el('text',{x:372,y:228,'font-family':'JetBrains Mono','font-size':10,fill:'#55626f'},'100'))}
function lineChart(svg,xs,ys,opts){svg.innerHTML='';var W=900,H=220,pl=38,pr=10,pt=10,pb=22;
 if(!ys.length){svg.appendChild(el('text',{x:W/2,y:H/2,'text-anchor':'middle',fill:'#55626f','font-family':'JetBrains Mono','font-size':14},'尚無資料'));return}
 var X=function(i){return pl+(ys.length<2?(W-pl-pr)/2:i*(W-pl-pr)/(ys.length-1))},Y=function(v){return pt+(1-v)*(H-pt-pb)};
 (opts.lines||[]).forEach(function(v){svg.appendChild(el('line',{x1:pl,x2:W-pr,y1:Y(v),y2:Y(v),stroke:'#202932','stroke-dasharray':'4 4'}));svg.appendChild(el('text',{x:pl-5,y:Y(v)+3,'text-anchor':'end',fill:'#55626f','font-family':'JetBrains Mono','font-size':10},Math.round(v*100)))});
 var d=ys.map(function(v,i){return (i?'L':'M')+X(i)+' '+Y(v)}).join('');
 svg.appendChild(el('path',{d:d,fill:'none',stroke:'#c9805f','stroke-width':2,'vector-effect':'non-scaling-stroke'}));
 ys.forEach(function(v,i){if(ys.length<=90)svg.appendChild(el('circle',{cx:X(i),cy:Y(v),r:ys.length>40?2:3.5,fill:'#c9805f'}))});
 var step=Math.max(1,Math.ceil(xs.length/8));xs.forEach(function(x,i){if(i%step===0||i===xs.length-1)svg.appendChild(el('text',{x:X(i),y:H-6,'text-anchor':'middle',fill:'#55626f','font-family':'JetBrains Mono','font-size':10},x))})}
var STR=[['defensive','Defensive Rotation','QLD / XLU / Cash','<20% 或磁滯鎖定 → Cash；20–66% QLD；66–85% XLU；≥85% Cash（需升回30%才解除低波動Cash）'],
['tactical','Tactical Volatility','SVIX / GLD / VXZ','<60% SVIX；60–95% GLD；≥95% VXZ'],
['tail','Strategic Tail Risk','SPY / IYR·KO / CAOS','0.8×溫度計＋0.2×S&P價格訊號：<60% SPY；60–90% IYR/KO；≥90% CAOS']];
Promise.all([get('live.json'),get('snapshots.csv',1),get('intraday_today.json')]).then(function(r){
 var L=r[0],S=r[1]?parseCSV(r[1]):[],T=r[2];
 if(!L){$('asof').textContent='尚無即時資料（等待第一次排程執行）';gauge(null)}
 else{var b=L.barometer;gauge(b);$('val').textContent=pct(b);$('zone').textContent=zoneName(b);
  $('asof').textContent='交易日 '+L.trade_date+' · 更新 '+L.asof_et.slice(11,16)+' ET'+(L.bar_time_et?' · 最新K線 '+L.bar_time_et:'');
  $('kv').innerHTML=[['VIX',L.inputs.VIX],['VIX9D',L.inputs.VIX9D],['VIX3M',L.inputs.VIX3M],['S&P價格訊號',L.price_signal*100,'%'],['覆蓋率',L.coverage*100,'%']].map(function(k){return '<div><small>'+k[0]+'</small><b>'+(k[1]==null?'--':(+k[1]).toFixed(k[2]?0:2)+(k[2]||''))+'</b></div>'}).join('');
  if(L.coverage<.95){var w=$('warn');w.style.display='block';w.textContent='⚠ 覆蓋率 '+(L.coverage*100).toFixed(0)+'%：部分指標（多為 VIX 期貨）暫缺，已重新正規化，數值僅供參考。'}
  $('strats').innerHTML=STR.map(function(s){return '<div class="card st"><div class="tick">'+s[2]+'</div><h2>'+s[1]+'</h2><div class="pos">'+L.strategies[s[0]]+'</div><div class="desc">'+s[3]+'</div></div>'}).join('');
  var rows=(window.WEIGHTS||[]);
  var h='<tr><th>指標</th><th class="num">數值</th><th>風險分位</th><th class="num">權重</th></tr>';
  Object.keys(L.metrics).forEach(function(k){var m=L.metrics[k];h+='<tr><td>'+k+'</td><td class="num">'+(m.value==null?'<span class="na">缺</span>':m.value.toFixed(4))+'</td><td>'+(m.risk==null?'<span class="na">--</span>':'<div class="bar"><i style="width:'+(m.risk*100)+'%"></i></div> <small class="na">'+(m.risk*100).toFixed(0)+'%</small>')+'</td><td class="num" data-w="'+k+'"></td></tr>'});
  $('mt').innerHTML=h;
  get('weights.json').then(function(w){if(!w)return;w.metrics.forEach(function(m){var c=document.querySelector('[data-w="'+m.name+'"]');if(c)c.textContent=(m.weight*100).toFixed(1)+'%'})})}
 var pts=(T&&L&&T.date===L.trade_date)?T.points:[];lineChart($('intra'),pts.map(function(p){return p.t}),pts.map(function(p){return p.b}),{lines:[.2,.6,.66,.85,.95]});
 $('intra-lg').textContent=pts.length?'共 '+pts.length+' 個資料點':'';
 var ok=S.filter(function(x){return x.barometer!==''});
 lineChart($('hist'),ok.map(function(x){return x.date.slice(5)}),ok.map(function(x){return +x.barometer}),{lines:[.2,.6,.66,.85,.95]});
 var h='<tr><th>日期</th><th>K線(ET)</th><th class="num">溫度計</th><th>Defensive</th><th>Tactical</th><th>Tail</th><th class="num">VIX</th><th class="num">覆蓋</th></tr>';
 ok.slice().reverse().slice(0,60).forEach(function(x){h+='<tr><td>'+x.date+'</td><td>'+x.bar_time_et+'</td><td class="num">'+pct(+x.barometer)+'</td><td>'+x.defensive+'</td><td>'+x.tactical+'</td><td>'+x.tail+'</td><td class="num">'+(+x.VIX).toFixed(2)+'</td><td class="num">'+(+x.coverage*100).toFixed(0)+'%</td></tr>'});
 $('snaps').innerHTML=ok.length?h:'<tr><td class="na">尚無紀錄 — 下一個美股交易日開盤後約一小時將自動寫入</td></tr>';
});
})();
