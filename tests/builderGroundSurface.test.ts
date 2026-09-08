import * as THREE from 'three';
import { describe, expect, it } from 'vitest';
import { BuilderGroundSurface } from '../src/world/editor/BuilderGroundSurface';

describe('GM terrain footing', () => {
  it('uses the surveyed bottom instead of a decorative water surface', () => {
    const geometry = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute([
      0,0,0, 0,0,10, 10,0,0,
    ], 3));
    const root = new THREE.Group(), bottom = new THREE.Mesh(geometry), water = new THREE.Mesh(geometry);
    bottom.position.y = -2; water.position.y = -.35; water.userData.noGroundSupport = true;
    root.add(bottom, water);
    expect(new BuilderGroundSurface(root, root).heightAt(2, 2, 1)).toBe(-2);
  });
  it('uses actual sloped triangles, honors reachability and follows rotation and scale', () => {
    const geometry = new THREE.BufferGeometry().setAttribute('position', new THREE.Float32BufferAttribute([
      0,0,0, 0,0,10, 10,5,0,
      0,8,0, 0,8,10, 10,8,0,
    ], 3));
    const root = new THREE.Group(), surface = new THREE.Mesh(geometry);
    root.add(surface);
    const ground = new BuilderGroundSurface(root, surface);
    expect(ground.heightAt(2, 2, 2)).toBeCloseTo(1);
    expect(ground.heightAt(2, 2, 10)).toBeCloseTo(8);
    expect(ground.heightAt(9, 9, 10)).toBeNull();
    root.position.set(20, 3, 40); root.rotation.y = Math.PI / 2; root.scale.set(2, 2, 2);
    expect(ground.heightAt(24, 36, 6)).toBeCloseTo(5);
    expect(ground.heightAt(24, 36, 4)).toBeNull();
    expect(ground.heightAt(2, 2, 20)).toBeNull();
  });
});
