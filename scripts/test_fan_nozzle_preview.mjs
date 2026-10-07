import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import { createHash } from "node:crypto";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { validateManifest } from "../web/fan-nozzle/manifest-core.mjs";
import { positionsFromStl } from "../web/fan-nozzle/connected-islands.mjs";
import { rotationForTravel, createMotionAdapter } from "../web/fan-nozzle/project-motion.mjs";
import * as THREE from "../web/fan-nozzle/vendor/three.module.js";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const preview = resolve(root, "output/fan-nozzle-preview");
const hash = bytes => createHash("sha256").update(bytes).digest("hex");
const read = async path => JSON.parse(await readFile(path, "utf8"));
const endpoint = process.argv[2];
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
  console.log(`PASS ${variant}: P4 / ${travel} mm; helical kinematics, 5 exact print meshes, 2 references, fixed host, unit scale`);
}
for (const name of ["app.mjs","assembly-scene.mjs","project-motion.mjs","index.html","styles.css","vendor/three.module.js"]) {
  const source = await readFile(resolve(root,"web/fan-nozzle",name));
  assert.deepEqual(source,await readFile(resolve(preview,name)));
  if (endpoint) assert.equal(hash(source),hash(Buffer.from(await (await fetch(new URL(name,endpoint))).arrayBuffer())));
}
console.log(`PASS ${checks} mesh references; deployed/source asset parity${endpoint ? "; LAN HTTP hashes verified" : ""}`);
