(function(){
'use strict';
var base=new URLSearchParams(location.search).get('data')||'data';
var $=function(i){return document.getElementById(i)};
var NS='http://www.w3.org/2000/svg';
var TICKERS=['SVIX','SVXY','GLD','VXZ','QLD','QQQ','XLU','SPY','IYR','KO','CAOS'];
/* 風險色階：與「台股波動率/均線輪換策略儀表板」相同 —— 10 格，最差 #FF2400 → 中位 #FFE135 → 最佳 #00FF7F */
var RISK_STEPS=(function(){var R=[255,36,0],M=[255,225,53],G=[0,255,127];var o=[];for(var i=0;i<10;i++){var t=i/9,a=t<.5?R:M,b=t<.5?M:G,u=t<.5?t/.5:(t-.5)/.5;o.push(a.map(function(v,k){return Math.round(v+(b[k]-v)*u)}))}return o})();
/* risk：0=低風險 … 1=高風險；回傳該格 rgb */
function riskRgb(risk){if(risk==null||isNaN(risk))return null;var f=Math.max(0,Math.min(1,1-risk));return RISK_STEPS[Math.min(9,Math.floor(f*10))]}
function rgba(c,a){return 'rgba('+c[0]+','+c[1]+','+c[2]+','+a+')'}
function rkCell(risk,txt){var c=riskRgb(risk);return c?'<td class="rk" style="background:'+rgba(c,.62)+';box-shadow:inset 0 0 0 1px '+rgba(c,.9)+'">'+txt+'</td>':'<td class="na">'+txt+'</td>'}
/* 倉位字色：依該倉位所對應的風險區間，取區間中點套用同一組紅黃綠色階（綠＝低風險區、紅＝高風險區） */
function posRisk(st,pos,b,ts){
 if(st==='defensive')return pos==='Cash'?(b>=.85?.925:.10):(pos==='QLD'?.43:.755);
 if(st==='tactical')return pos==='GLD'?.775:(pos==='VXZ'?.975:.30);
 return pos==='SPY'?.30:(pos==='CAOS'?.95:.75)}
function posColor(st,pos,b,ts){var c=riskRgb(posRisk(st,pos,b,ts));return c?'rgb('+c.join(',')+')':''}
function get(f,csv){return fetch(base+'/'+f+'?_='+Math.floor(Date.now()/60000)).then(function(r){if(!r.ok)throw 0;return csv?r.text():r.json()}).catch(function(){return null})}
function pct(x){return x==null||isNaN(x)?'--':(x*100).toFixed(1)+'%'}
function el(t,a,txt){var e=document.createElementNS(NS,t);for(var k in a)e.setAttribute(k,a[k]);if(txt!=null)e.textContent=txt;return e}
function parseCSV(t){var L=t.trim().split(/\r?\n/);var h=L.shift().split(',');return L.map(function(l){var c=l.split(',');var o={};h.forEach(function(k,i){o[k]=c[i]});return o})}
function zoneName(b){return b<.2?'低波動（<20%）':b<.6?'低風險':b<.66?'中性偏高':b<.85?'警戒':b<.95?'高風險':'極端恐慌（≥95%）'}
function polar(cx,cy,r,v){var a=Math.PI*(1-v);return [cx+r*Math.cos(a),cy-r*Math.sin(a)]}
function arcPath(cx,cy,r,v0,v1){var p0=polar(cx,cy,r,v0),p1=polar(cx,cy,r,v1);return 'M'+p0[0].toFixed(2)+' '+p0[1].toFixed(2)+' A'+r+' '+r+' 0 0 1 '+p1[0].toFixed(2)+' '+p1[1].toFixed(2)}
/* ===== 溫度計儀表 ===== */
function gauge(b){var s=$('gauge');s.innerHTML='';var cx=220,cy=215,R=160,W=22;
 var defs=el('defs',{});var f=el('filter',{id:'glow',x:'-30%',y:'-30%',width:'160%',height:'160%'});f.appendChild(el('feGaussianBlur',{stdDeviation:'2.2',result:'b'}));var mg=el('feMerge',{});mg.appendChild(el('feMergeNode',{in:'b'}));mg.appendChild(el('feMergeNode',{in:'SourceGraphic'}));f.appendChild(mg);defs.appendChild(f);s.appendChild(defs);
 s.appendChild(el('path',{d:arcPath(cx,cy,R+W/2+6,0,1),fill:'none',stroke:'#202932','stroke-width':1}));
 for(var i=0;i<10;i++){var c=RISK_STEPS[9-i];s.appendChild(el('path',{d:arcPath(cx,cy,R,i/10+.002,(i+1)/10-.002),fill:'none',stroke:'rgb('+c.join(',')+')','stroke-width':W,opacity:b!=null&&((i+1)/10<=b+.0001||(i/10<b))?1:.32}))}
 for(var k=0;k<=40;k++){var v=k/40,maj=k%4===0,a=polar(cx,cy,R-W/2-3,v),c2=polar(cx,cy,R-W/2-(maj?13:8),v);s.appendChild(el('line',{x1:a[0],y1:a[1],x2:c2[0],y2:c2[1],stroke:maj?'#8a97a6':'#3a4654','stroke-width':maj?1.6:1}));
  if(maj){var t=polar(cx,cy,R-W/2-26,v);s.appendChild(el('text',{x:t[0],y:t[1]+3.5,'text-anchor':'middle','font-family':'JetBrains Mono','font-size':11,fill:'#8a97a6'},Math.round(v*100)))}}
 [[.2,'20'],[.6,'60'],[.66,'66'],[.85,'85'],[.95,'95']].forEach(function(m){var p0=polar(cx,cy,R+W/2+2,m[0]),p1=polar(cx,cy,R+W/2+11,m[0]),t=polar(cx,cy,R+W/2+23,m[0]);
  s.appendChild(el('line',{x1:p0[0],y1:p0[1],x2:p1[0],y2:p1[1],stroke:'#c9805f','stroke-width':2.4}));
  s.appendChild(el('text',{x:t[0],y:t[1]+3.5,'text-anchor':'middle','font-family':'JetBrains Mono','font-size':10.5,'font-weight':600,fill:'#c9805f'},m[1]))});
 var g=el('g',{id:'needle',filter:'url(#glow)'});g.style.transformOrigin=cx+'px '+cy+'px';g.style.transition='transform 1.1s cubic-bezier(.2,.9,.25,1)';g.style.transform='rotate(0deg)';
 g.appendChild(el('polygon',{points:(cx-R+W/2+2)+','+cy+' '+(cx-12)+','+(cy-4.5)+' '+(cx+22)+','+cy+' '+(cx-12)+','+(cy+4.5),fill:'#f4f7fa'}));
 s.appendChild(g);
 s.appendChild(el('circle',{cx:cx,cy:cy,r:13,fill:'#0a0e14',stroke:'#e7edf3','stroke-width':2.5}));s.appendChild(el('circle',{cx:cx,cy:cy,r:4,fill:'#c9805f'}));
 if(b!=null)requestAnimationFrame(function(){requestAnimationFrame(function(){g.style.transform='rotate('+(Math.max(0,Math.min(1,b))*180)+'deg)'})});
 var lab=b!=null?pct(b):'--';var c3=riskRgb(b);
 s.appendChild(el('text',{x:cx,y:cy-52,'text-anchor':'middle','font-family':'JetBrains Mono','font-size':34,'font-weight':700,fill:c3?'rgb('+c3.join(',')+')':'#8a97a6'},lab));
 s.appendChild(el('text',{x:cx,y:cy-32,'text-anchor':'middle','font-family':'Noto Sans TC','font-size':11.5,fill:'#8a97a6'},b!=null?zoneName(b):'等待資料'))}
/* ===== 折線／時段圖 ===== */
function lineChart(svg,xs,ys,opts){svg.innerHTML='';var W=900,H=220,pl=38,pr=10,pt=10,pb=22;
 if(!ys.length){svg.appendChild(el('text',{x:W/2,y:H/2,'text-anchor':'middle',fill:'#55626f','font-family':'JetBrains Mono','font-size':14},'尚無資料'));return}
 var X=function(i){return pl+(ys.length<2?(W-pl-pr)/2:i*(W-pl-pr)/(ys.length-1))},Y=function(v){return pt+(1-v)*(H-pt-pb)};
 [0,.2,.6,.66,.85,.95,1].forEach(function(v){var th=v>0&&v<1;svg.appendChild(el('line',{x1:pl,x2:W-pr,y1:Y(v),y2:Y(v),stroke:th?'#2a323c':'#171e26','stroke-dasharray':th?'4 4':''}));svg.appendChild(el('text',{x:pl-5,y:Y(v)+3,'text-anchor':'end',fill:'#55626f','font-family':'JetBrains Mono','font-size':10},Math.round(v*100)))});
 svg.appendChild(el('path',{d:ys.map(function(v,i){return (i?'L':'M')+X(i)+' '+Y(v)}).join(''),fill:'none',stroke:'#8a97a6','stroke-width':1.4,'vector-effect':'non-scaling-stroke',opacity:.8}));
 ys.forEach(function(v,i){var c=riskRgb(v),hollow=opts.hollow&&opts.hollow[i];svg.appendChild(el('circle',{cx:X(i),cy:Y(v),r:ys.length>40?2.5:5,fill:hollow?'#0a0e14':'rgb('+c.join(',')+')',stroke:'rgb('+c.join(',')+')','stroke-width':hollow?1.8:0}))});
 var step=Math.max(1,Math.ceil(xs.length/9));xs.forEach(function(x,i){if(i%step===0||i===xs.length-1)svg.appendChild(el('text',{x:X(i),y:H-6,'text-anchor':'middle',fill:'#55626f','font-family':'JetBrains Mono','font-size':10},x))})}
var STR=[['defensive','Defensive Rotation','QLD / XLU / Cash','<20% 或磁滯鎖定 → Cash；20–66% QLD；66–85% XLU；≥85% Cash（需升回30%才解除低波動Cash）'],
['tactical','Tactical Volatility','SVIX / GLD / VXZ','<60% SVIX；60–95% GLD；≥95% VXZ'],
['tail','Strategic Tail Risk','SPY / IYR·KO / CAOS','0.8×溫度計＋0.2×S&P價格訊號：<60% SPY；60–90% IYR/KO；≥90% CAOS']];
$('scale').innerHTML=RISK_STEPS.slice().reverse().map(function(c){return '<b style="background:rgb('+c.join(',')+')"></b>'}).join('');
if(window.BARO)BARO.initUpdate($('updmount'),function(){location.reload()});
Promise.all([get('live.json'),get('log.csv',1),get('weights.json')]).then(function(r){
 var L=r[0],S=r[1]?parseCSV(r[1]):[],Wt=r[2];
 if(!L){$('asof').textContent='尚無即時資料（等待第一次排程執行）';gauge(null)}
 else{var b=L.barometer;gauge(b);$('val').textContent=pct(b);$('val').style.color=(function(){var c=riskRgb(b);return c?'rgb('+c.join(',')+')':''})();$('zone').textContent=zoneName(b);
  $('asof').textContent='資料日 '+L.trade_date+' · 更新 '+L.asof_et.slice(11,16)+' ET'+(L.bar_time_et?' · 最新K線 '+L.bar_time_et:'');
  $('kv').innerHTML=[['VIX',L.inputs.VIX],['VIX9D',L.inputs.VIX9D],['VIX3M',L.inputs.VIX3M],['S&P價格訊號',L.price_signal*100,'%'],['覆蓋率',L.coverage*100,'%']].map(function(k){return '<div><small>'+k[0]+'</small><b>'+(k[1]==null?'--':(+k[1]).toFixed(k[2]?0:2)+(k[2]||''))+'</b></div>'}).join('');
  if(L.coverage<.95){var w=$('warn');w.style.display='block';w.textContent='⚠ 覆蓋率 '+(L.coverage*100).toFixed(0)+'%：部分指標（多為 VIX 期貨）暫缺，已重新正規化，數值僅供參考。'}
  $('strats').innerHTML=STR.map(function(s){return '<div class="card st"><div class="tick">'+s[2]+'</div><h2>'+s[1]+'</h2><div class="pos" style="color:'+posColor(s[0],L.strategies[s[0]],L.barometer,L.tail_score)+'">'+L.strategies[s[0]]+'</div><div class="desc">'+s[3]+'</div></div>'}).join('');
  var wm={};if(Wt)Wt.metrics.forEach(function(m){wm[m.name]=m.weight});
  var h='<tr><th>指標</th><th class="num">數值</th><th>風險分位</th><th class="num">權重</th></tr>';
  Object.keys(L.metrics).forEach(function(k){var m=L.metrics[k];h+='<tr><td>'+k+'</td><td class="num">'+(m.value==null?'<span class="na">缺</span>':m.value.toFixed(4))+'</td>'+rkCell(m.risk,m.risk==null?'--':(m.risk*100).toFixed(0)+'%')+'<td class="num">'+(wm[k]!=null?(wm[k]*100).toFixed(1)+'%':'')+'</td></tr>'});
  $('mt').innerHTML=h}
 /* 時段紀錄 */
 var days=Array.from(new Set(S.map(function(x){return x.date}))).sort().reverse();
 var sel=$('daysel');sel.innerHTML=days.map(function(d){return '<option>'+d+'</option>'}).join('');
 function show(){var d=sel.value,rows=S.filter(function(x){return x.date===d});
  lineChart($('intra'),rows.map(function(x){return x.slot}),rows.map(function(x){return +x.barometer}),{hollow:rows.map(function(x){return x.late==='1'||+x.coverage<.95})});
  $('logmeta').textContent=rows.length?('已記錄 '+rows.length+' / 14 個時段；累計 '+S.length+' 筆 / '+days.length+' 個交易日'):'';
  var h='<tr><th>時段 ET</th><th class="num">溫度計</th><th>Def</th><th>Tac</th><th>Tail</th><th class="num">VIX</th>'+TICKERS.map(function(t){return '<th class="num">'+t+'</th>'}).join('')+'<th class="num">覆蓋</th></tr>';
  rows.forEach(function(x){h+='<tr class="'+(x.late==='1'?'slotrow-late':'')+'"><td>'+x.slot+(x.late==='1'?' *':'')+'</td>'+rkCell(+x.barometer,pct(+x.barometer))+'<td style="color:'+posColor('defensive',x.defensive,+x.barometer)+';font-weight:600">'+x.defensive+'</td><td style="color:'+posColor('tactical',x.tactical,+x.barometer)+';font-weight:600">'+x.tactical+'</td><td style="color:'+posColor('tail',x.tail.split('/')[0]==='IYR'?'IYR/KO':x.tail,+x.barometer,+x.tail_score)+';font-weight:600">'+x.tail+'</td><td class="num">'+(+x.VIX).toFixed(2)+'</td>'+TICKERS.map(function(t){return '<td class="num">'+(x[t]===''?'<span class="na">–</span>':(+x[t]).toFixed(2))+'</td>'}).join('')+'<td class="num">'+(+x.coverage*100).toFixed(0)+'%</td></tr>'});
  $('snaps').innerHTML=rows.length?h:'<tr><td class="na">尚無紀錄 — 下一個美股交易日開盤時起自動寫入（* 為補記，期貨缺漏）</td></tr>'}
 sel.onchange=show;show();
 var k=S.filter(function(x){return x.slot==='10:30'});
 lineChart($('hist'),k.map(function(x){return x.date.slice(5)}),k.map(function(x){return +x.barometer}),{hollow:k.map(function(x){return x.late==='1'||+x.coverage<.95})});
});
})();
