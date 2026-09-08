import * as THREE from 'three';
import { describe, expect, test, vi } from 'vitest';
import { CityRenderBatch, cityBatchKey, supportsCityBatch } from '../src/world/CityRenderBatch';

describe('capital multi-draw batches', () => {
  test('different compatible geometry shares one material batch with independent transforms', () => {
    const material = new THREE.MeshStandardMaterial();
    const a = new THREE.Mesh(new THREE.SphereGeometry(), material);
    const b = new THREE.Mesh(new THREE.SphereGeometry(2, 12, 8), material);
    expect(cityBatchKey(a, 'cell', true)).toBe(cityBatchKey(b, 'cell', true));
    expect(cityBatchKey(a, 'cell', false)).not.toBe(cityBatchKey(b, 'cell', false));
    const batch = new CityRenderBatch([a, b], true);
    const first = new THREE.Matrix4().makeTranslation(1, 2, 3);
    const second = new THREE.Matrix4().makeTranslation(8, 2, 3);
    const i = batch.add(a, first), j = batch.add(b, second);
    batch.reset(); batch.include(i, first); batch.include(j, second); batch.commit(true);
    const mesh = batch.object as THREE.BatchedMesh;
    expect(mesh.getVisibleAt(i)).toBe(true); expect(mesh.getVisibleAt(j)).toBe(true);
    const matrix = new THREE.Matrix4(); mesh.getMatrixAt(j, matrix);
    expect(matrix.equals(second)).toBe(true);
    const bounds = vi.spyOn(mesh, 'computeBoundingSphere');
    batch.reset(); batch.include(j, second); batch.commit(true);
    expect(mesh.getVisibleAt(i)).toBe(false); expect(mesh.getVisibleAt(j)).toBe(true);
    expect(bounds).not.toHaveBeenCalled();
    const moved = second.clone().setPosition(200, 0, 0);
    batch.reset(); batch.include(j, moved); batch.commit(true);
    expect(bounds).toHaveBeenCalledOnce();
    const disposeMaterial = vi.spyOn(material, 'dispose');
    const disposeGeometry = vi.spyOn(a.geometry, 'dispose');
    batch.dispose();
    expect(disposeMaterial).not.toHaveBeenCalled(); expect(disposeGeometry).not.toHaveBeenCalled();
  });

  test('preserves unsupported roots intact and separates render states', () => {
    const a = new THREE.Mesh(new THREE.SphereGeometry(), new THREE.MeshStandardMaterial());
    expect(supportsCityBatch(a)).toBe(true);
    const root = new THREE.Group(); root.add(a);
    const glass = new THREE.Mesh(a.geometry, new THREE.MeshStandardMaterial({ transparent: true }));
    root.add(glass); expect(supportsCityBatch(root)).toBe(false);
    root.remove(glass); a.scale.x = -1; expect(supportsCityBatch(root)).toBe(false);
    a.scale.x = 1; root.add(new THREE.PointLight()); expect(supportsCityBatch(root)).toBe(false);
    const rig = new THREE.SkinnedMesh(a.geometry, a.material);
    expect(supportsCityBatch(rig)).toBe(false);
    const animated = a.clone(); animated.animations = [new THREE.AnimationClip('sway', 1, [])];
    expect(supportsCityBatch(animated)).toBe(false);
    const custom = new THREE.Mesh(a.geometry, new THREE.ShaderMaterial());
    expect(supportsCityBatch(custom)).toBe(false);
    const b = a.clone(); b.castShadow = true;
    expect(cityBatchKey(a, 'cell', true)).not.toBe(cityBatchKey(b, 'cell', true));
  });
});
