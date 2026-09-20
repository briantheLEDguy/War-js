import * as THREE from 'three';
import type { EquipmentKind, EquipmentState, KeepConfig } from '../../shared/orvr/protocol';

export const SIEGE_ASSET_KEYS = {
  ram: 'frontier_battering_ram', oil: 'frontier_oil_cauldron', catapult: 'frontier_field_catapult',
} as const;
// Accepted mechanism contract: siege tires use 86% of the wagon's 0.79 m radius.
export const SIEGE_WHEEL_CIRCUMFERENCE = 2 * Math.PI * .79 * .86;

export function campaignSiegeKind(assetKey: string): EquipmentKind | undefined {
  return (Object.keys(SIEGE_ASSET_KEYS) as EquipmentKind[]).find(kind => SIEGE_ASSET_KEYS[kind] === assetKey);
}

/** Wall-mounted oil retains its authored orientation; mobile engines can aim at a confirmed target. */
export function campaignSiegeFacing(machine: Pick<EquipmentState, 'kind' | 'position' | 'lastOperation' | 'facing'>,
  keep?: Pick<KeepConfig, 'position' | 'outerGate'>): number {
  if (machine.kind === 'ram' && Number.isFinite(machine.facing)) return machine.facing!;
  const target = machine.kind !== 'oil' ? machine.lastOperation?.target : undefined;
  const dx = target ? target.x - machine.position.x : keep ? keep.outerGate.x - keep.position.x : 0;
  const dz = target ? target.z - machine.position.z : keep ? keep.outerGate.z - keep.position.z : 1;
  return Math.atan2(dx, dz);
}

export interface CampaignSiegeVisual {
  mixer: THREE.AnimationMixer;
  update(zoneSeconds: number, operation: EquipmentState['lastOperation'], distance: number): void;
}

/** Sample confirmed zone time, so repeated snapshots and loading another LOD never restart a shot. */
export function assembleCampaignSiege(object: THREE.Object3D, clips: THREE.AnimationClip[], kind: EquipmentKind): CampaignSiegeVisual {
  const mixer = new THREE.AnimationMixer(object);
  const action = (name: string) => {
    const clip = clips.find(clip => clip.name === name);
    if (!clip) return undefined;
    const result = mixer.clipAction(clip);
    result.setLoop(THREE.LoopOnce, 1); result.clampWhenFinished = true; result.paused = true;
    return result;
  };
  const fire = action({ ram: 'ram_strike', oil: 'oil_pour', catapult: 'catapult_fire' }[kind]);
  const reload = kind === 'catapult' ? action('catapult_reload') : undefined;
  const roll = action('siege_roll');
  let active: THREE.AnimationAction | undefined;
  const sample = (next: THREE.AnimationAction | undefined, time: number) => {
    if (active !== next) { active?.stop(); active = next; }
    if (next) { next.enabled = true; next.paused = true; next.time = time; next.play(); }
  };
  const visual: CampaignSiegeVisual = { mixer, update(zoneSeconds, operation, distance) {
    const age = operation && Number.isFinite(operation.at) ? Math.max(0, zoneSeconds - operation.at) : Infinity;
    const fireDuration = fire?.getClip().duration ?? 0;
    const reloadDuration = reload?.getClip().duration ?? 0;
    if (fire && age < fireDuration) sample(fire, age);
    else if (reload && age < fireDuration + reloadDuration) sample(reload, age - fireDuration);
    else sample(fire, 0); // Includes the catapult's cocked pose, instead of its vertical bind pose.
    if (roll) {
      roll.time = Math.max(0, distance) / SIEGE_WHEEL_CIRCUMFERENCE * roll.getClip().duration % roll.getClip().duration;
      roll.play();
    }
    mixer.update(0);
  } };
  visual.update(0, undefined, 0);
  return visual;
}
