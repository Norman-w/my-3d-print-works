/**
 * Export shell outer envelope STL (mm) — visual reference / diff vs OpenSCAD.
 * PRINT PATH: OpenSCAD bezier_paddle_outer() (CSG union, watertight).
 * Live preview merges two closed meshes (not watertight); do not import that for booleans.
 */
import * as fs from 'node:fs';
import * as path from 'node:path';
import { fileURLToPath } from 'node:url';
import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { STLExporter } from 'three/examples/jsm/exporters/STLExporter.js';
import saved from '../src/data/userBezierProfiles.json';
import { defaultProfile, type BezierProfile } from '../src/lib/bezierProfile';
import {
  createLoftedHandleGeometry,
  createHandleFromFrontProfile,
  profileToClosedShape,
} from '../src/lib/paddleFromBezier';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '../..');
const OUT = path.join(ROOT, 'enclosure/stl/outer_envelope_three.stl');

/** Match enclosure/parameters.scad blade_core_t (mm). */
const SHELL_BLADE_T_MM = 6.0;
const JOIN_Y_MM = -78.5;
const MM = 0.01;
const STL_SCALE = 100;

function profilesFromJson(): {
  blade: BezierProfile;
  handle: BezierProfile;
  side: BezierProfile;
  handleBottom: BezierProfile;
} {
  const s = saved as Record<string, BezierProfile>;
  return {
    blade: s['blade-front'],
    handle: s['handle-front'],
    side: s['side'] ?? defaultProfile('side'),
    handleBottom: s['handle-bottom'] ?? defaultProfile('handle-bottom'),
  };
}

function createShellOuterGroup(profiles: ReturnType<typeof profilesFromJson>): THREE.Group {
  const group = new THREE.Group();
  const coreT = SHELL_BLADE_T_MM * MM;

  const woodShape = profileToClosedShape(profiles.blade, JOIN_Y_MM);
  const woodGeo = new THREE.ExtrudeGeometry(woodShape, {
    depth: coreT,
    bevelEnabled: false,
  });
  woodGeo.translate(0, 0, -coreT / 2);
  group.add(new THREE.Mesh(woodGeo));

  const handleGeo = profiles.handleBottom
    ? createLoftedHandleGeometry(profiles.handle, profiles.handleBottom, profiles.side, 56, 40)
    : createHandleFromFrontProfile(profiles.handle, 25, 56);
  group.add(new THREE.Mesh(handleGeo));

  return group;
}

function prepareForMerge(g: THREE.BufferGeometry): THREE.BufferGeometry {
  let geo = g.index ? g.toNonIndexed() : g.clone();
  geo.deleteAttribute('uv');
  geo.computeVertexNormals();
  return geo;
}

function main(): void {
  const profiles = profilesFromJson();
  const group = createShellOuterGroup(profiles);
  const geos: THREE.BufferGeometry[] = [];
  group.traverse(obj => {
    if (obj instanceof THREE.Mesh && obj.geometry) {
      geos.push(prepareForMerge(obj.geometry));
    }
  });
  if (geos.length === 0) {
    console.error('No geometry to export');
    process.exit(1);
  }

  const merged = mergeGeometries(geos, false);
  if (!merged) {
    console.error('mergeGeometries failed');
    process.exit(1);
  }
  merged.applyMatrix4(new THREE.Matrix4().makeScale(STL_SCALE, STL_SCALE, STL_SCALE));
  merged.computeBoundingBox();
  const bb = merged.boundingBox!;
  const size = new THREE.Vector3();
  bb.getSize(size);

  const mesh = new THREE.Mesh(merged);
  const stl = new STLExporter().parse(mesh, { binary: true }) as DataView;
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  fs.writeFileSync(OUT, Buffer.from(stl.buffer));

  console.log(`✓ ${OUT}`);
  console.log(
    `  bbox mm: X=${size.x.toFixed(1)} Y=${size.y.toFixed(1)} Z=${size.z.toFixed(1)} (same as Live outer)`,
  );
}

main();
