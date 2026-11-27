// Pure kinematics: pitch stays fixed. Travel is gained by more engaged turns.
export function rotationForTravel(screw, travel) {
  if (!(screw.pitchMm > 0) || !Number.isFinite(travel) || travel < 0 || travel > screw.travelMm) {
    throw new Error("Screw travel outside evaluated mechanical contract");
  }
  return screw.baseAngleRad + travel * 2 * Math.PI / screw.pitchMm;
}

export function createMotionAdapter(runtime, manifest) {
  const screw = manifest.screwMotion;
  const node = runtime.frameNodes.get(screw.frameId);
  if (!node || node.userData.spec.kind !== "prismatic") throw new Error("Missing screw translation frame");
  return (_runtime, _time, values) => {
    // Translation is already applied by AssemblyScene. Add rotation to the
    // same local frame without moving the fixed body, fan or tee.
    node.quaternion.setFromAxisAngle({ x: 0, y: 0, z: 1 },
      rotationForTravel(screw, values[screw.frameId] ?? 0)).multiply(node.userData.baseQuaternion);
  };
}
