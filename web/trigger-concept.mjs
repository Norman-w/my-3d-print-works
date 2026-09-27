import * as THREE from 'three';
import {triggerConcept as spec,triggerPose,triggerHandPose} from './trigger-concept-kinematics.mjs';

// The grip, trigger, cable anchors and feeder are proposed illustration shapes.
// They do not modify or claim to fit the preserved STL assembly.
export function createTriggerConcept(material){
  const group=new THREE.Group(),labels=[];
  const blue=material(0x58c5ee),yellow=material(0xf4c05c),fixed=material(0x738999),metal=material(0xd4e1e8),purple=material(0xb69af1);
  const transparent=material(0x8dbbc8,{transparent:true,opacity:.24,depthWrite:false,side:THREE.DoubleSide});
  const point=a=>new THREE.Vector3(...a);
  function box(parent,at,size,mat){const m=new THREE.Mesh(new THREE.BoxGeometry(...size),mat);m.position.set(...at);parent.add(m);return m;}
  function rod(parent,a,b,r,mat,open=false){const p=point(a),q=point(b),d=q.clone().sub(p);const m=new THREE.Mesh(new THREE.CylinderGeometry(r,r,d.length(),32,1,open),mat);m.position.copy(p.add(q).multiplyScalar(.5));m.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),d.normalize());parent.add(m);return m;}
  function line(parent,pts,r,mat){const m=new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map(point)),70,r,10,false),mat);parent.add(m);return m;}
  function label(text,p){labels.push({text,point:()=>point(p)});}
  function arrow(a,b,color){const p=point(a),d=point(b).sub(p),m=new THREE.ArrowHelper(d.clone().normalize(),p,d.length(),color,9,5);group.add(m);return m;}
  // Machine context fixes the natural front/back/up orientation.
  rod(group,[-105,80,0],[320,80,0],25,transparent,true);
  rod(group,[235,80,0],[273,80,0],29,fixed,true);
  rod(group,[-150,80,-20],[-150,80,20],43,fixed);
  rod(group,[-124,80,0],[-104,80,0],23,fixed);
  rod(group,[303,80,0],[343,80,0],29,material(0x73d7a5),true);
  arrow([345,80,0],[390,80,0],0x73d7a5);
  label('前方 / 出球',[350,122,0]);label('风机',[-155,137,0]);
  // Vertical tool-style grip behind the trigger; pivot is fixed at the top.
  rod(group,spec.grip.top,spec.grip.bottom,15,fixed);
  box(group,[-61,-104,26],[34,9,34],fixed);
  box(group,[-35,8,23],[70,15,13],fixed);
  box(group,[-54,33,20],[14,47,12],fixed);
  const gripCollar=new THREE.Mesh(new THREE.TorusGeometry(27.5,2.5,12,56),fixed);
  gripCollar.rotation.y=Math.PI/2;gripCollar.position.set(-54,80,0);group.add(gripCollar);
  rod(group,[-54,52,20],[-54,50,0],3,fixed);
  rod(group,[0,0,16],[0,0,31],9,fixed);
  rod(group,[0,0,17],[0,0,49],4,metal);
  line(group,[[-37,-9,40],[25,-9,40],[38,-27,40],[26,-63,40],[-46,-63,40]],2.3,fixed);
  const trigger=new THREE.Group();trigger.position.set(...spec.pivot);group.add(trigger);
  line(trigger,[[0,0,0],[-3,-13,0],[-4,-26,0],[0,-36,0],[3,-42,0]],3.4,blue);
  // Keep the internal transmission visually distinct from the finger blade.
  rod(trigger,[0,0,0],[0,spec.outputRadius,0],3.4,metal);
  rod(trigger,[0,spec.outputRadius,-6],[0,spec.outputRadius,12],2.5,metal);
  const carriage=new THREE.Group();group.add(carriage);
  for(const xx of[-4.5,4.5])box(carriage,[xx,58,48],[3,16,4],yellow);
  for(const yy of[50,66])box(carriage,[0,yy,48],[12,3,4],yellow);
  box(carriage,[0,69,44],[14,7,14],yellow);
  rod(group,[-13,69,44],[42,69,44],2,metal);
  // Separate diagonal feed branch.
  const F=point(spec.feederCenter),d=point(spec.feederDirection),e=new THREE.Vector3(-d.y,d.x,0);
  const at=(distance,side=0,depth=0)=>F.clone().addScaledVector(d,distance).addScaledVector(e,side).add(new THREE.Vector3(0,0,depth)).toArray();
  rod(group,at(-66),at(66),33,transparent,true);
  rod(group,at(66),[245,80,0],25,transparent,true);
  line(group,[at(-68),[39,-145,0],[-100,-165,0],[-176,-95,0]],27.5,transparent);
  const feederCarriage=new THREE.Group();group.add(feederCarriage);
  for(const side of[-1,1])rod(feederCarriage,at(-38,side*40,35),at(15,side*40,35),3,yellow);
  rod(feederCarriage,at(15,-40,35),at(15,40,35),3.5,yellow);
  rod(feederCarriage,at(15,0,35),at(15,0,50),3,metal);
  // Two stationary housing anchors. Input free length increases u while the
  // feeder free length decreases u. Attach wire to guided carriages, not pin.
  const inputAnchor=spec.inputHousingEnd,outputAnchor=at(75,0,50);
  line(group,[inputAnchor,[-81,83,44],[-48,151,44],[126,152,50],outputAnchor],3,purple);
  box(group,inputAnchor,[8,12,12],fixed);
  rod(group,[-20,75,50],[-20,81,27],3,fixed);
  box(group,outputAnchor,[12,12,12],fixed);
  rod(group,at(75,0,50),at(75,0,27),3.5,fixed);
  const inputWire=rod(group,inputAnchor,[0,69,50],.9,metal);
  const outputWire=rod(group,at(15,0,50),outputAnchor,.9,metal);
  // Warm translucent palm grips the fixed handle. Only the index articulates.
  const handMaterial=material(0xeeb697,{transparent:true,opacity:.72,depthWrite:false,roughness:.86});
  const jointGeometry=new THREE.SphereGeometry(1,20,14);
  function joint(at,scale){const m=new THREE.Mesh(jointGeometry,handMaterial);m.position.set(...at);m.scale.set(...scale);group.add(m);return m;}
  joint([-82,-68,55],[18,35,13]);
  rod(group,[-112,-90,53],[-88,-80,54],14,handMaterial);
  rod(group,[-79,-38,55],[-44,-14,50],8,handMaterial);
  line(group,[[-82,-39,59],[-67,-20,61],[-49,-25,57]],7,handMaterial);
  for(const y of[-65,-80,-94])line(group,[[-80,y,55],[-50,y+3,57],[-39,y-1,39],[-48,y-7,23]],5.5,handMaterial);
  const handSegments=[],handJoints=[];
  for(let i=0;i<3;i++)handSegments.push(rod(group,[0,0,0],[0,1,0],i===0?6.2:i===1?5.8:5.3,handMaterial));
  for(let i=0;i<4;i++)handJoints.push(joint([0,0,0],[i===3?6:6.2,i===3?6:6.2,i===3?6:6.2]));
  const handArrow=arrow([23,-78,45],[-18,-78,45],0x58c5ee);
  const feedArrow=arrow(at(-5,68,25),at(37,68,25),0xf4c05c);
  label('近端 · 虎口 / 掌心',[-115,-33,56]);
  label('扳机 · 向近端勾扣',[-8,-121,55]);
  label('固定铰点',[1,23,48]);
  label('拉索 · 两端线管固定',[46,183,48]);
  label('送料模块 · 位于斜支路',[181,-115,25]);
  label('内部送料滑架',[165,25,50]);
  label('三通',[261,117,0]);
  label('接球仓软管',[-133,-177,0]);
  function update(u,{returning=false,released=false}={}){
    const p=triggerPose(u);trigger.rotation.z=-p.angle;carriage.position.x=p.u;
    const releaseDirection=returning||released;
    handArrow.position.set(releaseDirection?-18:23,-78,45);
    handArrow.setDirection(new THREE.Vector3(releaseDirection?1:-1,0,0));
    handArrow.setColor(releaseDirection?0x73d7a5:0x58c5ee);
    feedArrow.position.copy(point(at(releaseDirection?37:-5,68,25)));
    feedArrow.setDirection(d.clone().multiplyScalar(releaseDirection?-1:1));
    feederCarriage.position.copy(d).multiplyScalar(p.u);
    inputWire.scale.y=p.inputFreeLength/spec.inputCableRest;
    inputWire.position.set(-20+p.inputFreeLength/2,69,50);
    outputWire.scale.y=p.feederFreeLength/spec.feederCableRest;
    outputWire.position.copy(point(at(15+p.u,0,50)).add(point(outputAnchor)).multiplyScalar(.5));
    const hand=triggerHandPose(u),pts=[hand.root,hand.pip,hand.dip,hand.tip];
    for(let i=0;i<3;i++){
      const a=point(pts[i]),b=point(pts[i+1]),delta=b.clone().sub(a),mesh=handSegments[i];
      mesh.position.copy(a.add(b).multiplyScalar(.5));mesh.scale.y=delta.length();
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.normalize());
    }
    handJoints.forEach((mesh,i)=>mesh.position.set(...pts[i]));
    return p;
  }
  update(0);return {group,labels,update};
}
