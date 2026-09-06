import * as THREE from 'three';
import { Vfx, followObject } from './VfxLayer';

/** History of the actual hammer head, relative to its live anchor. */
export class WeaponTrailVfx extends Vfx {
  private points: THREE.Vector3[] = [];
  private geometry = new THREE.BufferGeometry();
  private positions = new Float32Array(24 * 3);
  private material = new THREE.LineBasicMaterial({ color: '#ffe4a3', transparent: true, opacity: .7, depthWrite: false, blending: THREE.AdditiveBlending });
  private world = new THREE.Vector3();
  constructor(private anchor: THREE.Object3D, duration: number, delay: number) {
    super(followObject(anchor), duration, delay);
  }
  build(): THREE.Group {
    const root = new THREE.Group();
    this.geometry.setAttribute('position', new THREE.BufferAttribute(this.positions, 3).setUsage(THREE.DynamicDrawUsage));
    this.geometry.setDrawRange(0, 0);
    const line = new THREE.Line(this.geometry, this.material);
    line.frustumCulled = false;
    root.add(line);
    return root;
  }
  updateEffect(t: number): void {
    this.anchor.getWorldPosition(this.world);
    const point = this.points.length === 24 ? this.points.shift()! : new THREE.Vector3();
    this.points.push(point.copy(this.world));
    this.points.forEach((p, i) => {
      this.positions[i * 3] = p.x - this.world.x;
      this.positions[i * 3 + 1] = p.y - this.world.y;
      this.positions[i * 3 + 2] = p.z - this.world.z;
    });
    this.geometry.attributes.position.needsUpdate = true;
    this.geometry.setDrawRange(0, this.points.length);
    this.material.opacity = .65 * Math.sin(Math.PI * t);
  }
}
