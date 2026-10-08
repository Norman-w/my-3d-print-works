/** Geometry revisions can move the safe starting pose without erasing shared UI state. */
export function motionStateForManifest(manifest, saved = {}) {
  const version = manifest.ui?.motionStateVersion;
  if (!version || saved.motionStateVersion === version) return { ...saved };
  // Keep nozzle choice. Old numeric travel/stage belongs to a different shell.
  const { stage, travel, ...rest } = saved;
  return { ...rest, motionStateVersion: version };
}
