const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { test } = require('node:test');
const motion = require('../web/motion.js');
const root = path.resolve(__dirname, '..');
const source = fs.readFileSync(path.join(root, 'orthokeratology_lens_cleaning_kit_box.scad'), 'utf8');
const value = name => Number(source.match(new RegExp(`^${name} = ([\\d.]+);`, 'm'))[1]);
const width = value('inner_width') + 2 * value('wall') + value('front_service') + value('rear_service');
motion.configure([0, width - value('axis_inset'), value('base_floor') + value('inner_height_total') / 2]);
function load(name) {
  const bytes = fs.readFileSync(path.join(root, 'output/3d-print', `orthokeratology_lens_cleaning_kit_box_${name}.stl`));
  const vertices = [];
  if (bytes.length >= 84 && 84 + bytes.readUInt32LE(80) * 50 === bytes.length) {
    for (let offset = 84; offset < bytes.length; offset += 50) {
      for (let v = 0; v < 3; v++) vertices.push([0, 1, 2].map(a => bytes.readFloatLE(offset + 12 + v * 12 + a * 4)));
    }
  } else {
    for (const m of bytes.toString().matchAll(/vertex\s+([-+\d.eE]+)\s+([-+\d.eE]+)\s+([-+\d.eE]+)/g)) vertices.push(m.slice(1).map(Number));
  }
  assert(vertices.length > 0);
  return { ...bounds(vertices), vertices };
}
function bounds(vertices) {
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  vertices.forEach(p => p.forEach((v, i) => { min[i] = Math.min(min[i], v); max[i] = Math.max(max[i], v); }));
  const size = max.map((v, i) => v - min[i]);
  return { min, max, center: min.map((v, i) => (v + max[i]) / 2), maxDimension: Math.max(...size) };
}
function close(a, b, tolerance = .001) {
  a.forEach((v, i) => assert(Math.abs(v - b[i]) < tolerance, `${v} != ${b[i]}`));
}
const base = load('base'), lid = load('lid');
test('hinge axis matches the authoritative SCAD dimensions', () => {
  assert.match(source, /axis_y = outer_width-axis_inset;/);
  assert.match(source, /axis_z = half_height;/);
  close(motion.pivot, [0, width - value('axis_inset'), value('base_floor') + value('inner_height_total') / 2]);
});
test('0 and 90 degree assembly bounds match OpenSCAD reference STLs', () => {
  for (const [angle, name] of [[0, 'closed_preview'], [90, 'open90']]) {
    const actual = bounds([...base.vertices, ...lid.vertices.map(p => motion.rotatePoint(p, angle))]);
    const expected = load(name);
    close(actual.min, expected.min); close(actual.max, expected.max);
  }
});
test('shared-coordinate GPU transform preserves the hinge and agrees with CAD rotation', () => {
  const frame = motion.frameFor(base, lid);
  for (const angle of [0, 1, 45, 90, 100]) {
    close(motion.rotatePoint(motion.pivot, angle), motion.pivot);
    const matrix = motion.partMatrix(lid, frame, angle);
    for (const p of lid.vertices) {
      const normalized = p.map((v, i) => (v - lid.center[i]) * 2 / lid.maxDimension);
      const transformed = [0, 1, 2].map(i => matrix[i] * normalized[0] + matrix[4 + i] * normalized[1] + matrix[8 + i] * normalized[2] + matrix[12 + i]);
      const expected = motion.rotatePoint(p, angle).map((v, i) => (v - frame.center[i]) * 2 / frame.maxDimension);
      close(transformed, expected, .00001);
    }
  }
});
test('loop reaches both limits; scrubbing resumes without an angle jump', () => {
  close([motion.angleAt(0), motion.angleAt(Math.PI), motion.angleAt(2 * Math.PI)], [0, 100, 0]);
  for (let a = 0; a <= 100; a++) close([motion.angleAt(motion.phaseAt(a))], [a]);
});
