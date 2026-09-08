import { afterEach, describe, expect, test, vi } from 'vitest';
import * as THREE from 'three';
import { CampaignAssetQueue, campaignChunkDistance, campaignLodLevel, releaseCampaignActor } from '../src/game/network/SharedCampaignRenderer';

afterEach(() => { vi.restoreAllMocks(); });

describe('shared campaign asset residency', () => {
  test('bounds total concurrent asset work across chunks and actors', async () => {
    const queue = new CampaignAssetQueue(2);
    const completions: Array<() => void> = [];
    let active = 0;
    let maximum = 0;
    const tasks = Array.from({ length: 5 }, () => queue.run(() => new Promise<void>(resolve => {
      active++; maximum = Math.max(maximum, active);
      completions.push(() => { active--; resolve(); });
    })));
    await vi.waitFor(() => expect(completions).toHaveLength(2));
    completions[0](); completions[1]();
    await vi.waitFor(() => expect(completions).toHaveLength(4));
    completions[2](); completions[3]();
    await vi.waitFor(() => expect(completions).toHaveLength(5));
    completions[4]();
    await Promise.all(tasks);
    expect(maximum).toBe(2);
    queue.close();
  });

  test('closing a stage cancels queued work while allowing active cleanup to finish', async () => {
    const queue = new CampaignAssetQueue(1);
    let complete!: () => void;
    const active = queue.run(() => new Promise<void>(resolve => { complete = resolve; }));
    const neverRun = vi.fn(async () => undefined);
    const waiting = expect(queue.run(neverRun)).rejects.toThrow('stage released');
    await vi.waitFor(() => expect(complete).toBeTypeOf('function'));
    queue.close();
    await waiting;
    complete(); await active;
    await expect(queue.run(neverRun)).rejects.toThrow('stage released');
    expect(neverRun).not.toHaveBeenCalled();
  });

  test('uses actual available LODs and distance to chunk edges', () => {
    expect([10, 150, 400].map(distance => campaignLodLevel(distance, 3))).toEqual([0, 1, 2]);
    expect([10, 50, 110].map(distance => campaignLodLevel(distance, 3, true))).toEqual([0, 1, 2]);
    expect(campaignLodLevel(1000, 1)).toBe(0);
    expect(campaignLodLevel(1000, 2)).toBe(1);
    expect(campaignChunkDistance({ x: 150, z: 150 }, { x: 0, z: 0 })).toBe(0);
    expect(campaignChunkDistance({ x: 450, z: 150 }, { x: 0, z: 0 })).toBe(300);
  });

  test('releases clone skeletons and mixer bindings without disposing shared meshes', () => {
    const geometry = new THREE.BufferGeometry();
    const material = new THREE.MeshStandardMaterial();
    const mesh = new THREE.SkinnedMesh(geometry, material);
    const bone = new THREE.Bone(); mesh.add(bone); mesh.bind(new THREE.Skeleton([bone]));
    const root = new THREE.Group(); root.add(mesh);
    const scene = new THREE.Scene(); scene.add(root);
    const mixer = new THREE.AnimationMixer(root);
    const geometryDispose = vi.spyOn(geometry, 'dispose');
    const materialDispose = vi.spyOn(material, 'dispose');
    const skeletonDispose = vi.spyOn(mesh.skeleton, 'dispose');
    const uncache = vi.spyOn(mixer, 'uncacheRoot');
    releaseCampaignActor(root, [mixer]);
    expect(skeletonDispose).toHaveBeenCalledOnce();
    expect(uncache).toHaveBeenCalledWith(root);
    expect(root.parent).toBeNull();
    expect(geometryDispose).not.toHaveBeenCalled();
    expect(materialDispose).not.toHaveBeenCalled();
    geometry.dispose(); material.dispose();
  });
});
