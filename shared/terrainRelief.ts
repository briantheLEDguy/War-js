/** Compact metre-space height detail. Derived licensed samples remain in private content. */
export interface TerrainRelief {
  bounds: { minX: number; maxX: number; minZ: number; maxZ: number };
  segmentsX: number;
  segmentsZ: number;
  /** Row-major Z/X vertex heights in metres; rectangular grids are supported. */
  samples: number[];
  edgeFade: number;
  /** Suppress detail in lowlands while retaining the authored watershed. */
  ridgeMaskHeight: number;
}

export function validateTerrainRelief(relief: TerrainRelief): void {
  const b = relief.bounds;
  if (!b || ![b.minX,b.maxX,b.minZ,b.maxZ].every(n => Number.isFinite(n) && Math.abs(n) <= 10000)
    || b.minX >= b.maxX || b.minZ >= b.maxZ
    || ![relief.segmentsX,relief.segmentsZ].every(n => Number.isInteger(n) && n >= 1 && n <= 512)
    || !Array.isArray(relief.samples) || relief.samples.length !== (relief.segmentsX+1)*(relief.segmentsZ+1)
    || !Number.isFinite(relief.edgeFade) || relief.edgeFade < 1 || relief.edgeFade > Math.min(b.maxX-b.minX,b.maxZ-b.minZ)/2
    || !Number.isFinite(relief.ridgeMaskHeight) || relief.ridgeMaskHeight < 10 || relief.ridgeMaskHeight > 150)
    throw new Error('Invalid bounded terrain relief');
  for (const n of relief.samples) if (!Number.isFinite(n) || Math.abs(n) > 40) throw new Error('Invalid bounded terrain relief samples');
}

/** Inputs are validated once when a terrain revision is admitted, not per movement sample. */
export function sampleTerrainRelief(relief: TerrainRelief, x: number, z: number): number {
  const b = relief.bounds;
  if (!Number.isFinite(x) || !Number.isFinite(z) || x <= b.minX || x >= b.maxX || z <= b.minZ || z >= b.maxZ) return 0;
  const fx=(x-b.minX)/(b.maxX-b.minX)*relief.segmentsX, fz=(z-b.minZ)/(b.maxZ-b.minZ)*relief.segmentsZ;
  const ix=Math.min(relief.segmentsX-1,Math.floor(fx)), iz=Math.min(relief.segmentsZ-1,Math.floor(fz)), tx=fx-ix,tz=fz-iz;
  const at=(dx:number,dz:number)=>relief.samples[(iz+dz)*(relief.segmentsX+1)+ix+dx];
  const h=(at(0,0)*(1-tx)+at(1,0)*tx)*(1-tz)+(at(0,1)*(1-tx)+at(1,1)*tx)*tz;
  const fade=Math.min(1,Math.min(x-b.minX,b.maxX-x,z-b.minZ,b.maxZ-z)/relief.edgeFade);
  return h*fade*fade*(3-2*fade);
}
