import * as THREE from 'three';
import {OrbitControls} from './assembly/vendor/OrbitControls.js';
import {STLLoader} from './assembly/vendor/STLLoader.js';
const host=document.querySelector('#view'), scene=new THREE.Scene();scene.background=new THREE.Color('#101923');
const camera=new THREE.PerspectiveCamera(38,innerWidth/innerHeight,.1,2000);camera.up.set(0,0,1);
const renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));host.append(renderer.domElement);
const controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,0,2);controls.enableDamping=true;
scene.add(new THREE.HemisphereLight(0xffffff,0x526579,2));const light=new THREE.DirectionalLight(0xffffff,2);light.position.set(60,-80,120);scene.add(light);
const axes=new THREE.AxesHelper(25);axes.position.set(-43,-48,-24);scene.add(axes);
for(const [name,p,c] of [['+X',[-14,-48,-24],'#ff6060'],['+Y',[-43,-19,-24],'#70ed80'],['+Z',[-43,-48,5],'#80aaff']]){const cv=document.createElement('canvas');cv.width=128;cv.height=64;let ctx=cv.getContext('2d');ctx.font='bold 38px sans-serif';ctx.fillStyle=c;ctx.fillText(name,8,45);let s=new THREE.Sprite(new THREE.SpriteMaterial({map:new THREE.CanvasTexture(cv),depthTest:false}));s.position.set(...p);s.scale.set(13,6.5,1);scene.add(s);}
const tubes=new THREE.Group();scene.add(tubes);
for(const [size,pos,color] of [[[112,20,20],[0,0,10],0x8995a3],[[20,110,20],[0,0,-10],0x267bcb]]){let m=new THREE.Mesh(new THREE.BoxGeometry(...size),new THREE.MeshStandardMaterial({color,transparent:true,opacity:.28,depthWrite:false}));m.position.set(...pos);tubes.add(m);}
let clip,seq=0;const loader=new STLLoader(),cache=new Map();
let torque=0,version='15';
const foot=tubes.children[1], loadArrows=new THREE.Group();scene.add(loadArrows);
const neutral=new THREE.Color('#224bc9');
function loadState(){
const span=version==='15'?23:28,a=10.5+span,h=22,t=7;
// Actual 20 mm foot against X=+-10.9 inner wall, ending at Y=+-a.
// At world Y=a, rotated foot edge is X=(10+a*sin(theta))/cos(theta).
let lo=0,hi=Math.PI/4;for(let i=0;i<60;i++){let m=(lo+hi)/2;if((10+a*Math.sin(m))/Math.cos(m)>10.9)hi=m;else lo=m;}
const limit=lo,requested=torque*Math.PI/180,theta=Math.sign(requested)*Math.min(Math.abs(requested),limit);
const overtravel=Math.max(0,Math.abs(torque)-limit*180/Math.PI);
// After rigid contact only the actuator indicator advances. Stiffness is
// a user-selected loading proxy, not a measured clip spring constant.
const mass=Number(document.querySelector('#mass').value),externalForce=mass*9.80665;
const appliedTorque=overtravel>0?externalForce*.2:0;
const F=appliedTorque*1000/(2*a),sigma=6*F*h/(span*t*t);
return {a,h,F,sigma,theta,limit,overtravel,appliedTorque,mass,externalForce};}
function applyLoad(){if(!clip)return;version=document.querySelector('#version').value;const s=loadState(),g=clip.geometry,p=g.attributes.position,c=g.attributes.color;
if(!g.userData.risk){const weights=new Float32Array(p.count);for(let i=0;i<p.count;i++){const x=Math.abs(p.getX(i)),y=Math.abs(p.getY(i)),z=p.getZ(i);weights[i]=Math.max(Math.exp(-((x-14.4)**2/25+(y-23)**2/110+z*z/55)),.85*Math.exp(-((x-14.4)**2/24+(y-33.5)**2/35+(z-.2)**2/25)),.65*Math.exp(-((x-18)**2/30+(y-17)**2/60+(z-5)**2/100)));}g.userData.risk=weights;}
const field=g.userData.risk;for(let i=0;i<p.count;i++){const x=p.getX(i),y=p.getY(i),onLoadedDiagonal=torque===0?0:(Math.sign(x*y)===-Math.sign(torque)?1:.2);const estimate=s.sigma*field[i]*onLoadedDiagonal;neutral.setHSL((1-Math.min(1,estimate/400))*.65,.88,.49);c.setXYZ(i,neutral.r,neutral.g,neutral.b);}c.needsUpdate=true;
foot.rotation.z=s.theta;
while(loadArrows.children.length){const old=loadArrows.children[0];loadArrows.remove(old);old.line.geometry.dispose();old.line.material.dispose();old.cone.geometry.dispose();old.cone.material.dispose();}
if(s.F>0)for(const side of [-1,1]){const direction=new THREE.Vector3(-Math.sign(torque)*side,0,0);loadArrows.add(new THREE.ArrowHelper(direction,new THREE.Vector3(-Math.sign(torque)*side*10.9,side*s.a,-10),Math.min(28,6+s.F*.25),0xffa63d,4,2));}
document.querySelector('#mass-value').value=s.mass.toFixed(1);document.querySelector('#torque-value').value=torque.toFixed(1);document.querySelector('#stress-readout').textContent=`${s.overtravel>0?'已碰壁：管子停止，载荷由止挡承受':'间隙内：未接触，卡子受力为零'}。外部切向力 ${s.externalForce.toFixed(1)} N，力臂 200 mm；承受扭矩 ${s.appliedTorque.toFixed(2)} N·m；碰壁角 ±${(s.limit*180/Math.PI).toFixed(3)}°；实际转角 ${(s.theta*180/Math.PI).toFixed(3)}°；等效对角反力 ${s.F.toFixed(1)} N / 端；名义弯曲应力 ${s.sigma.toFixed(2)} MPa（线弹性外推，不代表能承受此载荷）。`;
document.querySelector('#caption').textContent=`X 上梁 · Y 下脚 · Z 向上｜实际转角 ${(s.theta*180/Math.PI).toFixed(2)}°｜${s.overtravel>0?'接触受力':'自由间隙 / 零应力'}`;
}
document.querySelector('#torque').oninput=e=>{torque=Number(e.target.value);applyLoad();};
document.querySelector('#mass').oninput=()=>{torque=Number(document.querySelector('#mass').value)>0?Number(document.querySelector('#direction-load').value)*8:0;document.querySelector('#torque').value=torque;applyLoad();};
document.querySelector('#direction-load').onchange=()=>{torque=Math.abs(torque)*Number(document.querySelector('#direction-load').value);document.querySelector('#torque').value=torque;applyLoad();};
document.querySelector('#zero').onclick=()=>{torque=0;document.querySelector('#mass').value=0;document.querySelector('#torque').value=0;applyLoad();};
function colors(g){const p=g.attributes.position,c=new Float32Array(p.count*3),out=new THREE.Color();for(let i=0;i<p.count;i++){let x=Math.abs(p.getX(i)),y=Math.abs(p.getY(i)),z=p.getZ(i);let root=Math.exp(-((x-14.4)**2/25+(y-23)**2/110+z*z/55));let toe=.85*Math.exp(-((x-14.4)**2/24+(y-33.5)**2/35+(z-.2)**2/25));let rib=.65*Math.exp(-((x-18)**2/30+(y-17)**2/60+(z-5)**2/100));let hook=.45*Math.exp(-((x-10.7)**2/12+(y-26)**2/120+(z+22)**2/8));let v=Math.min(1,Math.max(root,toe,rib,hook));out.setHSL((1-v)*.65,.88,.49);out.toArray(c,i*3);}g.setAttribute('color',new THREE.BufferAttribute(c,3));}
async function load(v){let token=++seq;document.querySelector('#status').textContent='正在加载 v1.'+v+'…';try{let g=cache.get(v);if(!g){let path=v==='15'?'../print-packages/barrier-clip-v1.15-6x-black-PETG/guard-v1.15.stl':'../exports/perpendicular-u-joint-v1.16-root-radius/guard-v1.16.stl';g=await loader.loadAsync(path);g.computeVertexNormals();colors(g);cache.set(v,g);}if(token!==seq)return;if(clip){scene.remove(clip);clip.material.dispose();}clip=new THREE.Mesh(g,new THREE.MeshStandardMaterial({vertexColors:true,roughness:.62,metalness:.05}));scene.add(clip);update();document.querySelector('#status').textContent='v1.'+v+' 实际网格已加载 · '+g.attributes.position.count/3+' 个三角面';}catch(e){document.querySelector('#status').textContent='加载失败：'+e.message;}}
function update(){tubes.visible=document.querySelector('#tubes').checked;if(clip){clip.material.vertexColors=document.querySelector('#heat').checked;clip.material.color.set(clip.material.vertexColors?0xffffff:0x14a5b6);clip.material.transparent=document.querySelector('#transparent').checked;clip.material.opacity=clip.material.transparent?.55:1;clip.material.depthWrite=!clip.material.transparent;clip.material.needsUpdate=true;applyLoad();}}
for(const id of ['heat','tubes','transparent'])document.querySelector('#'+id).onchange=update;
document.querySelector('#version').onchange=e=>load(e.target.value);
function view(p){camera.position.set(...p);controls.target.set(0,0,2);controls.update();}document.querySelector('#iso').onclick=()=>view([125,-165,110]);document.querySelector('#front').onclick=()=>view([0,-210,2]);document.querySelector('#top').onclick=()=>view([0,-.01,225]);
function resize(){renderer.setSize(innerWidth,innerHeight);camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();}addEventListener('resize',resize);resize();view([125,-165,110]);load('15');renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
