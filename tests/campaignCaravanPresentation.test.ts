import fs from 'node:fs';
import * as THREE from 'three';
import { describe, expect, it, vi } from 'vitest';
import type { AssetLoader } from '../src/game/AssetLoader';
import { assembleCampaignCaravan, CARAVAN_DRIVER_OFFSET, CARAVAN_HORSE_OFFSET, CARAVAN_WHEEL_CIRCUMFERENCE, caravanFacing, caravanWheelTime } from '../src/game/network/CampaignCaravanPresentation';

vi.mock('../src/game/network/CampaignCharacterPresentation', () => ({
  resolveCampaignEquipment: vi.fn(async () => []), assembleCampaignEquipment: vi.fn(async () => {}),
}));

function fixture() {
  const root = (name: string) => {
    const group = new THREE.Group(); group.name = name;
    const mesh = new THREE.Mesh(); mesh.name = 'part'; group.add(mesh);
    return group;
  };
  const clip = (name: string, duration = 4) => new THREE.AnimationClip(name, duration,
    [new THREE.NumberKeyframeTrack('part.position[x]', [0, duration], [0, duration])]);
  const wagon = root('wagon'), horse = root('horse'), reins = root('reins'), driver = root('driver');
  const loader = {
    resolveApprovedAssetModels: vi.fn(async (key: string) => [`${key}-0`, `${key}-1`, `${key}-2`]),
    loadModelFull: vi.fn(async (model: string) => model.includes('draft_horse')
      ? { object: horse, animations: ['idle', 'walk', 'draft_trot'].map(name => clip(name)) }
      : { object: model.includes('reins') ? reins : driver, animations: [] }),
    resolveCharacterAsset: vi.fn(async () => ({ model: 'driver', skeletonId: 'humanoid_game_v2', bindPoseId: 'a_pose_v2' })),
    resolveStaticAnimationPack: vi.fn(async () => ({ model: 'pack', skeletonId: 'humanoid_game_v2', bindPoseId: 'a_pose_v2' })),
    loadCharacterAnimations: vi.fn(async () => [new THREE.AnimationClip('driver_seated', 4, [])]),
  };
  return { wagon, horse, reins, driver, loader, clips: [clip('caravan_roll', 1.6)] };
}

describe('reviewed campaign caravan assembly', () => {
  it('faces the supply route while waiting, ignoring coincident route points', () => {
    const origin = { x: 10, y: 3, z: 20 }, east = { ...origin, x: 25 };
    expect(caravanFacing({ position: origin, route: [origin, origin, east], routeIndex: 1 })).toBeCloseTo(Math.PI / 2);
    expect(caravanFacing({ position: east, route: [origin, east], routeIndex: 2 })).toBeCloseTo(Math.PI / 2);
    expect(caravanFacing({ position: origin, route: [], routeIndex: 0 })).toBe(0);
  });

  it('retains measured hitch and seated driver origins and chooses matching LODs', async () => {
    const f = fixture(), result = await assembleCampaignCaravan(f.wagon, f.clips, 2, f.loader as unknown as AssetLoader);
    expect(result?.object.children).toEqual([f.wagon, f.horse, f.reins, f.driver]);
    expect(f.horse.position.toArray()).toEqual([...CARAVAN_HORSE_OFFSET]);
    expect(f.driver.position.toArray()).toEqual([...CARAVAN_DRIVER_OFFSET]);
    expect(f.loader.loadModelFull.mock.calls.every(([name]) => name.endsWith('-2'))).toBe(true);
    const contract = JSON.parse(fs.readFileSync('authoring/blender/orvr-frontier/review/frontier_teamster_animations_build.json', 'utf8'));
    expect([...CARAVAN_DRIVER_OFFSET]).toEqual(contract.avatar_origin_wagon_local_gltf);
    expect(result?.mixers.map(mixer => mixer.getRoot())).toEqual([f.wagon, f.horse, f.driver]);
  });

  it('turns the wheels by travelled distance and holds their pose while waiting', async () => {
    const f = fixture(), result = await assembleCampaignCaravan(f.wagon, f.clips, 0, f.loader as unknown as AssetLoader);
    result!.update(10, CARAVAN_WHEEL_CIRCUMFERENCE / 4, 1.5);
    const wheel = f.wagon.getObjectByName('part')!;
    expect(wheel.position.x).toBeCloseTo(.4);
    result!.update(14, CARAVAN_WHEEL_CIRCUMFERENCE / 4, 0);
    expect(wheel.position.x).toBeCloseTo(.4);
    expect(caravanWheelTime(CARAVAN_WHEEL_CIRCUMFERENCE, 1.6)).toBeCloseTo(1.6);
  });

  it('keeps the original wagon usable when an operator pack is missing', async () => {
    const f = fixture();
    f.loader.loadCharacterAnimations.mockResolvedValue([]);
    expect(await assembleCampaignCaravan(f.wagon, f.clips, 0, f.loader as unknown as AssetLoader)).toBeNull();
    expect(f.wagon.parent).toBeNull();
    expect(f.horse.parent).toBeNull();
    expect(f.reins.parent).toBeNull();
  });

  it('does not attach asynchronous components after the actor has been released', async () => {
    const f = fixture(); let alive = true;
    const run = async <T,>(task: () => Promise<T>) => { const result = await task(); alive = false; return result; };
    expect(await assembleCampaignCaravan(f.wagon, f.clips, 0, f.loader as unknown as AssetLoader, run, () => alive)).toBeNull();
    expect(f.loader.loadModelFull).toHaveBeenCalledTimes(1);
    expect(f.horse.parent).toBeNull();
  });
});
