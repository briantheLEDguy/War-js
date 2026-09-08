import * as THREE from 'three';
import { acceleratedRaycast, MeshBVH } from 'three-mesh-bvh';

interface Leaf { mesh: THREE.Mesh; bounds: THREE.Box3 }
interface Node { bounds: THREE.Box3; leaves?: Leaf[]; left?: Node; right?: Node }

function tree(leaves: Leaf[]): Node | null {
  if (!leaves.length) return null;
  const bounds = new THREE.Box3();
  for (const leaf of leaves) bounds.union(leaf.bounds);
  if (leaves.length <= 8) return { bounds, leaves };
  const size = bounds.getSize(new THREE.Vector3());
  const axis = size.x >= size.y && size.x >= size.z ? 'x' : size.y >= size.z ? 'y' : 'z';
  leaves.sort((a, b) => a.bounds.min[axis] + a.bounds.max[axis] - b.bounds.min[axis] - b.bounds.max[axis]);
  const middle = Math.floor(leaves.length / 2);
  return { bounds, left: tree(leaves.slice(0, middle))!, right: tree(leaves.slice(middle))! };
}

/** Preserve the camera's high-detail geometry even when rendering hides an LOD. */
function visitMeshes(object: THREE.Object3D, visit: (mesh: THREE.Mesh) => void): void {
  if (object instanceof THREE.LOD) {
    if (object.levels[0]) visitMeshes(object.levels[0].object, visit);
    return;
  }
  if (object instanceof THREE.Mesh) visit(object);
  for (const child of object.children) visitMeshes(child, visit);
}

function accelerate(mesh: THREE.Mesh): void {
  if (mesh instanceof THREE.SkinnedMesh || mesh.morphTargetInfluences?.length
    || mesh.raycast !== THREE.Mesh.prototype.raycast && mesh.raycast !== acceleratedRaycast) return;
  const geometry = mesh.geometry;
  // Tiny primitives are cheaper to intersect directly. Indirect BVHs leave the
  // shared index buffer and material groups intact for rendering/editor use.
  if ((geometry.index?.count ?? geometry.attributes.position?.count ?? 0) < 450) return;
  if (!geometry.boundsTree) {
    // v0.8 supports indirect construction but omits it from its options type.
    const options = { indirect: true, maxLeafTris: 10 };
    geometry.boundsTree = new MeshBVH(geometry, options);
    const dispose = () => { delete geometry.boundsTree; geometry.removeEventListener('dispose', dispose); };
    geometry.addEventListener('dispose', dispose);
  }
  mesh.raycast = acceleratedRaycast;
}

/** Rebuilt on world/editor revisions; steady frames only visit intersecting nodes.
 * Dynamic roots remain live and are never baked into the static index. */
export class CameraCollisionIndex {
  private root: Node | null = null;
  private dynamic: THREE.Object3D[] = [];
  private meshBounds = new THREE.Box3();

  rebuild(objects: readonly THREE.Object3D[]): void {
    const leaves: Leaf[] = [];
    this.dynamic = [];
    for (const object of objects) {
      if (object.userData.cameraStaticGeometry !== true) {
        this.dynamic.push(object);
        visitMeshes(object, accelerate);
        continue;
      }
      object.updateWorldMatrix(true, true);
      visitMeshes(object, mesh => {
        if (mesh instanceof THREE.SkinnedMesh || mesh.morphTargetInfluences?.length) {
          this.dynamic.push(mesh);
          return;
        }
        if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
        if (!mesh.geometry.boundingBox || mesh.geometry.boundingBox.isEmpty()) return;
        accelerate(mesh);
        leaves.push({ mesh, bounds: mesh.geometry.boundingBox.clone().applyMatrix4(mesh.matrixWorld) });
      });
    }
    this.root = tree(leaves);
  }

  query(bounds: THREE.Box3, result: THREE.Mesh[], extraDynamic: readonly THREE.Object3D[] = []): void {
    result.length = 0;
    const visit = (node: Node | null | undefined) => {
      if (!node || !node.bounds.intersectsBox(bounds)) return;
      if (node.leaves) {
        for (const leaf of node.leaves) if (leaf.bounds.intersectsBox(bounds)) result.push(leaf.mesh);
      } else { visit(node.left); visit(node.right); }
    };
    visit(this.root);
    const dynamic = (object: THREE.Object3D) => {
      object.updateWorldMatrix(true, true);
      visitMeshes(object, mesh => {
        if (!mesh.geometry.boundingBox) mesh.geometry.computeBoundingBox();
        if (mesh.geometry.boundingBox && this.meshBounds.copy(mesh.geometry.boundingBox).applyMatrix4(mesh.matrixWorld).intersectsBox(bounds)) result.push(mesh);
      });
    };
    for (const object of this.dynamic) dynamic(object);
    for (const object of extraDynamic) dynamic(object);
  }

  dispose(): void { this.root = null; this.dynamic = []; }
}

export interface IndexedCameraObjects {
  index: CameraCollisionIndex;
  dynamic: readonly THREE.Object3D[];
}
