import * as THREE from 'three';
import type { AssetLoader } from '../AssetLoader';
import type { CaravanState } from '../../shared/orvr/protocol';
import { assembleCampaignEquipment, resolveCampaignEquipment, type PresentationQueue } from './CampaignCharacterPresentation';
import { sanitizePlayerAnimationClip } from '../CharacterEquipmentPresentation';

// Measured in the accepted wagon/horse/driver export contracts (metres, seconds).
export const CARAVAN_WHEEL_CIRCUMFERENCE = 4.963716392671874;
export const CARAVAN_HORSE_OFFSET = [0, 0, 3.75] as const;
export const CARAVAN_DRIVER_OFFSET = [0, .6541226744651794, 1.38] as const;
export const CARAVAN_DRIVER_PROFILE = 'civic_battle_prelate_m';

export function caravanWheelTime(distance: number, duration: number): number {
  return Math.max(0, distance) / CARAVAN_WHEEL_CIRCUMFERENCE * duration;
}

/** Waiting caravans point into their next route segment before interpolation begins. */
export function caravanFacing(caravan: Pick<CaravanState, 'position' | 'route' | 'routeIndex'>): number {
  for (const point of caravan.route.slice(caravan.routeIndex)) {
    const dx = point.x - caravan.position.x, dz = point.z - caravan.position.z;
    if (Math.hypot(dx, dz) > .001) return Math.atan2(dx, dz);
  }
  for (const point of caravan.route.slice(0, caravan.routeIndex).reverse()) {
    const dx = caravan.position.x - point.x, dz = caravan.position.z - point.z;
    if (Math.hypot(dx, dz) > .001) return Math.atan2(dx, dz);
  }
  return 0;
}

export interface CampaignCaravanVisual {
  object: THREE.Group;
  mixers: THREE.AnimationMixer[];
  update(time: number, distance: number, speed: number): void;
}

function releaseClones(objects: THREE.Object3D[], mixers: THREE.AnimationMixer[]): void {
  for (const mixer of mixers) { mixer.stopAllAction(); mixer.uncacheRoot(mixer.getRoot()); }
  const skeletons = new Set<THREE.Skeleton>();
  for (const object of objects) {
    object.traverse(node => { if ((node as THREE.SkinnedMesh).isSkinnedMesh) skeletons.add((node as THREE.SkinnedMesh).skeleton); });
    object.removeFromParent();
  }
  for (const skeleton of skeletons) skeleton.dispose();
}

/** Independent mixers preserve each reviewed rig; the loader owns shared geometry/materials. */
export async function assembleCampaignCaravan(
  wagon: THREE.Object3D, wagonClips: THREE.AnimationClip[], level: number,
  loader: AssetLoader, run: PresentationQueue = task => task(), alive: () => boolean = () => true,
): Promise<CampaignCaravanVisual | null> {
  const additions: THREE.Object3D[] = [], mixers: THREE.AnimationMixer[] = [];
  try {
    const load = async (key: string) => {
      const models = await loader.resolveApprovedAssetModels(key, 'staticProps');
      if (!models.length || !alive()) throw new Error(`Caravan component unavailable: ${key}`);
      const result = await run(() => loader.loadModelFull(models[Math.min(level, models.length - 1)], () => new THREE.Group()));
      additions.push(result.object);
      let mesh = false; result.object.traverse(node => { if ((node as THREE.Mesh).isMesh) mesh = true; });
      if (!mesh || !alive()) throw new Error(`Caravan component could not load: ${key}`);
      return result;
    };
    const horse = await load('frontier_draft_horse'), reins = await load('frontier_caravan_reins');
    const asset = await loader.resolveCharacterAsset(CARAVAN_DRIVER_PROFILE);
    const pack = await loader.resolveStaticAnimationPack('frontier_supply_wagon');
    const models = await loader.resolveApprovedAssetModels(CARAVAN_DRIVER_PROFILE, 'characterProfiles');
    if (!asset || !pack || !models.length || !alive()) throw new Error('Reviewed driver unavailable');
    const driver = await run(() => loader.loadModelFull(models[Math.min(level, models.length - 1)], () => new THREE.Group()));
    additions.push(driver.object);
    const equipment = await resolveCampaignEquipment(loader, CARAVAN_DRIVER_PROFILE, asset, false);
    await assembleCampaignEquipment(driver.object, equipment, level, loader, run, alive);
    const driverClips = await run(() => loader.loadCharacterAnimations({ ...asset, animationPack: pack }, driver.object));
    if (!alive()) throw new Error('Caravan released');
    const required = (clips: THREE.AnimationClip[], name: string) => {
      const clip = clips.find(clip => clip.name === name);
      if (!clip) throw new Error(`Caravan clip unavailable: ${name}`);
      return clip;
    };
    const roll = required(wagonClips, 'caravan_roll');
    const seated = sanitizePlayerAnimationClip(required(driverClips, 'driver_seated'));
    const idle = required(horse.animations, 'idle'), walk = required(horse.animations, 'walk'), trot = required(horse.animations, 'draft_trot');
    const wagonMixer = new THREE.AnimationMixer(wagon), horseMixer = new THREE.AnimationMixer(horse.object), driverMixer = new THREE.AnimationMixer(driver.object);
    mixers.push(wagonMixer, horseMixer, driverMixer);
    wagonMixer.clipAction(roll).play(); driverMixer.clipAction(seated).play();
    const actions = { idle: horseMixer.clipAction(idle), walk: horseMixer.clipAction(walk), trot: horseMixer.clipAction(trot) };
    let gait: keyof typeof actions | undefined;
    horse.object.position.fromArray(CARAVAN_HORSE_OFFSET); driver.object.position.fromArray(CARAVAN_DRIVER_OFFSET);
    const object = new THREE.Group(); object.add(wagon, horse.object, reins.object, driver.object);
    return { object, mixers, update(time, distance, speed) {
      const next = speed < .08 ? 'idle' : speed < 2.4 ? 'walk' : 'trot';
      if (next !== gait) { horseMixer.stopAllAction(); actions[next].reset().play(); gait = next; }
      wagonMixer.setTime(caravanWheelTime(distance, roll.duration));
      horseMixer.setTime(next === 'idle' ? time : distance / (next === 'walk' ? 1.5 : 3.5));
      driverMixer.setTime(time);
    } };
  } catch {
    // Keep the already loaded wagon if an optional component is missing or stale.
    releaseClones(additions, mixers);
    return null;
  }
}
