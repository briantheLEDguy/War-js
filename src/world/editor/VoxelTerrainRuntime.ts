import * as THREE from 'three';
import type {
  VoxelCell,
  VoxelMaterialId,
  VoxelTerrainChunk,
  WorldEditDocument,
} from '../../services/types';

export type VoxelBrushTool =
  | 'voxel_add'
  | 'voxel_subtract'
  | 'voxel_smooth'
  | 'voxel_flatten'
  | 'voxel_roughen'
  | 'paint_material'
  | 'fill_erase';

export interface VoxelBrushOptions {
  tool: VoxelBrushTool;
  x: number;
  y: number;
  z: number;
  radius: number;
  strength: number;
  material: VoxelMaterialId;
}

interface HeightSample {
  height: number;
  material: VoxelMaterialId;
}

interface VoxelMeshPayload {
  vertices: number[];
  colors: number[];
  indices: number[];
}

const CHUNK_SIZE = 16;
const VOXEL_SIZE = 1;
const MAX_VERTICAL_CELLS = 31;

export class VoxelTerrainRuntime {
  private group = new THREE.Group();
  private mesh: THREE.Mesh | null = null;
  private worker: Worker | null = null;
  private jobId = 0;
  private material = new THREE.MeshStandardMaterial({
    roughness: 0.92,
    metalness: 0,
    side: THREE.DoubleSide,
    vertexColors: true,
  });

  constructor(private scene: THREE.Scene) {
    this.group.name = 'world-edit-voxel-terrain';
    this.scene.add(this.group);
    if (typeof Worker !== 'undefined') {
      try {
        this.worker = new Worker(new URL('./voxelMesher.worker.ts', import.meta.url), { type: 'module' });
        this.worker.onmessage = (event: MessageEvent<{ jobId: number; payload: VoxelMeshPayload | null }>) => {
          if (event.data.jobId !== this.jobId) return;
          this.replaceMesh(event.data.payload ? this.createMeshFromPayload(event.data.payload) : null);
        };
      } catch (err) {
        console.warn('[VoxelTerrainRuntime] worker unavailable, using synchronous meshing.', err);
        this.worker = null;
      }
    }
  }

  get object(): THREE.Object3D {
    return this.group;
  }

  load(document: WorldEditDocument | null): void {
    this.jobId += 1;
    if (!document || document.voxelChunks.length === 0) {
      this.replaceMesh(null);
      return;
    }
    if (this.worker) {
      this.worker.postMessage({
        jobId: this.jobId,
        chunks: document.voxelChunks,
        palette: document.palette,
      });
      return;
    }
    this.replaceMesh(buildSmoothVoxelMesh(document.voxelChunks, document));
  }

  clear(): void {
    if (this.mesh) {
      this.group.remove(this.mesh);
      this.mesh.geometry.dispose();
      this.mesh = null;
    }
  }

  dispose(): void {
    this.clear();
    this.scene.remove(this.group);
    this.worker?.terminate();
    this.worker = null;
    this.material.dispose();
  }

  private createMeshFromPayload(payload: VoxelMeshPayload): THREE.Mesh | null {
    if (payload.vertices.length === 0 || payload.indices.length === 0) return null;
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.Float32BufferAttribute(payload.vertices, 3));
    geometry.setAttribute('color', new THREE.Float32BufferAttribute(payload.colors, 3));
    geometry.setIndex(payload.indices);
    geometry.computeVertexNormals();
    return new THREE.Mesh(geometry);
  }

  private replaceMesh(mesh: THREE.Mesh | null): void {
    this.clear();
    if (!mesh) return;
    this.prepareMesh(mesh);
    this.mesh = mesh;
  }

  private prepareMesh(mesh: THREE.Mesh): void {
    mesh.material = this.material;
    mesh.receiveShadow = true;
    mesh.castShadow = true;
    mesh.userData.worldEditVoxelTerrain = true;
    this.group.add(mesh);
  }
}

export function applyVoxelBrushToDocument(
  document: WorldEditDocument,
  brush: VoxelBrushOptions,
): WorldEditDocument {
  const next: WorldEditDocument = JSON.parse(JSON.stringify(document)) as WorldEditDocument;
  const chunks = new Map(next.voxelChunks.map((chunk) => [chunk.key, chunk]));
  const radius = Math.max(0.5, brush.radius);
  const strength = Math.max(0.05, Math.min(1, brush.strength));
  const cellRadius = Math.max(1, Math.ceil(radius / VOXEL_SIZE));
  const centerX = Math.floor(brush.x / VOXEL_SIZE);
  const centerZ = Math.floor(brush.z / VOXEL_SIZE);
  const targetY = Math.max(0, Math.min(MAX_VERTICAL_CELLS, Math.round(brush.y / VOXEL_SIZE)));

  const heightCache = buildHeightMap(next.voxelChunks);
  const changedColumns = new Set<string>();

  for (let gx = centerX - cellRadius; gx <= centerX + cellRadius; gx += 1) {
    for (let gz = centerZ - cellRadius; gz <= centerZ + cellRadius; gz += 1) {
      const wx = (gx + 0.5) * VOXEL_SIZE;
      const wz = (gz + 0.5) * VOXEL_SIZE;
      const dist = Math.hypot(wx - brush.x, wz - brush.z);
      if (dist > radius) continue;

      const falloff = Math.max(0, 1 - dist / radius);
      const steps = Math.max(1, Math.round((1 + strength * 3) * falloff));
      const key = columnKey(gx, gz);
      const current = heightCache.get(key)?.height ?? 0;
      let desired = current;

      if (brush.tool === 'voxel_add') desired = current + steps;
      if (brush.tool === 'voxel_subtract' || brush.tool === 'fill_erase') desired = current - steps;
      if (brush.tool === 'voxel_flatten') {
        desired = Math.round(lerp(current, targetY, Math.max(0.15, strength * falloff)));
      }
      if (brush.tool === 'voxel_smooth') {
        desired = Math.round(lerp(current, averageNeighborHeight(heightCache, gx, gz), strength * falloff));
      }
      if (brush.tool === 'voxel_roughen') {
        const noise = deterministicNoise(gx, gz, next.updatedAt) > 0.5 ? 1 : -1;
        desired = current + noise * steps;
      }

      desired = Math.max(0, Math.min(MAX_VERTICAL_CELLS, desired));

      if (brush.tool === 'paint_material') {
        const top = getColumnTop(chunks, gx, gz);
        if (top < 0) {
          desired = Math.max(1, targetY);
          setColumnHeight(chunks, gx, gz, desired, brush.material);
        } else {
          desired = current > 0 ? current : top + 1;
          setColumnMaterial(chunks, gx, gz, brush.material);
        }
      } else {
        setColumnHeight(chunks, gx, gz, desired, brush.material);
      }
      changedColumns.add(key);
      heightCache.set(key, { height: desired, material: brush.material });
    }
  }

  if (changedColumns.size === 0) return next;
  next.updatedAt = Date.now();
  next.voxelChunks = Array.from(chunks.values())
    .map((chunk) => ({ ...chunk, updatedAt: next.updatedAt }))
    .filter((chunk) => Object.keys(chunk.cells).length > 0);
  return next;
}

export function getVoxelRaycastTargets(runtime: VoxelTerrainRuntime | null): THREE.Object3D[] {
  return runtime ? [runtime.object] : [];
}

function buildSmoothVoxelMesh(
  chunks: VoxelTerrainChunk[],
  document: WorldEditDocument,
): THREE.Mesh | null {
  const heights = buildHeightMap(chunks);
  if (heights.size === 0) return null;

  const vertices: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];
  const palette = new Map(document.palette.materials.map((material) => [material.id, material.color]));
  const color = new THREE.Color();
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

    vertices.push(x0, h00, z0, x1, h10, z0, x1, h11, z1, x0, h01, z1);
    color.set(palette.get(center.material) ?? '#77736a');
    for (let i = 0; i < 4; i += 1) colors.push(color.r, color.g, color.b);
    indices.push(vertexIndex, vertexIndex + 1, vertexIndex + 2, vertexIndex, vertexIndex + 2, vertexIndex + 3);
    vertexIndex += 4;

  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(vertices, 3));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();
  return new THREE.Mesh(geometry);
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

function setColumnHeight(
  chunks: Map<string, VoxelTerrainChunk>,
  gx: number,
  gz: number,
  height: number,
  material: VoxelMaterialId,
): void {
  const currentTop = getColumnTop(chunks, gx, gz);
  const target = Math.round(height);
  if (target <= 0) {
    for (let y = 0; y <= currentTop; y += 1) deleteCell(chunks, gx, y, gz);
    return;
  }

  for (let y = 0; y < target; y += 1) setCell(chunks, gx, y, gz, { density: 1, material });
  for (let y = target; y <= currentTop; y += 1) deleteCell(chunks, gx, y, gz);
}

function setColumnMaterial(
  chunks: Map<string, VoxelTerrainChunk>,
  gx: number,
  gz: number,
  material: VoxelMaterialId,
): void {
  const top = getColumnTop(chunks, gx, gz);
  if (top < 0) return;
  setCell(chunks, gx, top, gz, { density: 1, material });
}

function getColumnTop(chunks: Map<string, VoxelTerrainChunk>, gx: number, gz: number): number {
  let top = -1;
  for (const chunk of chunks.values()) {
    const originX = Math.round(chunk.origin.x / chunk.voxelSize);
    const originZ = Math.round(chunk.origin.z / chunk.voxelSize);
    const lx = gx - originX;
    const lz = gz - originZ;
    if (lx < 0 || lx >= chunk.size || lz < 0 || lz >= chunk.size) continue;
    for (let y = 0; y < chunk.size; y += 1) {
      const cell = chunk.cells[cellKey(lx, y, lz)];
      if (cell?.density > 0) top = Math.max(top, y + Math.round(chunk.origin.y / chunk.voxelSize));
    }
  }
  return top;
}

function setCell(
  chunks: Map<string, VoxelTerrainChunk>,
  gx: number,
  gy: number,
  gz: number,
  cell: VoxelCell,
): void {
  const chunk = ensureChunk(chunks, gx, gy, gz);
  const local = toLocalCell(chunk, gx, gy, gz);
  chunk.cells[cellKey(local.x, local.y, local.z)] = cell;
}

function deleteCell(chunks: Map<string, VoxelTerrainChunk>, gx: number, gy: number, gz: number): void {
  const key = chunkKeyForCell(gx, gy, gz);
  const chunk = chunks.get(key);
  if (!chunk) return;
  const local = toLocalCell(chunk, gx, gy, gz);
  delete chunk.cells[cellKey(local.x, local.y, local.z)];
}

function ensureChunk(
  chunks: Map<string, VoxelTerrainChunk>,
  gx: number,
  gy: number,
  gz: number,
): VoxelTerrainChunk {
  const key = chunkKeyForCell(gx, gy, gz);
  const existing = chunks.get(key);
  if (existing) return existing;
  const ox = Math.floor(gx / CHUNK_SIZE) * CHUNK_SIZE * VOXEL_SIZE;
  const oy = Math.floor(gy / CHUNK_SIZE) * CHUNK_SIZE * VOXEL_SIZE;
  const oz = Math.floor(gz / CHUNK_SIZE) * CHUNK_SIZE * VOXEL_SIZE;
  const chunk: VoxelTerrainChunk = {
    key,
    origin: { x: ox, y: oy, z: oz },
    size: CHUNK_SIZE,
    voxelSize: VOXEL_SIZE,
    cells: {},
    updatedAt: Date.now(),
  };
  chunks.set(key, chunk);
  return chunk;
}

function toLocalCell(chunk: VoxelTerrainChunk, gx: number, gy: number, gz: number): { x: number; y: number; z: number } {
  const ox = Math.round(chunk.origin.x / chunk.voxelSize);
  const oy = Math.round(chunk.origin.y / chunk.voxelSize);
  const oz = Math.round(chunk.origin.z / chunk.voxelSize);
  return {
    x: positiveMod(gx - ox, chunk.size),
    y: positiveMod(gy - oy, chunk.size),
    z: positiveMod(gz - oz, chunk.size),
  };
}

function chunkKeyForCell(gx: number, gy: number, gz: number): string {
  const cx = Math.floor(gx / CHUNK_SIZE);
  const cy = Math.floor(gy / CHUNK_SIZE);
  const cz = Math.floor(gz / CHUNK_SIZE);
  return `${cx}:${cy}:${cz}`;
}

function cellKey(x: number, y: number, z: number): string {
  return `${x}:${y}:${z}`;
}

function columnKey(gx: number, gz: number): string {
  return `${gx}:${gz}`;
}

function parseColumnKey(key: string): [number, number] {
  const [x, z] = key.split(':').map((part) => Number.parseInt(part, 10));
  return [x, z];
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

function averageNeighborHeight(heights: Map<string, HeightSample>, gx: number, gz: number): number {
  let total = 0;
  let count = 0;
  for (let dx = -1; dx <= 1; dx += 1) {
    for (let dz = -1; dz <= 1; dz += 1) {
      const sample = heights.get(columnKey(gx + dx, gz + dz));
      total += sample?.height ?? 0;
      count += 1;
    }
  }
  return total / count;
}

function deterministicNoise(x: number, z: number, salt: number): number {
  let h = Math.imul(x, 374761393) ^ Math.imul(z, 668265263) ^ salt;
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
}

function positiveMod(value: number, modulus: number): number {
  return ((value % modulus) + modulus) % modulus;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * Math.max(0, Math.min(1, t));
}
