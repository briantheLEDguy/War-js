import * as THREE from 'three';
import { staticTarget, Vfx } from './animation/VfxLayer';
import type { EnemyCastState } from './enemyAttackTelegraph';

/** A fixed ground footprint, using only primitive geometry so no asset is required. */
export class EnemyAttackTelegraphVfx extends Vfx {
  private fill: THREE.MeshBasicMaterial | null = null;

  constructor(private cast: EnemyCastState, private groundHeightAt?: (x: number, z: number) => number) {
    const { origin } = cast.footprint;
    super(staticTarget(new THREE.Vector3(origin.x, origin.y, origin.z)), (cast.dueAt - cast.startedAt) / 1000);
  }

  build(): THREE.Group {
    const root = new THREE.Group();
    const footprint = this.cast.footprint;
    const segments = 48;
    const radialSteps = 6;
    const radius = footprint.shape === 'circle' ? footprint.radius : footprint.range;
    const start = footprint.shape === 'circle' ? 0 : footprint.rotationY - footprint.halfAngleRad;
    const arc = footprint.shape === 'circle' ? Math.PI * 2 : footprint.halfAngleRad * 2;
    const project = (x: number, z: number): THREE.Vector3 => {
      const height = this.groundHeightAt?.(footprint.origin.x + x, footprint.origin.z + z) ?? footprint.origin.y;
      return new THREE.Vector3(x, (Number.isFinite(height) ? height : footprint.origin.y) - footprint.origin.y + 0.08, z);
    };
    // 295 shared vertices project the interior as well as the outline onto slopes.
    const points = [project(0, 0)];
    for (let ring = 1; ring <= radialSteps; ring++) {
      for (let i = 0; i <= segments; i++) {
        const angle = start + arc * i / segments;
        const distance = radius * ring / radialSteps;
        points.push(project(Math.sin(angle) * distance, Math.cos(angle) * distance));
      }
    }
    const ringIndex = (ring: number, segment: number) => 1 + (ring - 1) * (segments + 1) + segment;
    const indices: number[] = [];
    for (let segment = 0; segment < segments; segment++) {
      indices.push(0, ringIndex(1, segment), ringIndex(1, segment + 1));
      for (let ring = 1; ring < radialSteps; ring++) {
        const a = ringIndex(ring, segment);
        const b = ringIndex(ring, segment + 1);
        const c = ringIndex(ring + 1, segment);
        const d = ringIndex(ring + 1, segment + 1);
        indices.push(a, c, d, a, d, b);
      }
    }
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    geometry.setIndex(indices);
    this.fill = new THREE.MeshBasicMaterial({
      color: 0xe6502d, transparent: true, opacity: 0.22, side: THREE.DoubleSide,
      depthWrite: false, polygonOffset: true, polygonOffsetFactor: -1,
    });
    const mesh = new THREE.Mesh(geometry, this.fill);
    mesh.renderOrder = 4;
    root.add(mesh);
    const outline: THREE.Vector3[] = [];
    if (footprint.shape === 'cone') {
      outline.push(points[0]);
      for (let ring = 1; ring < radialSteps; ring++) outline.push(points[ringIndex(ring, 0)]);
    }
    for (let i = 0; i <= segments; i++) outline.push(points[ringIndex(radialSteps, i)]);
    if (footprint.shape === 'cone') {
      for (let ring = radialSteps - 1; ring >= 1; ring--) outline.push(points[ringIndex(ring, segments)]);
    }
    const border = new THREE.LineLoop(
      new THREE.BufferGeometry().setFromPoints(outline),
      new THREE.LineBasicMaterial({ color: 0xffc177, transparent: true, opacity: 0.95, depthWrite: false }),
    );
    border.renderOrder = 5;
    root.add(border);
    return root;
  }

  updateEffect(progress: number): void {
    if (this.fill) this.fill.opacity = 0.22 + progress * 0.3;
  }

  cancel(): void {
    if (this.root) this.root.visible = false;
    this.elapsed = this.duration;
  }
}
