/** Proposal coordinates: +X front/muzzle, +Y up, +Z side of tube.
 * Conventional hanging trigger rotates clockwise toward the rearward grip.
 * A vertical slot converts the upper pin's arc to a horizontal cable pull.
 * These are motion-illustration parameters, not frozen manufacturing CAD.
 */
export const triggerConcept={
  status:'conventional-trigger-layout-concept',units:'mm',
  coordinateBasis:'+X front/muzzle; +Y up; +Z side of tube',
  pivot:[0,0,40],inputRadius:36,outputRadius:60,outputStroke:20,
  grip:{top:[-52,6,26],bottom:[-64,-99,26],width:30},
  feederCenter:[125,-40,0],feederDirection:[Math.SQRT1_2,Math.SQRT1_2,0],
  inputHousingEnd:[-20,69,50],inputCableRest:20,feederCableRest:60,
  unverified:['new grip and pivot mount','cable and housing selection','housing anchor loads','hand clearance','operating force','integration with original blower']
};
export function triggerPose(u){
  if(!Number.isFinite(u))throw new TypeError('Stroke must be finite');
  const c=triggerConcept,s=Math.max(0,Math.min(c.outputStroke,u));
  const angle=Math.asin(s/c.outputRadius),[x,y,z]=c.pivot;
  const rearward=c.inputRadius*Math.sin(angle);
  return {u:s,angle,angleDeg:angle*180/Math.PI,
    input:[x-rearward,y-c.inputRadius*Math.cos(angle),z],
    output:[x+s,y+c.outputRadius*Math.cos(angle),z],
    cableInput:[x+s,69,50],
    rearward,squeeze:rearward,slotSideTravel:c.outputRadius*(1-Math.cos(angle)),
    inputFreeLength:c.inputCableRest+s,feederFreeLength:c.feederCableRest-s,
    feederCarriage:c.feederCenter.map((v,i)=>v+c.feederDirection[i]*s)};
}

// Articulated hand for explaining contact, not a human-fit certification.
// Finger pad remains on the FRONT (+X) face. Two-link IK keeps the proximal
// and middle phalanges rigid while the fingertip follows the trigger.
export function triggerHandPose(u){
  const p=triggerPose(u),c=Math.cos(p.angle),s=Math.sin(p.angle);
  const root=[-44,-14,50],padOffset=9.4;
  const tip=[padOffset*c-36*s,-padOffset*s-36*c,40];
  const distalLength=18,distalDir=[-.55,-Math.sqrt(1-.55**2),0];
  const dip=tip.map((v,i)=>v-distalDir[i]*distalLength);
  const delta=dip.map((v,i)=>v-root[i]),distance=Math.hypot(...delta);
  const lengths=[39,27,distalLength],direction=delta.map(v=>v/distance);
  const side=[-direction[0]*direction[1],1-direction[1]**2,-direction[2]*direction[1]];
  const sideLength=Math.hypot(...side),normal=side.map(v=>v/sideLength);
  const a=(lengths[0]**2-lengths[1]**2+distance**2)/(2*distance);
  const height=Math.sqrt(Math.max(0,lengths[0]**2-a**2));
  const pip=root.map((v,i)=>v+direction[i]*a+normal[i]*height);
  return {root,pip,dip,tip,lengths,reachable:distance<=lengths[0]+lengths[1],contactSide:'front +X; curls rearward toward palm'};
}
