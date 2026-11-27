/** Explicit display contract for a nonphysical installation-space reference. */
export const ECLIP_SPACE_ID='feeder/cable-input-eclip-space';

export function displayContract(row){
  const d=row.display;
  if(d===undefined){
    if(row.id===ECLIP_SPACE_ID)throw new Error('E卡簧空间参考缺少显示约定');
    return null;
  }
  if(!d||Array.isArray(d)||d.kind!=='space-requirement'||row.role!=='reference'
    ||row.motion?.kind!=='fixed'||typeof d.default_visible!=='boolean'
    ||!/^#[0-9a-f]{6}$/i.test(d.color)||!Number.isFinite(d.opacity)
    ||d.opacity<=0||d.opacity>=1)throw new Error(`无效的空间参考显示约定：${row.id}`);
  return d;
}

export function defaultPartVisible(row){return displayContract(row)?.default_visible??true;}
export function partIsVisible(row,overrides){
  return overrides.has(row.id)?overrides.get(row.id):defaultPartVisible(row);
}
export function recordMaterialDisplay(row,{surface,shell,clip}){
  const d=displayContract(row);
  const opacity=d?.opacity??(row.id==='feeder/pc-reference'?.23:shell&&surface==='transparent'?.24:shell&&surface==='cutaway'?.65:1);
  return {opacity,transparent:opacity<1,depthWrite:opacity>=1,
    clippingPlanes:!d&&surface==='cutaway'&&shell?[clip]:[]};
}
