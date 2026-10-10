/** Optional absolute landform raster. Source-derived/licensed samples stay in private content. */
export interface TerrainSurface {
  bounds: { minX: number; maxX: number; minZ: number; maxZ: number };
  segmentsX: number;
  segmentsZ: number;
  /** Row-major Z/X vertex elevations in metres; this replaces the underlying field, not route grading. */
  samples: number[];
  /** Blend back to the original field at the raster boundary, in metres. */
  edgeFade: number;
}

export function validateTerrainSurface(surface: TerrainSurface): void {
  const b=surface.bounds;
  if (!b || ![b.minX,b.maxX,b.minZ,b.maxZ].every(v=>Number.isFinite(v)&&Math.abs(v)<=10000)
    || b.minX>=b.maxX || b.minZ>=b.maxZ
    || ![surface.segmentsX,surface.segmentsZ].every(v=>Number.isInteger(v)&&v>=1&&v<=512)
    || !Array.isArray(surface.samples) || surface.samples.length!==(surface.segmentsX+1)*(surface.segmentsZ+1)
    || !Number.isFinite(surface.edgeFade) || surface.edgeFade<1 || surface.edgeFade>Math.min(b.maxX-b.minX,b.maxZ-b.minZ)/2)
    throw new Error('Invalid bounded terrain surface');
  // Iteration visits sparse holes, unlike Array.some; every admitted vertex must exist.
  for (const v of surface.samples) if (!Number.isFinite(v)||v < -100||v>350) throw new Error('Invalid bounded terrain surface samples');
}

/** Validate once at admission. Both authority and terrain export evaluate this same absolute field. */
export function terrainSurfaceHeight(surface: TerrainSurface,x: number,z: number,fallback: number): number {
  const b=surface.bounds;
  if (!Number.isFinite(x)||!Number.isFinite(z)||x<=b.minX||x>=b.maxX||z<=b.minZ||z>=b.maxZ) return fallback;
  const fx=(x-b.minX)/(b.maxX-b.minX)*surface.segmentsX,fz=(z-b.minZ)/(b.maxZ-b.minZ)*surface.segmentsZ;
  const ix=Math.min(surface.segmentsX-1,Math.floor(fx)),iz=Math.min(surface.segmentsZ-1,Math.floor(fz)),tx=fx-ix,tz=fz-iz;
  const at=(dx:number,dz:number)=>surface.samples[(iz+dz)*(surface.segmentsX+1)+ix+dx];
  const h=(at(0,0)*(1-tx)+at(1,0)*tx)*(1-tz)+(at(0,1)*(1-tx)+at(1,1)*tx)*tz;
  const t=Math.min(1,Math.min(x-b.minX,b.maxX-x,z-b.minZ,b.maxZ-z)/surface.edgeFade);
  return fallback+(h-fallback)*t*t*(3-2*t);
}
