import { installAssemblyInteraction } from './assembly-interaction.mjs';
import { AssemblyScene } from './assembly-scene.mjs';
import { installFloatingPanels } from './floating-panels.mjs';
const $=s=>document.querySelector(s);
function button(label,fn,parent){const b=document.createElement('button');b.type='button';b.textContent=label;b.onclick=fn;parent.append(b);return b;}
async function main(){
 const response=await fetch('./manifest.json',{cache:'no-store'});if(!response.ok)throw Error('清单读取失败');
 const manifest=await response.json();
 installFloatingPanels($('#canvas-panel'),{persist:true});
 const runtime=new AssemblyScene($('#viewport'),manifest);await runtime.load();
 $('#title').textContent=manifest.title;
 $('#filters').hidden=true;$('#group-actions').hidden=true;
 const stages=manifest.stages,stageButtons=new Map();let direction=manifest.views[0].direction;
 const focus=(ids,dir=direction)=>{direction=dir;runtime.focus(ids,dir);};
 const interaction=installAssemblyInteraction({runtime,manifest,focus});
 let progress=0;
 function markStage(id){for(const [key,b] of stageButtons){b.classList.toggle('active',key===id);b.setAttribute('aria-pressed',String(key===id));}}
 function setProgress(value){
   runtime.pause();runtime.playInitialized=false;progress=value;
   const n=value*(stages.length-1),i=Math.min(stages.length-2,Math.floor(n)),t=n-i;
   runtime.applyMotionValues(Object.fromEntries(Object.keys(stages[i].values).map(k=>[k,stages[i].values[k]*(1-t)+stages[i+1].values[k]*t])));
   $('#explode').value=String(value*100);$('#explode-value').textContent=`${Math.round(value*100)}%`;
   markStage(stages[Math.round(n)].id);interaction.refresh();
 }
 for(const [i,s] of stages.entries())stageButtons.set(s.id,button(s.label,()=>{setProgress(i/(stages.length-1));focus(null);},$('#stage')));
 $('#explode').oninput=e=>setProgress(Number(e.target.value)/100);
 $('#play').onclick=()=>{if(runtime.playing)runtime.pause();else {runtime.play();focus(null);} };
 $('#reset').onclick=()=>{setProgress(0);focus(null);};
 runtime.onPlaybackUpdate=(id,playing)=>{$('#play').textContent=playing?'Ⅱ 暂停':'▶ 拆模演示';if(id){markStage(id);if(!playing){const i=stages.findIndex(s=>s.id===id);$('#explode').value=String(100*i/(stages.length-1));$('#explode-value').textContent=Math.round(100*i/(stages.length-1))+'%';}}};
 const modeButtons=new Map();
 function mode(name){
   for(const [id,r] of runtime.instances){runtime.setVisible(id,true);runtime.setOpacity(id,1);}
   if(name==='透视外模'){for(const id of ['left-instance','right-instance'])runtime.setOpacity(id,.12);runtime.setOpacity('lid-instance',.28);}
   if(name==='只看成品'){for(const id of runtime.instances.keys())runtime.setVisible(id,id==='product-instance');}
   if(name==='只看芯块'){for(const id of ['left-instance','right-instance','lid-instance','product-instance'])runtime.setVisible(id,false);}
   for(const [key,b] of modeButtons){b.classList.toggle('active',key===name);b.setAttribute('aria-pressed',String(key===name));}
   interaction.refresh();focus(null);
 }
 for(const [name,label] of [['透视外模','◉ 透视外模'],['实体合模','▣ 实体'],['只看芯块','◇ 芯块'],['只看成品','⬡ 成品']])modeButtons.set(name,button(label,()=>mode(name),$('#mold-modes')));
 $('#global-opacity').oninput=e=>{runtime.setGlobalOpacity(Number(e.target.value)/100);$('#global-opacity-value').textContent=e.target.value+'%';};
 for(const [label,dir] of [['+X',[1,0,0]],['−X',[-1,0,0]],['+Y',[0,1,0]],['−Y',[0,-1,0]],['+Z',[0,0,1]],['−Z',[0,0,-1]]])button(label,()=>{direction=dir;runtime.orientToAxis(dir);},$('#axis-views'));
 for(const v of manifest.views)button(v.label,()=>focus(v.focusInstanceIds,v.direction),$('#views'));
 mode('透视外模');markStage(stages[0].id);
 $('#status').textContent='六块模具 · 84 × 102 × 76.5 mm · 成品保持 v1.19';
 const resize=()=>runtime.resize($('#canvas-panel').clientWidth,$('#canvas-panel').clientHeight);new ResizeObserver(resize).observe($('#canvas-panel'));resize();
 let last=performance.now();
 const tick=now=>{interaction.update(now);runtime.tick((now-last)/1000);last=now;
   if(runtime.playing){const n=runtime.playIndex+runtime.playElapsed/manifest.playback.secondsPerTransition;$('#explode').value=String(100*n/(stages.length-1));$('#explode-value').textContent=Math.round(100*n/(stages.length-1))+'%';}
   requestAnimationFrame(tick);
 };requestAnimationFrame(tick);
 // Read-only diagnostics for verifying loaded assets and stage positions.
 window.moldSnapshot=()=>({title:manifest.title,instances:[...runtime.instances].map(([id,r])=>({id,visible:r.visible,opacity:r.opacity,world:r.mesh.getWorldPosition(r.mesh.position.clone()).toArray()})),motion:{...runtime.motionValues},playing:runtime.playing});
 if(new URLSearchParams(location.search).has('stage')){const i=stages.findIndex(s=>s.id===new URLSearchParams(location.search).get('stage'));if(i>=0){setProgress(i/(stages.length-1));focus(null);}}
 document.body.dataset.ready='true';
}
main().catch(e=>{$('#status').textContent='加载失败：'+e.message;console.error(e);});
