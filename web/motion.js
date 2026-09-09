/* Same millimetre coordinates and negative-X rotation as lid_at() in SCAD.
 * Pivot comes from /api/model, derived from the authoritative SCAD parameters. */
(function (root) {
  "use strict";
  const pivot = [0, 0, 0];
  let configured = false;
  function configure(value) {
    if (!Array.isArray(value) || value.length !== 3 || !value.every(Number.isFinite)) throw new Error("缺少有效的 CAD 转轴参数");
    pivot.splice(0, 3, ...value);
    configured = true;
  }
  const maxAngle = 100;
  function rotatePoint(point, degrees) {
    if (!configured) throw new Error("尚未加载 CAD 转轴参数");
    const a = -degrees * Math.PI / 180;
    const c = Math.cos(a), s = Math.sin(a);
    const y = point[1] - pivot[1], z = point[2] - pivot[2];
    return [point[0], pivot[1] + c * y - s * z, pivot[2] + s * y + c * z];
  }
  function frameFor(base, lid) {
    const min = [...base.min], max = [...base.max];
    // Fixed framing for the whole sweep: no camera pumping as the lid moves.
    for (let a = 0; a <= maxAngle; a += 1) {
      for (let corner = 0; corner < 8; corner += 1) {
        const p = rotatePoint(lid.min.map((v, i) => corner & (1 << i) ? lid.max[i] : v), a);
        p.forEach((v, i) => { min[i] = Math.min(min[i], v); max[i] = Math.max(max[i], v); });
      }
    }
    const size = max.map((v, i) => v - min[i]);
    return { center: min.map((v, i) => (v + max[i]) / 2), maxDimension: Math.max(...size), size };
  }
  function partMatrix(mesh, frame, degrees) {
    const a = -degrees * Math.PI / 180;
    const c = Math.cos(a), s = Math.sin(a);
    const scale = mesh.maxDimension / frame.maxDimension;
    const center = rotatePoint(mesh.center, degrees);
    const t = center.map((v, i) => (v - frame.center[i]) * 2 / frame.maxDimension);
    // Undo this STL's own normalization, rotate in shared CAD coordinates,
    // then normalize into the assembly frame. Never center each half separately.
    return new Float32Array([scale, 0, 0, 0, 0, c * scale, s * scale, 0,
      0, -s * scale, c * scale, 0, ...t, 1]);
  }
  function angleAt(phase) { return maxAngle * (1 - Math.cos(phase)) / 2; }
  function phaseAt(angle) { return Math.acos(1 - 2 * Math.max(0, Math.min(maxAngle, angle)) / maxAngle); }
  const api = { pivot, maxAngle, configure, rotatePoint, frameFor, partMatrix, angleAt, phaseAt };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.BoxMotion = api;
})(globalThis);
