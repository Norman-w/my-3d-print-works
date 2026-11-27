import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {radii,partTranslation,springPose,cyclePose} from './feeder-motion-kinematics.mjs';
import {createOverview} from './feeder-overview.mjs';
import {createTriggerOverlay} from './trigger-overlay.mjs';
import {createAssetStore} from './scene-assets.mjs';
import {displayContract,defaultPartVisible,partIsVisible,recordMaterialDisplay} from './scene-display.mjs';
import {cableContracts,validateCableCatalogue,triggerPose,rigidPose,springOffset,
  inputCorePoints,outputCorePoints,coreDiameter,isCableAccessory,localInputToCad,activeDuringTrigger} from './cable-scene-kinematics.mjs';

const $=id=>document.getElementById(id),canvas=$('scene');
const query=new URLSearchParams(location.search).get('view');
const legacy={inside:'feeder',drive:'feeder',whole:'feeder',lube:'feeder'};
const initialView=['system','feeder','trigger','spin','side','outlet'].includes(query)?query:legacy[query]||'system';
const layerNames=['feeder','spin','hopper','hose','blower','pipes','trigger','hand','balls','labels','lube','hold'];
const state={p:0,partialReturn:false,playing:false,playTarget:1,playRate:1/18,ready:false,view:initialView,surface:query==='inside'?'cutaway':'transparent',layers:Object.fromEntries(layerNames.map(k=>[k,!['hold','lube'].includes(k)])),catalogue:[],partVisible:new Map(),previousTime:0,cableCandidate:false,snapshotKnown:false,contracts:null};
if(query==='lube')state.layers.lube=true;
$('view').value=state.view;$('surface').value=state.surface;
for(const k of layerNames)$(`layer-${k}`).checked=state.layers[k];
const renderer=new THREE.WebGLRenderer({canvas,antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio||1,2));renderer.setClearColor(0x121e26);renderer.localClippingEnabled=true;renderer.outputColorSpace=THREE.SRGBColorSpace;
const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera(38,1,.1,5000);
const controls=new OrbitControls(camera,canvas);controls.enableDamping=true;controls.minDistance=70;controls.maxDistance=3500;
scene.add(new THREE.HemisphereLight(0xd8edff,0x344856,2.6));
for(const [p,intensity] of [[[100,250,450],3],[[-350,20,-250],2],[[-100,-380,150],2]]){const l=new THREE.DirectionalLight(0xffffff,intensity);l.position.set(...p);scene.add(l);}
const material=(color,extra={})=>new THREE.MeshStandardMaterial({color,roughness:.55,metalness:.08,...extra});
const basis=new THREE.Matrix4().set(0,0,1,0,1,0,0,0,0,1,0,0,0,0,0,1);
const feeder=new THREE.Group(),feederMount=new THREE.Group();feeder.quaternion.setFromRotationMatrix(basis);feederMount.add(feeder);feederMount.rotation.z=Math.PI/4;feederMount.position.set(-155,-155,0);scene.add(feederMount);
const spin=new THREE.Group();spin.quaternion.setFromRotationMatrix(basis);spin.position.set(380,0,0);scene.add(spin);
const hold=new THREE.Group();hold.quaternion.copy(spin.quaternion);hold.position.set(380,-125,0);scene.add(hold);
scene.updateMatrixWorld(true);
const feederWorld=(x,y,z)=>feeder.localToWorld(new THREE.Vector3(x,y,z));
const feedDirection=new THREE.Vector3(Math.SQRT1_2,Math.SQRT1_2,0);
const movingPoint=u=>feederWorld(-68,24,13+u);
const overview=createOverview(material);scene.add(overview.group);
const overlay=createTriggerOverlay(material,{feederMovingPoint:movingPoint,feederFixedPoint:movingPoint(0).addScaledVector(feedDirection,60)});scene.add(overlay.group);
const clip=new THREE.Plane(new THREE.Vector3(0,0,-1),0);
const labels=[];
function label(text,point,visible,klass='tag'){
  const node=document.createElement('span');node.className=klass;node.textContent=text;$('tags').append(node);
  labels.push({text,node,point,visible});
}
for(const l of overview.labels)label(l.text,()=>l.point.clone(),()=>state.layers[l.layer]&&['system','side'].includes(state.view));
for(const l of overlay.labels)label(l.text,l.point,()=>state.snapshotKnown&&!state.cableCandidate&&state.layers.trigger&&['system','trigger'].includes(state.view));
label('送料总成 · 原装配',()=>feederWorld(-95,40,0),()=>state.layers.feeder&&['system','side'].includes(state.view));
label('旋转头 · 原装配',()=>new THREE.Vector3(416,117,0),()=>state.layers.spin&&['system','side','spin'].includes(state.view));
label('保持叉 · 旁置参考',()=>new THREE.Vector3(425,-143,0),()=>state.layers.hold);
const localLabel=(text,fn)=>label(text,()=>feeder.localToWorld(fn()),()=>state.layers.feeder&&state.view==='feeder');
localLabel('前挡',()=>new THREE.Vector3(radii(cyclePose(state.p).u).front+20,28,0));
localLabel('后挡',()=>new THREE.Vector3(radii(cyclePose(state.p).u).rear+20,28,-28.5));
localLabel('送料滑架',()=>new THREE.Vector3(76,-8,23+cyclePose(state.p).u));
localLabel('回位弹簧',()=>new THREE.Vector3(-80,38,5+cyclePose(state.p).u/2));
label('摩擦垫 / 浮动载体',()=>spin.localToWorld(new THREE.Vector3(29,0,43)),()=>state.layers.spin&&state.view==='spin');
label('压缩弹簧与拉帽',()=>spin.localToWorld(new THREE.Vector3(88,0,43)),()=>state.layers.spin&&state.view==='spin');

const lube=new THREE.Group();feeder.add(lube);
const lubePoints=[
 {text:'1 导轨',at:()=>new THREE.Vector3(56,24,-14),tag:new THREE.Vector3(96,43,-69)},
 {text:'2 挡指滑块',at:()=>new THREE.Vector3(-(radii(cyclePose(state.p).u).front+20),0,0),tag:new THREE.Vector3(-100,40,-35)},
 {text:'3 肩销 / 槽壁',at:()=>new THREE.Vector3(radii(cyclePose(state.p).u).front+20,13,0),tag:new THREE.Vector3(90,42,65)}
];
for(const item of lubePoints){
 item.dot=new THREE.Mesh(new THREE.SphereGeometry(3,16,12),new THREE.MeshBasicMaterial({color:0xf7dd88,depthTest:false}));
 item.line=new THREE.Line(new THREE.BufferGeometry().setFromPoints([item.at(),item.tag]),new THREE.LineBasicMaterial({color:0xf7dd88,depthTest:false}));
 item.dot.renderOrder=item.line.renderOrder=8;lube.add(item.dot,item.line);
 label(item.text,()=>feeder.localToWorld(item.tag.clone()),()=>state.layers.lube&&state.layers.feeder,'tag lube-tag');
}
const balls=new THREE.Group();scene.add(balls);
const ballGeometry=new THREE.SphereGeometry(20.5,32,20),ballMeshes=[];
for(let i=0;i<3;i++){
 const ball=new THREE.Mesh(ballGeometry,material(i===0?0xf5eee0:0xd4e7ec));balls.add(ball);ballMeshes.push(ball);
 label(String(i+1),()=>ball.position.clone(),()=>state.layers.balls&&['feeder','spin'].includes(state.view),'tag ball-id');
}
function alongPolyline(points,t){
 const lengths=points.slice(1).map((p,i)=>p.distanceTo(points[i]));let travel=lengths.reduce((a,b)=>a+b,0)*Math.max(0,Math.min(1,t));
 for(let i=0;i<lengths.length;i++){if(travel<=lengths[i])return points[i].clone().lerp(points[i+1],travel/lengths[i]);travel-=lengths[i];}
 return points.at(-1).clone();
}
const ballPath=[feederWorld(0,0,cyclePose(0).balls[0]),feederWorld(0,0,135),new THREE.Vector3(0,0,0),new THREE.Vector3(535,0,0)];
const catalogueNodes=new Map();
function rowColor(row){
 const display=displayContract(row);if(display)return display.color;
 const id=row.id;
 if(row.motion?.kind==='input-wire'||row.motion?.kind==='output-wire'||id.includes('core'))return 0xd6b7ff;
 if(id.includes('housing'))return 0x65768f;
 if(['feeder/cable-input-lever','feeder/cable-input-terminal-cap'].includes(id))return 0x58c5ee;
 if(id.startsWith('feeder/cable-route-'))return 0x6faebd;
 if(id.includes('hardware'))return 0xc5d0d7;
 if(id.includes('spring')||id==='spin/pad')return 0x73d7a5;
 if(id==='feeder/frame'||id==='spin/carriage'||id==='spin/pull-cap')return 0xf4c05c;
 if(id.includes('finger-')||id.includes('pin-block-'))return id.endsWith('rear')?0x58c5ee:0xef9270;
 return row.color||0x91a9b7;
}
const store=createAssetStore({
 material:row=>material(rowColor(row),{side:THREE.DoubleSide,metalness:row.id.includes('hardware')?.65:.08}),
 attach:record=>{const g=record.row.id.startsWith('feeder/')?feeder:record.row.group==='hold'?hold:spin;g.add(record.group);},
 onChange:record=>{applyRecord(record);updatePose();updateCatalogue();}
});
function isShell(id){return /^(feeder\/(positive-half|negative-half|liner|pc-reference|capture-.+|pipe-clamp-.+|cable-input-body|cable-input-cover|cable-input-terminal-cap|cable-output-cap|cable-route-cap)|spin\/(body|cover|spring-cage))$/.test(id);}
function applyRecord(record){
 const {row,group,meshes}=record;group.visible=partIsVisible(row,state.partVisible)&&(!state.cableCandidate||!isCableAccessory(row)||state.layers.trigger);
 for(const mesh of meshes){
  const shell=isShell(row.id)||state.cableCandidate&&row.id.includes('housing');
  Object.assign(mesh.material,recordMaterialDisplay(row,{surface:state.surface,shell,clip}));mesh.material.needsUpdate=true;
 }
}
function applyVisibility(){
 feederMount.visible=state.layers.feeder;spin.visible=state.layers.spin;hold.visible=state.layers.hold;
 for(const [name,group] of Object.entries(overview.layers))group.visible=state.layers[name];
 overlay.group.visible=state.snapshotKnown&&!state.cableCandidate&&state.layers.trigger;overlay.handGroup.visible=!state.cableCandidate&&state.layers.hand;
 balls.visible=state.layers.balls;lube.visible=state.layers.lube;
 for(const r of store.loaded.values())applyRecord(r);
 updateCatalogue();updateEvidence();
}
function coreGeometry(points,diameter){
 const curve=new THREE.CurvePath();
 for(let i=1;i<points.length;i++)curve.add(new THREE.LineCurve3(new THREE.Vector3(...points[i-1]),new THREE.Vector3(...points[i])));
 return new THREE.TubeGeometry(curve,Math.max(8,points.length*2),diameter/2,10,false);
}
function applyCableMotion(mesh,u){
 const motion=mesh.userData.motion,pose=rigidPose(motion,u,state.contracts);
 mesh.position.set(...pose.position);mesh.quaternion.identity();
 if(pose.origin){
  const origin=new THREE.Vector3(...pose.origin);
  mesh.quaternion.setFromAxisAngle(new THREE.Vector3(...pose.axis).normalize(),pose.angle);
  mesh.position.copy(origin).sub(origin.clone().applyQuaternion(mesh.quaternion));
 }
 if(!activeDuringTrigger(motion))return;
 if(mesh.userData.lastDeformU===u)return;
 if(motion.kind==='spring'){
  const a=mesh.geometry.attributes.position,base=mesh.userData.restPositions;
  for(let i=0;i<a.count;i++)a.setZ(i,base[i*3+2]+springOffset(base[i*3+2],u,motion,state.contracts));
  a.needsUpdate=true;mesh.geometry.computeVertexNormals();mesh.geometry.computeBoundingBox();mesh.geometry.computeBoundingSphere();
 }else if(motion.kind==='input-wire'||motion.kind==='output-wire'){
  const points=motion.kind==='input-wire'?inputCorePoints(u,motion,state.contracts):outputCorePoints(u,motion,state.contracts);
  mesh.geometry.dispose();mesh.geometry=coreGeometry(points,coreDiameter(motion.kind,state.contracts));
  mesh.userData.displayReference='Source-contract steel core path; no force or cable deformation simulation';
  mesh.userData.coreEndpoints=[points[0],points.at(-1)];
 }
 mesh.userData.lastDeformU=u;
}
function updatePose(){
 const pose=cyclePose(state.p),u=pose.u;
 for(const record of store.loaded.values()){
  if(!record.row.id.startsWith('feeder/'))continue;
  if(state.cableCandidate){for(const mesh of record.meshes)applyCableMotion(mesh,u);continue;}
  for(const mesh of record.meshes)mesh.position.set(...partTranslation(mesh.userData.motionGroup,u));
  if(record.springBase&&record.lastSpringU!==u){
   const mesh=record.meshes[0],a=mesh.geometry.attributes.position,base=record.springBase,s=springPose(0);
   for(let i=0;i<a.count;i++){const z=base[i*3+2],f=Math.max(0,Math.min(1,(z-s.coilStartZ)/(s.coilEndZ-s.coilStartZ)));a.setZ(i,z+f*u);}
   a.needsUpdate=true;mesh.geometry.computeVertexNormals();mesh.geometry.computeBoundingSphere();record.lastSpringU=u;
  }
 }
 const p=state.cableCandidate?triggerPose(u,state.contracts):overlay.update(u,{returning:state.p>.65&&state.p<.85,released:state.p>=.85});
 const ballPositions=state.partialReturn?cyclePose(0).balls:pose.balls;
 ballMeshes.forEach((b,i)=>b.position.copy(i===0&&state.p>=.5&&!state.partialReturn?alongPolyline(ballPath,(state.p-.5)/.15):feederWorld(0,0,ballPositions[i])));
 for(const item of lubePoints){const at=item.at();item.dot.position.copy(at);item.line.geometry.attributes.position.setXYZ(0,at.x,at.y,at.z);item.line.geometry.attributes.position.needsUpdate=true;item.line.geometry.computeBoundingSphere();}
 $('progress').value=(state.p*100).toFixed(1);$('stroke').value=state.snapshotKnown?`近端扣入 ${p.rearward.toFixed(2)} / ${(p.fullRearward??12).toFixed(2)} mm`:'等待装配数据';
 $('phase').textContent=state.p===0?'远端待发：首球在前挡':state.p<.18?'近端勾扣：后挡关闭':state.p<.3?'继续扣动：两挡同时关闭':state.p<.5?'扣到近端：前挡打开':state.p<=.65?'扣住保持：一颗球经三通送出':state.p<.85?'松手释放：远端回位、两挡复位':'远端已释放：下一颗补入';
 if(state.partialReturn)$('phase').textContent=state.p<.85?'中途松手：回位，本次未出球':'回位完成：首球仍在待发位';
 $('detail').textContent=state.cableCandidate
  ?`向虎口扣入 ${p.rearward.toFixed(2)} mm，扳机转过 ${Math.abs(p.angleDegrees).toFixed(2)}°，通过固定导向拉动送料滑架 ${u.toFixed(1)} mm。固定护套座不动；松手由回位弹簧带回。球路和线芯形状是动作参考，未模拟摩擦、载荷或气流。`
  :`手指向虎口扣入 ${p.rearward.toFixed(1)} mm，传动带原凸轮架前进 ${u.toFixed(1)} mm。原挡指、肩销、端部五金与弹簧同步运动；球速和新增拉索安装关系为示意。`;
 $('pull-trigger').disabled=!state.ready||(state.p>0&&state.p<1);$('release-trigger').disabled=!state.ready||u===0;
 canvas.dataset.progress=state.p.toFixed(5);canvas.dataset.stroke=u.toFixed(5);canvas.dataset.triggerConcept=JSON.stringify(p);
 canvas.dataset.ballCenters=JSON.stringify(ballMeshes.map(b=>b.position.toArray()));
 canvas.dataset.motionOffsets=JSON.stringify([...store.loaded.values()].filter(r=>r.row.id.startsWith('feeder/')).flatMap(r=>r.meshes.map(m=>[r.row.id,m.userData.motionGroup,...m.position.toArray()])));
 canvas.dataset.motionTransforms=JSON.stringify([...store.loaded.values()].filter(r=>r.row.id.startsWith('feeder/')).flatMap(r=>r.meshes.map(m=>({id:r.row.id,kind:m.userData.motion?.kind||'legacy',position:m.position.toArray(),quaternion:m.quaternion.toArray(),coreEndpoints:m.userData.coreEndpoints}))));
}
function updateEvidence(){
 canvas.dataset.view=state.view;canvas.dataset.sceneIdentity=scene.uuid;
 canvas.dataset.loadedParts=String(store.loaded.size);
 canvas.dataset.partInstances=JSON.stringify([...store.loaded.values()].map(r=>[r.row.id,r.instanceId]));
 canvas.dataset.layers=JSON.stringify(state.layers);
 canvas.dataset.visibleParts=JSON.stringify([...store.loaded.values()].filter(r=>r.group.visible&&(r.row.id.startsWith('feeder/')?state.layers.feeder:r.row.group==='hold'?state.layers.hold:state.layers.spin)).map(r=>r.row.id));
 canvas.dataset.surface=state.surface;
 canvas.dataset.legacyTriggerOverlay=String(overlay.group.visible);
 canvas.dataset.motionMode=state.cableCandidate?'source-cable-contract':'legacy-baseline';
}
function updateCatalogue(){
 $('load-status').textContent=`详细模型 ${store.loaded.size} / ${state.catalogue.length||48} 已加载`;
 $('catalogue-count').textContent=`（${store.loaded.size} / ${state.catalogue.length||48} 已加载）`;
 for(const row of state.catalogue){const node=catalogueNodes.get(row.id);if(!node)continue;node.input.checked=partIsVisible(row,state.partVisible);node.status.textContent=(store.loaded.has(row.id)?'已加载':'按需加载')+(row.display?.kind==='space-requirement'?' · 空间要求':'');}
 updateEvidence();
}
function buildCatalogue(){
 for(const row of state.catalogue){
  const node=document.createElement('label');node.className='part-row';const input=document.createElement('input');input.type='checkbox';input.checked=partIsVisible(row,state.partVisible);input.setAttribute('aria-label',row.name);
  if(row.display?.kind==='space-requirement')node.title='橙色透明区域为空间要求，不是E卡簧实体，也不代表工具已适配。';
  const name=document.createElement('span');name.textContent=row.name;const status=document.createElement('small');node.append(input,name,status);$('part-list').append(node);catalogueNodes.set(row.id,{node,input,status});
  input.addEventListener('change',async()=>{
   state.partVisible.set(row.id,input.checked);
   if(input.checked){const layer=row.id.startsWith('feeder/')?'feeder':row.group==='hold'?'hold':'spin';state.layers[layer]=true;$(`layer-${layer}`).checked=true;if(state.cableCandidate&&isCableAccessory(row)){state.layers.trigger=true;$('layer-trigger').checked=true;}await safely(()=>store.ensure(row));}
   applyVisibility();
  });
 }
}
function resetCamera(){
 const aspect=canvas.clientWidth/Math.max(1,canvas.clientHeight);camera.up.set(0,1,0);
 const presets={
  system:{target:[-18,-45,30],offset:[90,90,1150],aspect:1.65},
  side:{target:[-18,-45,30],offset:[0,0,1150],aspect:1.65},
  feeder:{target:[-160,-170,20],offset:[135,80,510],aspect:1.15},
  trigger:{target:[-140,-132,92],offset:[60,15,575],aspect:1.15},
  spin:{target:[409,25,0],offset:[80,45,230],aspect:1.05},
  outlet:{target:[380,0,0],offset:[350,10,0],aspect:1.05}
 };
 if(state.cableCandidate&&state.contracts){
  presets.trigger={target:feederWorld(...state.contracts.ci.origin).toArray(),offset:[25,-15,450],aspect:1.15};
  presets.feeder={target:[-145,-125,-15],offset:[140,70,620],aspect:1.15};
 }
 const p=presets[state.view];controls.target.set(...p.target);camera.position.copy(controls.target).add(new THREE.Vector3(...p.offset).multiplyScalar(Math.max(1,p.aspect/aspect)));controls.update();updateEvidence();
}
function resize(){const w=canvas.clientWidth,h=canvas.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/Math.max(1,h);camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe(canvas);resize();resetCamera();
function stop(){state.playing=false;$('play').textContent='播放一轮';}
function playTo(target,rate){state.playTarget=target;state.playRate=rate;state.playing=true;$('play').textContent='暂停';}
$('play').addEventListener('click',()=>{if(state.playing){stop();return;}if(state.p>=1){state.p=0;state.partialReturn=false;}playTo(1,1/18);});
$('pull-trigger').addEventListener('click',()=>{if(state.p>.65)state.p=0;state.partialReturn=false;playTo(.65,.25);});
$('release-trigger').addEventListener('click',()=>{if(state.p<=.65)state.partialReturn=state.p<.5;state.p=.85-.2*cyclePose(state.p).u/20;playTo(1,.25);});
$('next').addEventListener('click',()=>{stop();state.p=[0,.18,.30,.50,.65,.85,1].find(p=>p>state.p+.002)??0;if(state.p===0)state.partialReturn=false;updatePose();});
$('reset').addEventListener('click',()=>{stop();state.p=0;state.partialReturn=false;updatePose();});
$('progress').addEventListener('input',e=>{stop();state.partialReturn=false;state.p=Number(e.target.value)/100;updatePose();});
// A camera choice changes only the camera. No geometry, visibility or cycle reset.
$('view').addEventListener('change',e=>{state.view=e.target.value;resetCamera();});
$('camera').addEventListener('click',resetCamera);
$('surface').addEventListener('change',e=>{state.surface=e.target.value;applyVisibility();});
$('part-search').addEventListener('input',e=>{const q=e.target.value.trim().toLowerCase();for(const row of state.catalogue)catalogueNodes.get(row.id).node.hidden=!(row.name+' '+row.id).toLowerCase().includes(q);});
async function safely(action){try{$('error').hidden=true;await action();}catch(e){$('error').hidden=false;$('error').textContent=`模型加载失败：${e.message}。可重新勾选重试。`;}}
for(const k of layerNames)$(`layer-${k}`).addEventListener('change',async e=>{
 state.layers[k]=e.target.checked;applyVisibility();
 if(state.cableCandidate&&k==='trigger'&&e.target.checked){state.layers.feeder=true;$('layer-feeder').checked=true;await safely(()=>store.ensureMany(state.catalogue.filter(isCableAccessory)));}
 if(e.target.checked&&['feeder','spin','hold'].includes(k))await safely(()=>store.ensureMany(state.catalogue.filter(r=>k==='feeder'?r.id.startsWith('feeder/'):r.group===k)));
 applyVisibility();
});
$('show-all').addEventListener('click',async()=>{
 $('show-all').disabled=true;
 for(const k of layerNames){if(k!=='lube')state.layers[k]=!(state.cableCandidate&&k==='hand');$(`layer-${k}`).checked=state.layers[k];}
 for(const row of state.catalogue)state.partVisible.set(row.id,true);
 await safely(()=>store.ensureMany(state.catalogue));applyVisibility();$('show-all').disabled=false;
});
function projectLabels(){
 scene.updateMatrixWorld();const w=canvas.clientWidth,h=canvas.clientHeight;
 for(const row of labels){
  const v=row.point().project(camera),hidden=!state.layers.labels||!row.visible()||v.z>1||v.z<-1||Math.abs(v.x)>1||Math.abs(v.y)>1;
  row.node.classList.toggle('hidden',hidden);if(hidden)continue;
  const half=row.node.offsetWidth/2+4;row.node.style.left=`${Math.max(half,Math.min(w-half,(v.x*.5+.5)*w))}px`;row.node.style.top=`${(-v.y*.5+.5)*h}px`;
 }
}
function animate(time){
 const dt=Math.min(.06,Math.max(0,(time-state.previousTime)/1000));state.previousTime=time;
 if(state.playing&&state.ready){state.p=Math.min(state.playTarget,state.p+dt*state.playRate);updatePose();if(state.p===state.playTarget)stop();}
 controls.update();projectLabels();renderer.render(scene,camera);requestAnimationFrame(animate);
}
applyVisibility();updatePose();requestAnimationFrame(animate);
async function init(){
 const response=await fetch('./motion-manifest.json',{cache:'no-store'});if(!response.ok)throw new Error(`模型目录 HTTP ${response.status}`);
 const manifest=await response.json();state.catalogue=manifest.assembly_catalog;
 for(const row of state.catalogue)displayContract(row);
 const currentCable=manifest.snapshot==='current-cable-candidate';
 if(currentCable){
  const contracts=cableContracts(manifest.scene_contract);validateCableCatalogue(state.catalogue,contracts);
  state.contracts=contracts;state.cableCandidate=true;state.snapshotKnown=true;
  state.layers.hand=false;$('layer-hand').checked=false;$('layer-hand').disabled=true;
  $('hand-label').textContent='手部 · 未建模';$('layer-hand').title='当前没有手部尺寸模型';
  $('trigger-label').textContent='拉索附件与护套';
  $('model-note').textContent='历史拉索方案：这里的扳机、钢芯和护套均已退出当前往复电机方案；本场景仅用于查阅原拉索机构，不是当前装配。';
  label('固定护套座 · 输入',()=>feederWorld(...localInputToCad(state.contracts.ci.adjuster_seat_local,state.contracts.ci)),()=>state.layers.feeder&&state.layers.trigger&&['system','trigger'].includes(state.view));
  label('向虎口勾扣',()=>feederWorld(...triggerPose(cyclePose(state.p).u,state.contracts).fingerPoint),()=>state.layers.feeder&&state.layers.trigger&&['system','trigger'].includes(state.view));
  label('输出端 · 拉动20 mm',()=>{const a=state.contracts.co.moving_wire_axis_t0;return feederWorld(a[0],a[1],a[2]+cyclePose(state.p).u);},()=>state.layers.feeder&&state.layers.trigger&&['system','feeder','trigger'].includes(state.view));
  $('source-note').textContent=`${state.catalogue.length}项资源来自历史拉索导出清单；旋转、滑移与弹簧端点按当时CAD契约演示。钢芯仅作旧方案参考，不能进入当前往复电机版。保持叉旁置，不与工作档叠装。`;
 }else {$('source-note').textContent='当前是保留的旧版模型资源；五金按运动分组并保留原三角面。旧拉索叠加仅作历史示意。保持叉旁置，不与工作档叠装。';state.snapshotKnown=true;}
 canvas.dataset.snapshot=manifest.snapshot;applyVisibility();resetCamera();
 for(const row of state.catalogue)state.partVisible.set(row.id,defaultPartVisible(row));
 buildCatalogue();updateCatalogue();
 await store.ensureMany(state.catalogue.filter(r=>r.id.startsWith('feeder/')));
 state.ready=true;for(const id of ['play','next','reset','progress'])$(id).disabled=false;updatePose();
 await store.ensureMany(state.catalogue.filter(r=>r.group==='spin'));
 if(state.layers.hold)await store.ensureMany(state.catalogue.filter(r=>r.group==='hold'));
 $('loading').hidden=true;applyVisibility();canvas.dataset.snapshot=manifest.snapshot;
}
init().catch(e=>{stop();$('loading').hidden=true;$('error').hidden=false;$('error').textContent=`加载未完成：${e.message}`;});
