/* 共用：資料路徑、色階、CSV 解析、「立即更新」按鈕（以 GitHub API 觸發 workflow） */
(function(){
'use strict';
var B=window.BARO={};
B.base=new URLSearchParams(location.search).get('data')||'data';
B.get=function(f,csv){return fetch(B.base+'/'+f+'?_='+Math.floor(Date.now()/60000)).then(function(r){if(!r.ok)throw 0;return csv?r.text():r.json()}).catch(function(){return null})};
B.parseCSV=function(t){var L=t.trim().split(/\r?\n/);var h=L.shift().split(',');return L.map(function(l){var c=l.split(',');var o={};h.forEach(function(k,i){o[k]=c[i]});return o})};
B.STEPS=(function(){var R=[255,36,0],M=[255,225,53],G=[0,255,127],o=[];for(var i=0;i<10;i++){var t=i/9,a=t<.5?R:M,b=t<.5?M:G,u=t<.5?t/.5:(t-.5)/.5;o.push(a.map(function(v,k){return Math.round(v+(b[k]-v)*u)}))}return o})();
B.riskRgb=function(r){if(r==null||isNaN(r))return null;return B.STEPS[Math.min(9,Math.floor(Math.max(0,Math.min(1,1-r))*10))]};
/* ---- 立即更新 ---- */
var host=location.hostname,parts=location.pathname.split('/').filter(Boolean);
B.repo=(host.endsWith('.github.io')?host.split('.')[0]:'leveragevolatilitylife')+'/'+(host.endsWith('.github.io')&&parts[0]?parts[0]:'Volatility-Barometer');
var KEY='baro_gh_token';
function tok(){try{return localStorage.getItem(KEY)||''}catch(e){return ''}}
function setTok(v){try{v?localStorage.setItem(KEY,v):localStorage.removeItem(KEY)}catch(e){}}
B.initUpdate=function(mount,onDone){
 var wrap=document.createElement('span');wrap.className='upd';
 wrap.innerHTML='<button class="btn" id="upd-btn">↻ 立即更新資料</button><button class="btn ghost" id="upd-set" title="設定 GitHub Token">⚙</button><span class="upd-msg" id="upd-msg"></span>';
 mount.appendChild(wrap);var msg=wrap.querySelector('#upd-msg');
 function say(t,c){msg.textContent=t;msg.style.color=c||''}
 wrap.querySelector('#upd-set').onclick=function(){
  var v=prompt('貼上 GitHub fine-grained token（僅限本 repo、Actions: Read and write）。\n只存在這個瀏覽器的 localStorage。留空並確定＝清除。',tok());
  if(v!==null){setTok(v.trim());say(v.trim()?'Token 已儲存':'Token 已清除')}};
 wrap.querySelector('#upd-btn').onclick=function(){
  var t=tok();if(!t){wrap.querySelector('#upd-set').click();t=tok();if(!t)return}
  say('觸發中…');
  fetch('https://api.github.com/repos/'+B.repo+'/actions/workflows/barometer.yml/dispatches',{method:'POST',headers:{'Authorization':'Bearer '+t,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},body:JSON.stringify({ref:'main',inputs:{mode:'auto',force:'true'}})})
  .then(function(r){if(r.status===204){say('已觸發，約 60–90 秒後自動重新載入資料…','#34d399');setTimeout(function(){say('');onDone&&onDone()},80000)}
   else if(r.status===401||r.status===403||r.status===404){say('失敗('+r.status+')：Token 無效或沒有 Actions 寫入權限','#e5654f')}
   else{say('失敗('+r.status+')','#e5654f')}}).catch(function(){say('網路錯誤','#e5654f')})};
};
})();
