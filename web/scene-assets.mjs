import * as THREE from 'three';
import {STLLoader} from 'three/addons/loaders/STLLoader.js';

/** One catalogue entry -> one persistent scene node. Visibility never reloads it. */
export function createAssetStore({attach,material,onChange}){
  const loader=new STLLoader(),pending=new Map(),loaded=new Map();
  async function ensure(row){
    if(pending.has(row.id))return pending.get(row.id);
    const task=(async()=>{
      const group=new THREE.Group();group.name=row.id;
      const pieces=row.subparts||[{file:row.file,motionGroup:row.id.split('/')[1],motion:row.motion,sha256:row.sha256}];
      const meshes=[];
      for(const piece of pieces){
        const geometry=await loader.loadAsync(piece.file);geometry.computeVertexNormals();geometry.computeBoundingBox();
        const mesh=new THREE.Mesh(geometry,material(row));mesh.name=piece.id||row.id;
        mesh.userData.motionGroup=piece.motionGroup;
        mesh.userData.motion=piece.motion||row.motion;
        mesh.userData.sourceFile=piece.file;mesh.userData.sourceSha256=piece.sha256||row.sha256;
        if(mesh.userData.motion?.kind==='spring'||row.id==='feeder/spring-reference'){
          mesh.userData.restPositions=geometry.attributes.position.array.slice();
        }
        group.add(mesh);meshes.push(mesh);
      }
      const record={row,group,meshes,instanceId:group.uuid};
      if(row.id==='feeder/spring-reference')record.springBase=meshes[0].geometry.attributes.position.array.slice();
      loaded.set(row.id,record);attach(record);onChange?.(record);return record;
    })().catch(e=>{pending.delete(row.id);throw e;});
    pending.set(row.id,task);return task;
  }
  async function ensureMany(rows){
    for(let i=0;i<rows.length;i+=4)await Promise.all(rows.slice(i,i+4).map(ensure));
  }
  return {ensure,ensureMany,loaded};
}
