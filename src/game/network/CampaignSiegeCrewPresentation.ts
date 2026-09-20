import * as THREE from 'three';
import type { AssetLoader, CharacterAssetResolution } from '../AssetLoader';
import type { EquipmentState } from '../../shared/orvr/protocol';
import { sanitizePlayerAnimationClip } from '../CharacterEquipmentPresentation';
import type { PresentationQueue } from './CampaignCharacterPresentation';
import { SIEGE_WHEEL_CIRCUMFERENCE } from './CampaignSiegePresentation';

export function compatibleRamCrew(asset: CharacterAssetResolution): boolean {
  return asset.bodyFamily === 'civic_battle_prelate_m' && asset.bodyVariant === 'm'
    && asset.skeletonId === 'humanoid_game_v2' && asset.bindPoseId === 'a_pose_v2';
}

export interface CampaignSiegeCrewVisual {
  mixer: THREE.AnimationMixer;
  setSeat(seat: 0 | 1 | undefined): boolean;
  update(zoneSeconds: number, operation: EquipmentState['lastOperation'], distance: number, speed: number): void;
  dispose(): void;
}

/** Pose the existing player skeleton. External authority transforms own every seat/root position. */
export function createCampaignSiegeCrew(object: THREE.Object3D, packs: [THREE.AnimationClip[], THREE.AnimationClip[]]): CampaignSiegeCrewVisual | null {
  const required = ['ram_crew_idle', 'ram_crew_drive', 'ram_crew_strike'] as const;
  if (packs.some(clips => required.some(name => !clips.find(clip => clip.name === name)))) return null;
  const mixer = new THREE.AnimationMixer(object);
  const actions = packs.map(clips => Object.fromEntries(required.map(name => {
    const action = mixer.clipAction(sanitizePlayerAnimationClip(clips.find(clip => clip.name === name)!));
    action.setLoop(THREE.LoopOnce, 1); action.clampWhenFinished = true; action.paused = true;
    return [name, action];
  })) as Record<typeof required[number], THREE.AnimationAction>);
  let seat: 0 | 1 | undefined, active: THREE.AnimationAction | undefined;
  const held = new Map<THREE.Object3D, boolean>();
  return { mixer,
    setSeat(next) {
      if (next === seat) return false;
      if (seat === undefined && next !== undefined) object.traverse(node => {
        if (node.userData.equipmentSlot === 'mainHand' || node.userData.equipmentSlot === 'offHand') {
          held.set(node, node.visible); node.visible = false;
        }
      });
      active?.stop(); active = undefined;
      if (next === undefined) { for (const [node, visible] of held) node.visible = visible; held.clear(); }
      seat = next;
      return true;
    },
    update(zoneSeconds, operation, distance, speed) {
      if (seat === undefined) return;
      const set = actions[seat], age = operation && Number.isFinite(operation.at) ? Math.max(0, zoneSeconds - operation.at) : Infinity;
      const next = age < set.ram_crew_strike.getClip().duration ? set.ram_crew_strike : speed > .08 ? set.ram_crew_drive : set.ram_crew_idle;
      if (active !== next) { active?.stop(); active = next; }
      const duration = next.getClip().duration;
      next.enabled = true; next.paused = true;
      next.time = next === set.ram_crew_strike ? age : next === set.ram_crew_drive
        ? Math.max(0, distance) / SIEGE_WHEEL_CIRCUMFERENCE * duration % duration : Math.max(0, zoneSeconds) % duration;
      next.play(); mixer.update(0);
    },
    dispose() {
      for (const [node, visible] of held) node.visible = visible;
      held.clear(); mixer.stopAllAction(); mixer.uncacheRoot(object);
    },
  };
}

/** A missing or incompatible optional pose pack leaves the actual avatar and ordinary animation intact. */
export async function assembleCampaignSiegeCrew(object: THREE.Object3D, asset: CharacterAssetResolution,
  loader: Pick<AssetLoader, 'resolveStaticOperatorAnimationPacks' | 'loadCharacterAnimations'>,
  run: PresentationQueue = load => load(), alive: () => boolean = () => true): Promise<CampaignSiegeCrewVisual | null> {
  if (!compatibleRamCrew(asset)) return null;
  try {
    const packs = await loader.resolveStaticOperatorAnimationPacks('frontier_battering_ram');
    if (!packs || !alive()) return null;
    const [left, right] = await Promise.all([packs.left, packs.right].map(animationPack =>
      run(() => loader.loadCharacterAnimations({ ...asset, animationPack }, object))));
    return alive() ? createCampaignSiegeCrew(object, [left, right]) : null;
  } catch { return null; }
}
