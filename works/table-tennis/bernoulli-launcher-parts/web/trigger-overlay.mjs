import * as THREE from 'three';
import {triggerConcept as spec,triggerPose,triggerHandPose} from './trigger-concept-kinematics.mjs';

// Operation proposal laid over the preserved assembly. There is no second
// blower, tube, Y fitting, feeder shell or feeder carriage in this module.
// Mounts, cable routing and hand proportions explain the motion only.
export function createTriggerOverlay(material,{
  inputToWorld,
  feederMovingPoint,
  feederFixedPoint,
  offset=new THREE.Vector3(-100,-95,110),
}={}){
  if(typeof feederMovingPoint!=='function'||!feederFixedPoint?.isVector3){
    throw new TypeError('Trigger overlay needs feederMovingPoint(u) and a world-space feederFixedPoint Vector3');
  }
  const group=new THREE.Group();group.name='trigger-operation-proposal';
  const inputGroup=new THREE.Group();inputGroup.name='trigger-and-grip-proposal';
  const handGroup=new THREE.Group();handGroup.name='illustrative-hand';
  const cableGroup=new THREE.Group();cableGroup.name='cable-routing-proposal';
  group.add(inputGroup,cableGroup);inputGroup.add(handGroup);
  const labels=[],v=a=>new THREE.Vector3(...a),up=new THREE.Vector3(0,1,0);
  const placement=offset.isVector3?offset.clone():v(offset);
  const map=inputToWorld??(p=>p.add(placement));
  // A caller may supply a rigid local-to-world transform. Build it once so
  // meshes, finger poses and labels share exactly the same coordinate basis.
  const origin=map(new THREE.Vector3()).clone();
  const axes=[[1,0,0],[0,1,0],[0,0,1]].map(a=>map(v(a)).clone().sub(origin));
  if(axes.some(a=>Math.abs(a.length()-1)>1e-6)||
     Math.abs(axes[0].dot(axes[1]))>1e-6||Math.abs(axes[1].dot(axes[2]))>1e-6||
     Math.abs(axes[2].dot(axes[0]))>1e-6||
     axes[0].clone().cross(axes[1]).dot(axes[2])<.999999){
    throw new TypeError('inputToWorld must preserve a right-handed millimetre coordinate basis');
  }
  inputGroup.matrix.makeBasis(...axes).setPosition(origin);inputGroup.matrixAutoUpdate=false;
  const world=p=>(p.isVector3?p.clone():v(p)).applyMatrix4(inputGroup.matrix);
  const blue=material(0x58c5ee),yellow=material(0xf4c05c),fixed=material(0x738999);
  const metal=material(0xd4e1e8),purple=material(0xb69af1);
  function box(parent,at,size,mat){
    const m=new THREE.Mesh(new THREE.BoxGeometry(...size),mat);m.position.copy(at.isVector3?at:v(at));parent.add(m);return m;
  }
  function setRod(mesh,a,b){
    const delta=b.clone().sub(a),length=delta.length();
    mesh.visible=length>1e-7;mesh.position.copy(a).add(b).multiplyScalar(.5);mesh.scale.y=length;
    if(mesh.visible)mesh.quaternion.setFromUnitVectors(up,delta.divideScalar(length));
    return length;
  }
  function rod(parent,a,b,r,mat){
    const m=new THREE.Mesh(new THREE.CylinderGeometry(r,r,1,24),mat);parent.add(m);
    setRod(m,a.isVector3?a:v(a),b.isVector3?b:v(b));return m;
  }
  function line(parent,points,r,mat){
    const curve=new THREE.CatmullRomCurve3(points.map(p=>p.isVector3?p.clone():v(p)));
    const m=new THREE.Mesh(new THREE.TubeGeometry(curve,70,r,10,false),mat);parent.add(m);return m;
  }
  function label(text,p){labels.push({text,point:()=>world(p)});}

  // Fixed grip and local support; the connection into the host remains an
  // installation proposal, explicitly labelled instead of a fabricated fit.
  rod(inputGroup,spec.grip.top,spec.grip.bottom,15,fixed);
  box(inputGroup,[-61,-104,26],[34,9,34],fixed);
  box(inputGroup,[-35,8,23],[70,15,13],fixed);
  box(inputGroup,[-54,33,20],[14,47,12],fixed);
  box(inputGroup,[-54,55,20],[32,6,22],fixed);
  rod(inputGroup,[0,0,16],[0,0,31],9,fixed);
  rod(inputGroup,[0,0,17],[0,0,49],4,metal);
  line(inputGroup,[[-37,-9,40],[25,-9,40],[38,-27,40],[26,-63,40],[-46,-63,40]],2.3,fixed);
  const trigger=new THREE.Group();trigger.position.set(...spec.pivot);inputGroup.add(trigger);
  line(trigger,[[0,0,0],[-3,-13,0],[-4,-26,0],[0,-36,0],[3,-42,0]],3.4,blue);
  rod(trigger,[0,0,0],[0,spec.outputRadius,0],3.4,metal);
  rod(trigger,[0,spec.outputRadius,-6],[0,spec.outputRadius,12],2.5,metal);

  // This small slotted part belongs to the trigger transmission. The actual
  // feeder carriage is supplied by the caller's original detailed rig.
  const inputSlider=new THREE.Group();inputSlider.name='trigger-cable-input-slider';inputGroup.add(inputSlider);
  for(const x of[-4.5,4.5])box(inputSlider,[x,58,48],[3,16,4],yellow);
  for(const y of[50,66])box(inputSlider,[0,y,48],[12,3,4],yellow);
  box(inputSlider,[0,69,44],[14,7,14],yellow);
  rod(inputGroup,[-13,69,44],[42,69,44],2,metal);
  const inputAnchor=v(spec.inputHousingEnd),outputAnchor=feederFixedPoint.clone();
  box(inputGroup,inputAnchor,[8,12,12],fixed);
  rod(inputGroup,[-20,75,50],[-20,81,27],3,fixed);
  rod(inputGroup,[-20,81,27],[-54,55,20],3,fixed);
  const inputAnchorWorld=world(inputAnchor);
  const inputWire=rod(inputGroup,inputAnchor,v([0,69,50]),.9,metal);
  const outputWire=rod(cableGroup,feederMovingPoint(0),outputAnchor,.9,metal);
  // Output anchor is shown at the caller's attachment coordinate. It is not a
  // model of a manufactured clamp or a declaration that the host supports it.
  const outputFerrule=new THREE.Mesh(new THREE.SphereGeometry(4.5,16,10),purple);
  outputFerrule.position.copy(outputAnchor);cableGroup.add(outputFerrule);
  const archY=Math.max(inputAnchorWorld.y,outputAnchor.y)+135;
  const archZ=Math.max(inputAnchorWorld.z,outputAnchor.z)+12;
  line(cableGroup,[inputAnchorWorld,
    inputAnchorWorld.clone().add(new THREE.Vector3(-44,25,0)),
    new THREE.Vector3(inputAnchorWorld.x-50,archY,archZ),
    new THREE.Vector3(outputAnchor.x,archY,archZ),
    outputAnchor.clone().add(new THREE.Vector3(0,35,0)),outputAnchor],3,purple);
  labels.push({text:'拉索 · 路径与安装待定',point:()=>new THREE.Vector3((inputAnchorWorld.x+outputAnchor.x)/2,archY+19,archZ)});

  // Palm and other fingers remain on the fixed grip. Only the index curls,
  // with its pad on the forward concave face of the blue trigger blade.
  const handMaterial=material(0xeeb697,{transparent:true,opacity:.72,depthWrite:false,roughness:.86});
  const jointGeometry=new THREE.SphereGeometry(1,20,14);
  function joint(at,scale){
    const m=new THREE.Mesh(jointGeometry,handMaterial);m.position.set(...at);m.scale.set(...scale);handGroup.add(m);return m;
  }
  joint([-82,-68,55],[18,35,13]);
  rod(handGroup,[-112,-90,53],[-88,-80,54],14,handMaterial);
  rod(handGroup,[-79,-38,55],[-44,-14,50],8,handMaterial);
  line(handGroup,[[-82,-39,59],[-67,-20,61],[-49,-25,57]],7,handMaterial);
  for(const y of[-65,-80,-94])line(handGroup,[[-80,y,55],[-50,y+3,57],[-39,y-1,39],[-48,y-7,23]],5.5,handMaterial);
  const handSegments=[6.2,5.8,5.3].map(r=>rod(handGroup,[0,0,0],[0,1,0],r,handMaterial));
  const handJoints=[6.2,6.2,6.2,6].map(r=>joint([0,0,0],[r,r,r]));
  const handArrow=new THREE.ArrowHelper(new THREE.Vector3(-1,0,0),v([23,-78,45]),41,0x58c5ee,9,5);
  inputGroup.add(handArrow);
  label('扳机 · 近端勾扣 / 方案叠加',[-10,-124,55]);
  label('握把支架 · 安装待定',[-104,58,30]);

  function update(u,{returning=false,released=false}={}){
    const p=triggerPose(u);trigger.rotation.z=-p.angle;inputSlider.position.x=p.u;
    const releaseDirection=returning||released;
    handArrow.position.set(releaseDirection?-18:23,-78,45);
    handArrow.setDirection(new THREE.Vector3(releaseDirection?1:-1,0,0));
    handArrow.setColor(releaseDirection?0x73d7a5:0x58c5ee);
    setRod(inputWire,inputAnchor,v(p.cableInput));
    const outputPoint=feederMovingPoint(p.u);
    if(!outputPoint?.isVector3||!outputPoint.toArray().every(Number.isFinite))throw new TypeError('feederMovingPoint must return a finite world-space Vector3');
    const outputFreeLength=setRod(outputWire,outputPoint,outputAnchor);
    const hand=triggerHandPose(p.u),points=[hand.root,hand.pip,hand.dip,hand.tip];
    handSegments.forEach((mesh,i)=>setRod(mesh,v(points[i]),v(points[i+1])));
    handJoints.forEach((mesh,i)=>mesh.position.set(...points[i]));
    return {...p,inputWorld:world(p.input).toArray(),cableInputWorld:world(p.cableInput).toArray(),
      cableOutputWorld:outputPoint.toArray(),outputFreeLength,
      proposalOnly:true};
  }
  update(0);
  return {group,handGroup,cableGroup,labels,update,inputToWorld:world,
    anchors:{input:inputAnchorWorld.clone(),output:outputAnchor.clone()},offset:origin.clone()};
}
