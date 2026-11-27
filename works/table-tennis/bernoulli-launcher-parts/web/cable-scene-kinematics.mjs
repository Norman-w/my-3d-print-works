/** Source-contract driven display motion in FEEDER CAD millimetres.
 * This is a position illustration, not a cable/force/pneumatic simulation.
 * STL vertices already carry their assembled t=0 coordinates.
 */
const KINDS=new Set(['fixed','translate','radial','trigger-rotate','spring','input-wire','output-wire']);
const finite=(v,name)=>{if(typeof v!=='number'||!Number.isFinite(v))throw new TypeError(`Missing or invalid ${name}`);return v;};
const vector=(v,name)=>{if(!Array.isArray(v)||v.length!==3)throw new TypeError(`Missing ${name}`);return v.map((x,i)=>finite(x,`${name}[${i}]`));};
const positive=(v,name)=>{finite(v,name);if(v<=0)throw new RangeError(`${name} must be positive`);return v;};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const add=(a,b)=>a.map((x,i)=>x+b[i]);
const scale=(a,k)=>a.map(x=>x*k);
const distance=(a,b)=>Math.hypot(...a.map((x,i)=>x-b[i]));
const DIRECT_LAW='fixed-guide-direct-pull-v2';
const RAD=Math.PI/180;
const inputCache=new WeakMap();

function inputConfiguration(ci){
  if(!ci||ci.motion_law!==DIRECT_LAW)throw new TypeError(`Unsupported or missing ci.motion_law: ${ci?.motion_law}`);
  const keys=['motion_law','stroke','ball_orbit_radius','fairlead_center','fairlead_core_radius',
    'wire_terminal_local','angle_solve_deg','fairlead_extent_deg','adjuster_delta','adjuster_exit_local',
    'wire_tangent_local','ferrule_mouth_display_local','wire_z'];
  const signature=JSON.stringify(keys.map(k=>ci[k]));
  const cached=inputCache.get(ci);if(cached?.signature===signature)return cached;
  const c={signature,solutions:new Map(),stroke:positive(ci.stroke,'ci.stroke'),
    orbit:positive(ci.ball_orbit_radius,'ci.ball_orbit_radius'),
    radius:positive(ci.fairlead_core_radius,'ci.fairlead_core_radius'),
    center:vector(ci.fairlead_center,'ci.fairlead_center'),
    terminal:vector(ci.wire_terminal_local,'ci.wire_terminal_local'),
    start:vector(ci.wire_tangent_local,'ci.wire_tangent_local'),
    exit:vector(ci.adjuster_exit_local,'ci.adjuster_exit_local'),
    mouth:vector(ci.ferrule_mouth_display_local,'ci.ferrule_mouth_display_local'),
    z:finite(ci.wire_z,'ci.wire_z'),extent:positive(ci.fairlead_extent_deg,'ci.fairlead_extent_deg')*RAD};
  const delta=finite(ci.adjuster_delta,'ci.adjuster_delta');
  if(Math.abs(delta)>2)throw new RangeError('Input adjuster_delta exceeds the v2 -2..2 mm budget');
  if(!Array.isArray(ci.angle_solve_deg)||ci.angle_solve_deg.length!==2)throw new TypeError('Missing ci.angle_solve_deg');
  const [lo,hi]=ci.angle_solve_deg.map((v,i)=>finite(v,`ci.angle_solve_deg[${i}]`));
  if(lo!==0||hi<=lo||hi>=90)throw new RangeError('Invalid input angle solve interval');
  c.low=lo*RAD;c.high=hi*RAD;
  if(distance(c.terminal,[0,c.orbit,c.z])>1e-8||distance(c.start,[c.center[0],c.center[1]+c.radius,c.z])>1e-8||Math.abs(c.center[2]-c.z)>1e-8)
    throw new RangeError('Input terminal or fixed-guide start does not match the declared law');
  if(Math.abs(c.exit[1]-c.start[1])>1e-8||Math.abs(c.exit[2]-c.z)>1e-8||Math.abs(c.mouth[1]-c.start[1])>1e-8||Math.abs(c.mouth[2]-c.z)>1e-8||c.mouth[0]>=c.exit[0])
    throw new RangeError('Input adjuster and ferrule must share the fixed axial lead-in');
  if(Math.abs(c.terminal[1]-c.start[1])>1e-8||c.start[0]>=c.terminal[0])
    throw new RangeError('Rest terminal must extend the initial fixed-guide tangent');
  c.lead=c.start[0]-c.exit[0];
  if(c.lead<3-1e-8)throw new RangeError('Input axial lead-in is below the v2 3 mm budget');
  c.rest=pathAtAngle(c.low,c).L;
  // The mathematical bracket can exceed the guide's working arc; the solved
  // state, not an arbitrary upper bisection bound, must fit the actual guide.
  if(pathAtAngle(c.high,c).L-c.rest<c.stroke)throw new RangeError('Input angle solve interval does not bracket the working stroke');
  inputCache.set(ci,c);return c;
}

function pathAtAngle(a,c){
  const B=[c.orbit*Math.sin(a),c.orbit*Math.cos(a),c.z];
  const x=B[0]-c.center[0],y=B[1]-c.center[1],d=Math.hypot(x,y);
  if(d<=c.radius)throw new RangeError('Terminal has no external tangent to the fixed guide');
  const phi=Math.max(0,Math.atan2(x,y)-Math.acos(c.radius/d));
  const T=[c.center[0]+c.radius*Math.sin(phi),c.center[1]+c.radius*Math.cos(phi),c.z];
  const L=c.lead+c.radius*phi+Math.sqrt(d*d-c.radius*c.radius);
  return {a,phi,B,T,L};
}

/** One shared, source-parameter solution for the lever, cap, hardware and core.
 * Angles are radians. L is adjuster-exit-to-ball length, not a cable cut length.
 * The cache is keyed by all law parameters and retains only four recent poses.
 */
export function inputKinematics(u,ci){
  const c=inputConfiguration(ci);finite(u,'input displacement');
  if(u<0||u>c.stroke)throw new RangeError(`Input displacement must be 0..${c.stroke} mm`);
  if(c.solutions.has(u))return c.solutions.get(u);
  let lo=c.low,hi=c.high;
  for(let i=0;i<56;i++){const m=(lo+hi)/2;if(pathAtAngle(m,c).L-c.rest<u)lo=m;else hi=m;}
  const k=pathAtAngle(u===0?c.low:(lo+hi)/2,c);
  if(k.phi>c.extent+1e-12)throw new RangeError('Solved core tangent exceeds the fixed-guide arc');
  const takeup=k.L-c.rest;
  if(Math.abs(takeup-u)>1e-8)throw new RangeError('Input take-up inversion did not converge');
  const tangentLength=distance(k.B,k.T);
  const dB=[c.orbit*Math.cos(k.a),-c.orbit*Math.sin(k.a),0];
  const effectiveArm=dB.reduce((sum,v,i)=>sum+v*(k.B[i]-k.T[i])/tangentLength,0);
  if(effectiveArm<=0)throw new RangeError('Input take-up is not monotone at this pose');
  const answer=Object.freeze({...k,B:Object.freeze(k.B),T:Object.freeze(k.T),u,takeup,
    restLength:c.rest,effectiveArm,axialLeadIn:c.lead,coreLengthFromMouth:k.L+c.exit[0]-c.mouth[0]});
  if(c.solutions.size>=4)c.solutions.delete(c.solutions.keys().next().value);
  c.solutions.set(u,answer);return answer;
}
export const contractObject=value=>Array.isArray(value)?Object.fromEntries(value):value;
export const activeDuringTrigger=motion=>motion.active_during_trigger!==false&&(!motion.input||motion.input==='stroke');

export function cableContracts(value){
  if(!value||typeof value!=='object'||Array.isArray(value))throw new TypeError('Current cable scene needs its source contracts');
  const result={};
  for(const key of ['ci','co','cr','spring'])result[key]=contractObject(value[key]);
  if(!result.ci||!result.co||!result.cr||!result.spring)throw new TypeError('Missing ci/co/cr/spring source contract');
  positive(result.ci.stroke,'ci.stroke');positive(result.co.stroke,'co.stroke');
  if(result.ci.stroke!==20||result.co.stroke!==20)throw new RangeError('Current feeder cycle requires the declared 20 mm input/output stroke');
  positive(result.ci.radius_finger,'ci.radius_finger');
  for(const name of ['origin','basis_x','basis_y','basis_z'])vector(result.ci[name],`ci.${name}`);
  const axes=['basis_x','basis_y','basis_z'].map(key=>result.ci[key]);
  const dot=(a,b)=>a.reduce((sum,v,i)=>sum+v*b[i],0);
  if(axes.some(a=>Math.abs(dot(a,a)-1)>1e-5)||axes.some((a,i)=>axes.slice(i+1).some(b=>Math.abs(dot(a,b))>1e-5)))
    throw new RangeError('Input coordinate bases must be orthonormal');
  const [x,y,z]=axes,cross=[x[1]*y[2]-x[2]*y[1],x[2]*y[0]-x[0]*y[2],x[0]*y[1]-x[1]*y[0]];
  if(distance(cross,z)>1e-5)throw new RangeError('Input coordinate bases must be right-handed');
  positive(result.ci.wire_d,'ci.wire_d');
  inputKinematics(0,result.ci);inputKinematics(result.ci.stroke,result.ci);
  return result;
}

export function validateCableCatalogue(rows,contracts){
  if(!Array.isArray(rows)||!rows.length)throw new TypeError('Empty assembly catalogue');
  const ids=new Set();
  for(const row of rows){
    if(ids.has(row.id))throw new TypeError(`Duplicate model ${row.id}`);ids.add(row.id);
    if(!KINDS.has(row.motion?.kind))throw new TypeError(`Missing source motion for ${row.id}`);
    if(!row.file&&!row.subparts?.length)throw new TypeError(`Missing mesh for ${row.id}`);
    // Spin float/preload settings are independent controls, not this trigger's u.
    if(!activeDuringTrigger(row.motion))continue;
    for(const u of [0,contracts.ci.stroke]){
      const motion=row.motion;
      rigidPose(motion,u,contracts);
      if(motion.kind==='spring')springOffset(0,u,motion,contracts);
      if(motion.kind==='input-wire')inputCorePoints(u,motion,contracts);
      if(motion.kind==='output-wire')outputCorePoints(u,motion,contracts);
    }
  }
  const requiredMotion={
    'feeder/cable-input-lever':'trigger-rotate',
    'feeder/cable-input-terminal-cap':'trigger-rotate',
    'feeder/cable-input-hardware-moving':'trigger-rotate',
    'feeder/cable-core-input':'input-wire',
    'feeder/cable-core-output':'output-wire'
  };
  for(const [id,kind] of Object.entries(requiredMotion)){
    const row=rows.find(r=>r.id===id);
    if(row?.motion?.kind!==kind||!activeDuringTrigger(row.motion))
      throw new TypeError(`Missing or inactive v2 ${kind} model: ${id}`);
  }
}

export function strokeFraction(u,stroke){
  finite(u,'stroke displacement');positive(stroke,'full stroke');
  if(u<0||u>stroke)throw new RangeError(`Stroke displacement must be 0..${stroke} mm`);
  return u/stroke;
}
export function localInputToCad(point,ci){
  const p=vector(point,'input point');
  return ['basis_x','basis_y','basis_z'].reduce((out,key,i)=>add(out,scale(ci[key],p[i])),ci.origin.slice());
}
export function triggerPose(u,contracts){
  const {ci}=contracts,stroke=ci.stroke,t=strokeFraction(u,stroke),angle=inputKinematics(u,ci).a;
  return {outputStroke:t*stroke,fraction:t,angleRadians:-angle,angleDegrees:-angle*180/Math.PI,
    rearward:ci.radius_finger*Math.sin(angle),fullRearward:ci.radius_finger*Math.sin(inputKinematics(stroke,ci).a),
    pivot:ci.origin.slice(),axis:ci.basis_z.slice(),referenceOnly:true,
    fingerPoint:localInputToCad([-ci.radius_finger*Math.sin(angle),-ci.radius_finger*Math.cos(angle),ci.wire_z],ci)};
}

/** A pivot rotation uses T(origin) R T(-origin); never rotate assembled vertices about CAD zero. */
export function rigidPose(motion,u,contracts){
  if(!KINDS.has(motion?.kind))throw new TypeError(`Unsupported motion: ${motion?.kind}`);
  if(!activeDuringTrigger(motion))return {position:[0,0,0]};
  const t=strokeFraction(u,motion.stroke_mm??contracts.ci.stroke);
  if(motion.kind==='translate')return {position:scale(vector(motion.axis,'motion.axis'),finite(motion.distance_mm,'motion.distance_mm')*t)};
  if(motion.kind==='radial'){
    const [start,end]=motion.breakpoints||[];finite(start,'radial start');finite(end,'radial end');
    if(end<=start)throw new RangeError('Invalid radial breakpoints');
    const closed=finite(motion.closed_mm,'closed radius'),open=finite(motion.open_mm,'open radius');
    const side=finite(motion.side,'radial side');if(side!==-1&&side!==1)throw new RangeError('Radial side must be -1 or 1');
    const f=clamp((t-start)/(end-start),0,1);
    const initial=motion.rear?open:closed,r=motion.rear?open-(open-closed)*f:closed+(open-closed)*f;
    return {position:scale(vector(motion.axis??[1,0,0],'radial axis'),side*(r-initial)),radius:r};
  }
  if(motion.kind==='trigger-rotate'){
    const {ci}=contracts,origin=vector(motion.origin,'trigger origin'),axis=vector(motion.axis,'trigger axis');
    if(motion.radians_per_t!==undefined)throw new TypeError('Linear radians_per_t is incompatible with the v2 direct-pull law');
    if((motion.stroke_mm??ci.stroke)!==ci.stroke||distance(origin,ci.origin)>1e-8||distance(axis,ci.basis_z)>1e-8)
      throw new RangeError('Trigger row does not match the source pivot, axis or stroke');
    return {position:[0,0,0],origin,axis,angle:-inputKinematics(u,ci).a};
  }
  return {position:[0,0,0]};
}

/** Lower eye is fixed, upper eye translates; only the coil span changes length. */
export function springOffset(z,u,motion,contracts){
  const source=contracts.spring||{};
  const start=finite(motion.coil_start_z??source.coil_start_z,'spring coil_start_z');
  const end=finite(motion.coil_end_z??source.coil_end_z,'spring coil_end_z');
  if(end<=start)throw new RangeError('Invalid spring coil span');
  const stroke=motion.stroke_mm??source.stroke_mm??contracts.ci.stroke;
  return clamp((z-start)/(end-start),0,1)*strokeFraction(u,stroke)*stroke;
}

/** Moving ball -> tangent -> fixed guide arc -> axial lead-in -> ferrule mouth. */
export function inputCorePoints(u,motion,contracts){
  const {ci}=contracts,k=inputKinematics(u,ci),c=inputConfiguration(ci);
  if(motion.arc_rest_angle_deg!==undefined||motion.arc_end_angle_deg!==undefined)
    throw new TypeError('Legacy input wrap angles are incompatible with the v2 core path');
  const points=[k.B,k.T],segments=Math.ceil(k.phi/(.1*RAD));
  for(let i=1;i<=segments;i++){
    const phi=k.phi*(1-i/segments);
    points.push([c.center[0]+c.radius*Math.sin(phi),c.center[1]+c.radius*Math.cos(phi),c.z]);
  }
  points.push(c.mouth);
  return points.filter((p,i)=>i===0||distance(p,points[i-1])>1e-10).map(p=>localInputToCad(p,ci));
}

/** Output core has a stationary upper endpoint and a translating lower tail. */
export function outputCorePoints(u,motion,contracts){
  const {co}=contracts,stroke=positive(co.stroke,'co.stroke'),t=strokeFraction(u,stroke);
  const a=vector(co.moving_wire_axis_t0,'output initial axis'),b=vector(co.moving_wire_axis_t1,'output final axis');
  const axis=a.map((x,i)=>x+(b[i]-x)*t),tail=finite(co.wire_tail_below_center,'output tail');
  return [axis.map((x,i)=>x-(i===2?tail:0)),vector(co.housing_route_entry,'output upper endpoint')];
}

export function coreDiameter(kind,contracts){
  return positive((kind==='input-wire'?contracts.ci:contracts.co).wire_d,'core diameter');
}

export function isCableAccessory(row){
  return row.id.startsWith('feeder/cable-')||['trigger-rotate','input-wire','output-wire'].includes(row.motion?.kind);
}
