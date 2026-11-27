// Isolated browser regression test for this local preview; never attaches to user Chrome.
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import os from 'node:os';
const base=process.argv[2]||'http://192.168.7.187:8786/';
const dir=await fs.mkdtemp(os.tmpdir()+'/guard-mold-v2-ui-');
const browser=spawn('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',['--headless','--no-first-run','--no-default-browser-check','--remote-debugging-port=9397',`--user-data-dir=${dir}`,'--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-background-timer-throttling','--disable-renderer-backgrounding','--disable-backgrounding-occluded-windows','--window-size=1600,1100','about:blank'],{stdio:'ignore'});
let ws;const checks=[];const errors=[];
const delay=ms=>new Promise(r=>setTimeout(r,ms));
const check=(ok,label)=>{if(!ok)throw Error(label);checks.push(label);};
try{
 let targets;
 for(let i=0;i<100;i++){try{targets=await (await fetch('http://127.0.0.1:9397/json')).json();break;}catch{await delay(100);}}
 if(!targets)throw Error('Chrome debug endpoint unavailable');
 ws=new WebSocket(targets.find(x=>x.type==='page').webSocketDebuggerUrl);await new Promise(r=>ws.addEventListener('open',r,{once:true}));
 let n=0;const pending=new Map();
 ws.addEventListener('message',e=>{const d=JSON.parse(e.data);if(d.id){const p=pending.get(d.id);pending.delete(d.id);d.error?p.reject(Error(JSON.stringify(d.error))):p.resolve(d.result);}if(d.method==='Runtime.exceptionThrown')errors.push(d.params.exceptionDetails.text+' '+d.params.exceptionDetails.exception?.description);});
 const send=(method,params={})=>new Promise((resolve,reject)=>{const id=++n;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));});
 const evaluate=async expression=>{const r=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
 await send('Runtime.enable');await send('Page.enable');await send('Page.navigate',{url:base});
 await evaluate(`new Promise((resolve,reject)=>{let n=0;const t=setInterval(()=>{if(document.body?.dataset.ready==='true'){clearInterval(t);resolve(true);}else if(n++>200){clearInterval(t);reject(Error(document.querySelector('#status')?.textContent||'timeout'));}},50);})`);
 check(await evaluate('document.querySelectorAll("select").length===0'),'flat controls; no dropdowns');
 check(await evaluate('moldSnapshot().instances.length===8'),'six mold solids, one pull pin and one casting reference');
 check(await evaluate('document.querySelectorAll("#stage button").length===9'),'nine ordered locator and mold stages');
 const names=['closed','pin-lifted','pin-out','lid-off','lower-out','back-out','shells-off','upper-lowered','released'];
 for(let i=0;i<names.length;i++){
   await evaluate(`document.querySelectorAll('#stage button')[${i}].click()`);
   const s=await evaluate('moldSnapshot()');
   check(s.instances.find(x=>x.id==='product-instance').world.every(x=>Math.abs(x)<1e-6),names[i]+': casting stays fixed');
 }
 let s=await evaluate('moldSnapshot()');
 check(JSON.stringify(s.instances.find(x=>x.id==='upper-instance').world)==='[120,0,-1]','upper core lowers before +X extraction');
 await evaluate(`document.querySelectorAll('#mold-modes button')[3].click()`);
 check(await evaluate(`moldSnapshot().instances.filter(x=>x.visible).every(x=>x.id==='product-instance')`),'casting-only visibility');
 await evaluate(`document.querySelectorAll('#mold-modes button')[2].click()`);
 check(await evaluate('moldSnapshot().instances.filter(x=>x.visible).length===3'),'three core inserts can be isolated');
 await evaluate(`document.querySelectorAll('#mold-modes button')[0].click();document.querySelector('#reset').click()`);
 check(await evaluate(`moldSnapshot().instances.find(x=>x.id==='left-instance').opacity===.12`),'transparent shells preserve opaque internal cores');
 await evaluate(`document.querySelector('#explode').value=50;document.querySelector('#explode').dispatchEvent(new Event('input',{bubbles:true}))`);
 check(await evaluate('moldSnapshot().motion.lower===160 && moldSnapshot().motion.back===0 && moldSnapshot().motion.left===0'),'slider follows ordered core-first sequence');
 await evaluate(`document.querySelector('#reset').click();document.querySelector('#play').click()`);
 for(let i=0;i<30;i++){if(await evaluate("moldSnapshot().playing && moldSnapshot().motion['pin-lift']>0"))break;await delay(200);}
 check(await evaluate("moldSnapshot().playing && moldSnapshot().motion['pin-lift']>0"),'animated extraction updates real frame positions');
 await evaluate(`document.querySelector('#play').click();document.querySelector('#reset').click()`);
 await delay(150);
 const screenshot=async name=>{const x=await send('Page.captureScreenshot',{format:'png'});await fs.writeFile(new URL(name,import.meta.url),Buffer.from(x.data,'base64'));};
 await evaluate(`document.querySelector('#band-controls button').click()`);
 check(await evaluate('moldSnapshot().bandsVisible'),'band paths shown only on assembled mold');
 await screenshot('preview-closed.png');
 await evaluate(`document.querySelectorAll('#stage button')[1].click()`);
 check(await evaluate('!moldSnapshot().bandsVisible'),'band paths removed before demolding');
 await evaluate(`document.querySelectorAll('#stage button')[2].click()`);
 const pin=await evaluate(`moldSnapshot().instances.find(x=>x.id==='pin-instance').world`);
 check(JSON.stringify(pin)==='[40,0,30]','pull pin clears bore before moving aside');

 await evaluate(`document.querySelectorAll('#stage button')[6].click();document.querySelectorAll('#mold-modes button')[1].click()`);await delay(150);
 await screenshot('preview-separated.png');
 await evaluate(`document.querySelectorAll('#views button')[2].click()`);
 check(await evaluate('moldSnapshot().motion.back===6 && !moldSnapshot().bandsVisible'),'pink locator inspection exposes actual guide pair');
 await screenshot('preview-pink-location.png');
 check(errors.length===0,'no browser runtime exceptions');
 const report={base,checks,errors};await fs.writeFile(new URL('ui-validation.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));
}finally{ws?.close();browser.kill('SIGTERM');}
