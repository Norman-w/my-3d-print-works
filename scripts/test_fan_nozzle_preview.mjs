import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { validateManifest } from "../web/fan-nozzle/manifest-core.mjs";
import { positionsFromStl, splitConnectedIslands } from "../web/fan-nozzle/connected-islands.mjs";
import { rotationForTravel, createMotionAdapter } from "../web/fan-nozzle/project-motion.mjs";
import * as THREE from "../web/fan-nozzle/vendor/three.module.js";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const preview = resolve(root, "output/fan-nozzle-preview");
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const read = async path => JSON.parse(await readFile(path, "utf8"));
const endpoint = process.argv[2];

function checkClosedMesh(positions) {
  const key = i => [0,1,2].map(j=>Math.round(positions[i+j]*1e6)).join(",");
  const edges = new Map();
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  for (let i=0; i<positions.length; i+=9) {
    const face = [key(i),key(i+3),key(i+6)];
    assert.equal(new Set(face).size,3,"Collapsed Y triangle");
    a.fromArray(positions,i); b.fromArray(positions,i+3); c.fromArray(positions,i+6);
    assert.ok(b.sub(a).cross(c.sub(a)).lengthSq()>1e-16,"Zero-area Y triangle");
    for (let j=0;j<3;j++) {
      const from = face[j], to = face[(j+1)%3];
      const order = from<to ? 1 : -1;
      const id = order===1 ? `${from}|${to}` : `${to}|${from}`;
      const e = edges.get(id) || { count:0, winding:0 };
      e.count++; e.winding+=order; edges.set(id,e);
    }
  }
  assert.ok(edges.size>0);
  for (const {count,winding} of edges.values()) {
    assert.equal(count,2,"Open/non-manifold Y edge");
    assert.equal(winding,0,"Inconsistent Y face winding");
  }
}

function checkTeeMesh(positions, c) {
  checkClosedMesh(positions);
  assert.equal(splitConnectedIslands(positions).length, 1, "Y reference must be one connected shell");
  const a = new THREE.Vector3(), b = new THREE.Vector3(), d = new THREE.Vector3(), hit = new THREE.Vector3();
  const intersections = (origin, direction) => {
    const ray = new THREE.Ray(origin, direction.clone().normalize());
    const distances = [];
    for (let i=0; i<positions.length; i+=9) {
      a.fromArray(positions,i); b.fromArray(positions,i+3); d.fromArray(positions,i+6);
      if (ray.intersectTriangle(a,b,d,false,hit)) distances.push(hit.distanceTo(origin));
    }
    return distances.sort((x,y)=>x-y).filter((x,i,all)=>i===0 || x-all[i-1]>1e-5);
  };
  const inMaterial = point => intersections(point,new THREE.Vector3(1,0.271,0.173)).length % 2 === 1;
  const side = new THREE.Vector3(0,1,0);
  for (const port of ["fan","outlet","ball"]) {
    const mouth = new THREE.Vector3(...c[`${port}_port`]);
    const outward = new THREE.Vector3(...c[`${port}_outward`]).normalize();
    const origin = mouth.clone().addScaledVector(outward, 1);
    const inward = outward.clone().negate();
    const pathLength = port === "ball" ? c.illustrative_branch_length : c.illustrative_main_length;
    assert.ok(intersections(origin,inward).every(t=>t>pathLength+1), `${port} has a blocked bore`);
    const midpoint = mouth.clone().addScaledVector(outward,-c.illustrative_socket_depth/2);
    assert.ok(!inMaterial(midpoint.clone().addScaledVector(side,c.measured_socket_id/2-0.2)), `${port} socket ID narrowed`);
    assert.ok(inMaterial(midpoint.clone().addScaledVector(side,(c.measured_socket_id+c.illustrative_socket_od)/4)), `${port} enlarged socket missing`);
    const lip = mouth.clone().addScaledVector(outward,-c.illustrative_lip_length/2);
    assert.ok(inMaterial(lip.addScaledVector(side,(c.illustrative_socket_od+c.illustrative_lip_od)/4)), `${port} terminal bead missing`);
  }
  assert.ok(!inMaterial(new THREE.Vector3(0,(c.illustrative_socket_od+c.illustrative_lip_od)/4,c.illustrative_junction_z)),
    "Spurious root flange returned");
  assert.ok(!inMaterial(new THREE.Vector3(0,(c.illustrative_body_od+c.illustrative_socket_od)/4,12)),
    "Main stem must be narrower than sockets");
}

assert.throws(()=>checkClosedMesh(new Float32Array([0,0,0,1,0,0,1,0,0])),/Collapsed/);
assert.throws(()=>checkClosedMesh(new Float32Array([0,0,0,1,0,0,2,0,0])),/Zero-area/);
assert.throws(()=>checkClosedMesh(new Float32Array([0,0,0,1,0,0,0,1,0])),/Open\/non-manifold/);

let checks = 0;
for (const [filename, travel, variant] of [["manifest.json",80,"fan76-direct"], ["manifest-fan41-direct.json",40,"fan41-direct"]]) {
  const manifest = await read(resolve(preview, filename));
  const index = validateManifest(manifest);
  assert.equal(manifest.variantId, variant);
  assert.equal(manifest.release.travelMm, travel);
  assert.equal(manifest.release.pitchMm, 4);
  assert.deepEqual(manifest.release.outletIdsMm, [15,20,25,30]);
  assert.equal(index.parts.size, 7);
  assert.equal([...index.frames.values()].filter(f => f.kind !== "fixed").length, 1);
  const screw = manifest.screwMotion;
  const node = new THREE.Object3D();
  const frame = index.frames.get(screw.frameId);
  node.userData = { spec: frame, baseQuaternion: node.quaternion.clone() };
  const adapter = createMotionAdapter({ frameNodes: new Map([[screw.frameId, node]]) }, manifest);
  for (const delta of [0,0.25,1,2,4,travel/2,travel]) {
    adapter(null, 0, { [screw.frameId]: delta });
    assert.ok(Math.abs(rotationForTravel(screw,delta)-screw.baseAngleRad-2*Math.PI*delta/4)<1e-10);
    assert.ok(Math.abs(node.quaternion.length()-1)<1e-12);
    assert.equal(node.position.length(), 0); // adapter rotates only, generic frame translates
    assert.equal(node.scale.x*node.scale.y*node.scale.z, 1);
  }
  assert.throws(()=>rotationForTravel(screw, travel+0.01));
  assert.throws(()=>rotationForTravel(screw, -0.01));
  const cores = manifest.parts.filter(p=>p.exclusiveGroup === "nozzle");
  assert.equal(cores.length, 4);
  assert.equal(cores.filter(p=>p.instances[0].visible).length, 1);
  assert.equal(index.instances.get("body").parentFrameId, "assembly");
  assert.equal(index.instances.get("tee").parentFrameId, "assembly");
  const tee = manifest.teeReference;
  assert.equal(tee.revision,"y-tee-photo-v2-20261007");
  assert.equal(tee.print_target,false);
  assert.equal(tee.measured_socket_id,50.2);
  assert.equal(tee.vendor_nominal_socket_id,49.8); // preserve conflict; user measurement wins
  assert.equal(tee.vendor_nominal_length,128);
  assert.equal(tee.illustrative_main_length,tee.vendor_nominal_length);
  assert.equal(tee.illustrative_lip_od,tee.vendor_nominal_od);
  assert.equal(hash(await readFile(resolve(root,"cad/y-tee-preview-reference.scad"))),tee.source_sha256);
  const air = new THREE.Vector3(...tee.airflow_local);
  const branch = new THREE.Vector3(...tee.ball_outward);
  assert.ok(branch.dot(air)<0, "Ball inlet must lean back toward fan");
  const pose = index.frames.get("assembly").localTransform.rotation;
  assert.ok(branch.clone().applyEuler(new THREE.Euler(...pose)).z>0, "Ball inlet must be above main tube");
  const exported = await read(resolve(root, manifest.release.package, "verification/export.json"));
  const sourceHashes = exported.source_sha256;
  for (const [name, expected] of Object.entries(sourceHashes)) {
    assert.equal(hash(await readFile(resolve(root,"cad",name))), expected);
    assert.equal(hash(await readFile(resolve(preview,"source",name))), expected);
  }
  const hashes = new Set();
  for (const part of manifest.parts) {
    const bytes = await readFile(resolve(preview,part.file));
    assert.equal(hash(bytes),part.sha256);
    assert.ok(!hashes.has(part.sha256)); hashes.add(part.sha256);
    assert.ok(positionsFromStl(bytes).length > 0);
    if (part.id === "tee") checkTeeMesh(positionsFromStl(bytes),tee);
    assert.ok((await stat(resolve(preview,part.source.file))).isFile());
    if (part.role === "printed") {
      const delivery = exported.files.find(row=>row.sha256===part.sha256 && row.print_target);
      assert.ok(delivery, `${part.id} is not a current print STL`);
      assert.deepEqual(bytes, await readFile(resolve(root,manifest.release.package,delivery.file)));
    }
    assert.deepEqual(bytes,await readFile(resolve(root,"output/revision-review/fan-nozzle",part.file)));
    if (endpoint) {
      const response = await fetch(new URL(part.file, endpoint));
      assert.equal(response.status,200);
      assert.equal(hash(Buffer.from(await response.arrayBuffer())),part.sha256);
    }
    checks++;
  }
  if (endpoint) assert.deepEqual(await (await fetch(new URL(filename,endpoint))).json(),manifest);
  console.log(`PASS ${variant}: P4 / ${travel} mm; exact print meshes; Y upstream/upward inlet, 3 open sockets, terminal beads, no root flange`);
}
for (const name of ["app.mjs","assembly-scene.mjs","project-motion.mjs","index.html","styles.css","vendor/three.module.js"]) {
  const source = await readFile(resolve(root,"web/fan-nozzle",name));
  assert.deepEqual(source,await readFile(resolve(preview,name)));
  if (endpoint) assert.equal(hash(source),hash(Buffer.from(await (await fetch(new URL(name,endpoint))).arrayBuffer())));
}
console.log(`PASS ${checks} mesh references; deployed/source asset parity${endpoint ? "; LAN HTTP hashes verified" : ""}`);
