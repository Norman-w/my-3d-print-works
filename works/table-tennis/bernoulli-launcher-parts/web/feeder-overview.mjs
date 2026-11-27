import * as THREE from 'three';

// Connection illustration only. The user's Y fitting, blower and hose route
// have not been measured. These objects must never be used as cutting lengths.
export function createOverview(material) {
  const group=new THREE.Group(), labels=[];
  const layers=Object.fromEntries(['hopper','hose','blower','pipes'].map(name=>{
    const layer=new THREE.Group();layer.name=`overview-${name}`;group.add(layer);return [name,layer];
  }));
  const v=a=>new THREE.Vector3(...a);
  const grey=material(0x91a9b7,{side:THREE.DoubleSide});
  const clear=material(0x91d5df,{transparent:true,opacity:.24,depthWrite:false,side:THREE.DoubleSide});
  const air=material(0x68b9f8);
  function cylinder(layer,a,b,r,mat,open=false){
    const p=v(a),q=v(b),delta=q.clone().sub(p);
    const mesh=new THREE.Mesh(new THREE.CylinderGeometry(r,r,delta.length(),36,1,open),mat);
    mesh.position.copy(p.add(q).multiplyScalar(.5));
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0,1,0),delta.normalize());
    layers[layer].add(mesh);return mesh;
  }
  function box(layer,at,size,mat){const mesh=new THREE.Mesh(new THREE.BoxGeometry(...size),mat);mesh.position.set(...at);layers[layer].add(mesh);return mesh;}
  function arrow(layer,a,b,color){const p=v(a),d=v(b).sub(p);const x=new THREE.ArrowHelper(d.clone().normalize(),p,d.length(),color,14,8);layers[layer].add(x);return x;}
  function label(layer,text,point){labels.push({text,point:v(point),layer});}

  // Main air axis is horizontal. The feeder is on the separate diagonal branch.
  cylinder('pipes',[-175,0,0],[85,0,0],29,grey,true);
  cylinder('pipes',[-55,-55,0],[0,0,0],29,grey,true);
  cylinder('pipes',[-59.54,-59.54,0],[-40,-40,0],25,clear,true);
  cylinder('pipes',[85,0,0],[380,0,0],25,clear,true);
  // The main scene mounts the detailed spin-head STL assembly at the outlet.
  // Do not overlay it with a second, simplified head in this context layer.

  // Blower silhouette identifies the connection; it is not a selected model.
  cylinder('blower',[-225,0,-22],[-225,0,22],48,air);
  cylinder('blower',[-205,0,0],[-174,0,0],23,air);
  box('blower',[-255,-67,0],[20,62,25],air);
  box('blower',[-255,-100,0],[66,24,42],grey);
  // Hopper and curved hose, drawn separately from the main blower path.
  cylinder('hopper',[-450,-35,0],[-450,195,0],76,clear);
  cylinder('hopper',[-450,195,0],[-450,208,0],79,grey);
  cylinder('hopper',[-450,-45,0],[-450,-22,0],27.5,grey);
  const sphere=new THREE.SphereGeometry(20.5,18,12),ballMat=material(0xf5eee0);
  for(let row=0;row<3;row++)for(let col=0;col<3;col++){
    const ball=new THREE.Mesh(sphere,ballMat);ball.position.set(-490+col*40,row*39,4+(col%2)*15);layers.hopper.add(ball);
  }
  const inlet=v([-155,-155,0]).add(v([-1,-1,0]).normalize().multiplyScalar(110));
  const hoseCurve=new THREE.CatmullRomCurve3([v([-450,-43,0]),v([-450,-230,0]),v([-335,-320,0]),inlet]);
  const hose=new THREE.Mesh(new THREE.TubeGeometry(hoseCurve,72,27.5,20,false),clear);layers.hose.add(hose);
  const ribGeom=new THREE.TorusGeometry(27,1.1,5,28),ribMat=material(0x789ca7);
  for(let i=0;i<=36;i++){
    const ring=new THREE.Mesh(ribGeom,ribMat);ring.position.copy(hoseCurve.getPointAt(i/36));
    ring.quaternion.setFromUnitVectors(new THREE.Vector3(0,0,1),hoseCurve.getTangentAt(i/36));layers.hose.add(ring);
  }
  arrow('pipes',[-148,38,0],[-45,38,0],0x68b9f8);arrow('pipes',[122,42,0],[222,42,0],0x68b9f8);
  arrow('pipes',[445,0,0],[508,0,0],0xf4c05c);
  arrow('hose',[-318,-275,35],[-276,-240,35],0xf4c05c);
  label('hopper','球仓',[-450,245,0]);label('hose','软管 · 内50 / 外55',[-420,-335,0]);
  label('pipes','PC短节 · 内48 / 外50',[-20,-114,0]);
  label('pipes','原斜三通',[5,68,0]);label('blower','风机 · 送风',[-255,80,0]);
  label('pipes','出球管',[235,-58,0]);
  label('pipes','出球',[510,-52,0]);
  return {group,labels,layers};
}
