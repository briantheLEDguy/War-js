import type { VoxelMaterialPalette, VoxelTerrainChunk } from '../../services/types';

interface WorkerRequest {
  jobId: number;
  chunks: VoxelTerrainChunk[];
  palette: VoxelMaterialPalette;
}

interface HeightSample {
  height: number;
  material: string;
}

const VOXEL_SIZE = 1;

self.onmessage = (event: MessageEvent<WorkerRequest>) => {
  const payload = buildSmoothVoxelMeshPayload(event.data.chunks, event.data.palette);
  self.postMessage({ jobId: event.data.jobId, payload });
};

function buildSmoothVoxelMeshPayload(
  chunks: VoxelTerrainChunk[],
  palette: VoxelMaterialPalette,
): { vertices: number[]; colors: number[]; indices: number[] } | null {
  const heights = buildHeightMap(chunks);
  if (heights.size === 0) return null;

  const vertices: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];
  const paletteColors = new Map(palette.materials.map((material) => [material.id, hexToRgb(material.color)]));
  let vertexIndex = 0;

  for (const key of heights.keys()) {
    const [gx, gz] = parseColumnKey(key);
    const center = heights.get(key)!;
    const x0 = gx * VOXEL_SIZE;
    const x1 = x0 + VOXEL_SIZE;
    const z0 = gz * VOXEL_SIZE;
    const z1 = z0 + VOXEL_SIZE;
    const h00 = cornerHeight(heights, gx, gz);
    const h10 = cornerHeight(heights, gx + 1, gz);
    const h11 = cornerHeight(heights, gx + 1, gz + 1);
    const h01 = cornerHeight(heights, gx, gz + 1);
    const rgb = paletteColors.get(center.material) ?? hexToRgb('#77736a');

    vertices.push(x0, h00, z0, x1, h10, z0, x1, h11, z1, x0, h01, z1);
    for (let i = 0; i < 4; i += 1) colors.push(rgb.r, rgb.g, rgb.b);
    indices.push(vertexIndex, vertexIndex + 1, vertexIndex + 2, vertexIndex, vertexIndex + 2, vertexIndex + 3);
    vertexIndex += 4;
  }

  return { vertices, colors, indices };
}

function buildHeightMap(chunks: VoxelTerrainChunk[]): Map<string, HeightSample> {
  const heights = new Map<string, HeightSample>();
  for (const chunk of chunks) {
    for (const [cellKey, cell] of Object.entries(chunk.cells)) {
      if (cell.density <= 0) continue;
      const [lx, ly, lz] = cellKey.split(':').map((part) => Number.parseInt(part, 10));
      const gx = Math.round(chunk.origin.x / chunk.voxelSize) + lx;
      const gz = Math.round(chunk.origin.z / chunk.voxelSize) + lz;
      const height = chunk.origin.y + (ly + cell.density) * chunk.voxelSize;
      const key = columnKey(gx, gz);
      const existing = heights.get(key);
      if (!existing || height >= existing.height) heights.set(key, { height, material: cell.material });
    }
  }
  return heights;
}

function cornerHeight(heights: Map<string, HeightSample>, gx: number, gz: number): number {
  let total = 0;
  let count = 0;
  for (const dx of [-1, 0]) {
    for (const dz of [-1, 0]) {
      const sample = heights.get(columnKey(gx + dx, gz + dz));
      if (!sample) continue;
      total += sample.height;
      count += 1;
    }
  }
  return count > 0 ? total / count : 0;
}

function columnKey(gx: number, gz: number): string {
  return `${gx}:${gz}`;
}

function parseColumnKey(key: string): [number, number] {
  const [x, z] = key.split(':').map((part) => Number.parseInt(part, 10));
  return [x, z];
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const clean = hex.replace('#', '');
  const value = Number.parseInt(clean.length === 3
    ? clean.split('').map((part) => `${part}${part}`).join('')
    : clean, 16);
  return {
    r: ((value >> 16) & 255) / 255,
    g: ((value >> 8) & 255) / 255,
    b: (value & 255) / 255,
  };
}
