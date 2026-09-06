import * as THREE from 'three';
import type { CameraCollider } from './Camera';

const TERRAIN_PADDING = 0.45;
const TERRAIN_STEP = 0.1;
const raycaster = new THREE.Raycaster();
const hits: THREE.Intersection[] = [];
const meshBox = new THREE.Box3();
const sweepBox = new THREE.Box3();
const staticBounds = new WeakMap<THREE.Object3D, { matrix: THREE.Matrix4; bounds: THREE.Box3 }>();

/** Shorten the orbit along its requested direction; never push it sideways or
 * raise it into a roof after resolving a wall. Zoom preference stays untouched. */
export function resolveCameraCollision(
  focus: THREE.Vector3,
  desired: THREE.Vector3,
  colliders: CameraCollider[] = [],
  terrainHeightAt?: (x: number, z: number) => number,
  objects: THREE.Object3D[] = [],
  padding = 0.35,
): THREE.Vector3 {
  const direction = desired.clone().sub(focus);
  const distance = direction.length();
  if (distance < 0.00001) return focus.clone();
  direction.divideScalar(distance);
  let safeDistance = distance;
  for (const collider of colliders) {
    const hit = intersectCollider(focus, direction, distance, collider, padding);
    if (hit !== null) safeDistance = Math.min(safeDistance, Math.max(0, hit - 0.01));
  }

  if (terrainHeightAt) {
    const probe = focus.clone();
    const clearance = (d: number) => {
      probe.copy(focus).addScaledVector(direction, d);
      return probe.y - terrainHeightAt(probe.x, probe.z) - Math.max(TERRAIN_PADDING, padding);
    };
    // Sample the whole segment: a hill can obstruct an otherwise clear endpoint.
    const steps = Math.max(1, Math.ceil(safeDistance / TERRAIN_STEP));
    let previous = 0;
    for (let step = 0; step <= steps; step++) {
      const d = safeDistance * step / steps;
      if (clearance(d) < 0) {
        let blocked = d;
        for (let i = 0; i < 12; i++) {
          const mid = (previous + blocked) / 2;
          if (clearance(mid) >= 0) previous = mid;
          else blocked = mid;
        }
        safeDistance = previous;
        break;
      }
      previous = d;
    }
  }
  if (objects.length) {
    safeDistance = Math.min(safeDistance, meshCollisionDistance(focus, direction, safeDistance, objects, padding));
  }
  return focus.clone().addScaledVector(direction, safeDistance);
}

function intersectCollider(
  start: THREE.Vector3, direction: THREE.Vector3, distance: number,
  collider: CameraCollider, padding: number,
): number | null {
  const cos = Math.cos(collider.rotY);
  const sin = Math.sin(collider.rotY);
  const x = start.x - collider.x;
  const z = start.z - collider.z;
  const origins = [x * cos + z * sin, start.y, -x * sin + z * cos];
  const deltas = [direction.x * cos + direction.z * sin, direction.y, -direction.x * sin + direction.z * cos];
  const mins = [-collider.width / 2 - padding, (collider.minY ?? -Infinity) - padding, -collider.depth / 2 - padding];
  const maxs = [collider.width / 2 + padding, (collider.maxY ?? Infinity) + padding, collider.depth / 2 + padding];
  let near = 0;
  let far = distance;
  for (let axis = 0; axis < 3; axis++) {
    if (Math.abs(deltas[axis]) < 0.000001) {
      if (origins[axis] < mins[axis] || origins[axis] > maxs[axis]) return null;
      continue;
    }
    let a = (mins[axis] - origins[axis]) / deltas[axis];
    let b = (maxs[axis] - origins[axis]) / deltas[axis];
    if (a > b) [a, b] = [b, a];
    near = Math.max(near, a);
    far = Math.min(far, b);
    if (near > far) return null;
  }
  return near;
}

function meshCollisionDistance(
  focus: THREE.Vector3, direction: THREE.Vector3, distance: number,
  objects: THREE.Object3D[], padding: number,
): number {
  if (distance <= 0) return 0;
  const end = focus.clone().addScaledVector(direction, distance);
  sweepBox.setFromPoints([focus, end]).expandByScalar(padding);
  const candidates: THREE.Mesh[] = [];
  const visit = (object: THREE.Object3D) => {
    // Use original high-detail geometry even when instancing/LOD hides it.
    if (object instanceof THREE.LOD) {
      if (object.levels[0]) visit(object.levels[0].object);
      return;
    }
    if (object instanceof THREE.Mesh) {
      if (!object.geometry.boundingBox) object.geometry.computeBoundingBox();
      if (object.geometry.boundingBox) {
        meshBox.copy(object.geometry.boundingBox).applyMatrix4(object.matrixWorld);
        if (meshBox.intersectsBox(sweepBox)) candidates.push(object);
      }
    }
    for (const child of object.children) visit(child);
  };
  for (const object of objects) {
    if (object.userData.cameraStaticGeometry === true) {
      object.updateWorldMatrix(true, false);
      let cached = staticBounds.get(object);
      if (!cached || !cached.matrix.equals(object.matrixWorld)) {
        object.updateWorldMatrix(false, true);
        cached = { matrix: object.matrixWorld.clone(), bounds: new THREE.Box3().setFromObject(object) };
        staticBounds.set(object, cached);
      }
      // Keep precise mesh/near-plane tests for nearby architecture only.
      if (!cached.bounds.intersectsBox(sweepBox)) continue;
    }
    object.updateWorldMatrix(true, true);
    visit(object);
  }
  if (candidates.length === 0) return distance;
  const right = new THREE.Vector3().crossVectors(direction, new THREE.Vector3(0, 1, 0));
  if (right.lengthSq() < 0.000001) right.set(1, 0, 0);
  right.normalize();
  const up = new THREE.Vector3().crossVectors(right, direction).normalize();
  const origin = new THREE.Vector3();
  const reverse = direction.clone().negate();
  let nearest = distance;
  // Center plus perimeter probes protect the near plane at grazing angles.
  for (const [x, y] of [[0, 0], [-1, 0], [1, 0], [0, -1], [0, 1], [-0.7, -0.7], [-0.7, 0.7], [0.7, -0.7], [0.7, 0.7]]) {
    origin.copy(focus).addScaledVector(right, x * padding).addScaledVector(up, y * padding);
    raycaster.set(origin, direction);
    raycaster.far = distance;
    hits.length = 0;
    raycaster.intersectObjects(candidates, false, hits);
    for (const hit of hits) nearest = Math.min(nearest, Math.max(0, hit.distance - padding));
    // Reverse probes also catch single-sided roofs and surfaces viewed inside-out.
    origin.addScaledVector(direction, distance);
    raycaster.set(origin, reverse);
    hits.length = 0;
    raycaster.intersectObjects(candidates, false, hits);
    for (const hit of hits) nearest = Math.min(nearest, Math.max(0, distance - hit.distance - padding));
  }
  hits.length = 0;
  return nearest;
}
