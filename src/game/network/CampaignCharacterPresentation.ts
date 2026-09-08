import * as THREE from 'three';
import { PLAYABLE_CHARACTER_PROFILES } from '../../data/playableAssets.generated';
import { getEquipmentVisualForKey } from '../../data/items';
import { aegisNpcCivilianVariantFor, aegisNpcGuardVariantFor } from '../../data/modelOverrides';
import type { EquipSlot } from '../../services/types';
import type { AssetLoader, CharacterAssetResolution, EquipmentAssetResolution } from '../AssetLoader';
import { applyBodyRegionMask, bindSkinnedOverlayToPlayer, findFirstSkeleton, prepareEquipmentOverlay, sanitizePlayerAnimationClip } from '../CharacterEquipmentPresentation';
import { inferWeaponKindFromEquipment, markWeaponAttachment, positionEquipmentWeaponOverlay } from '../WeaponAnimation';

export interface CampaignEquipmentModule {
  key: string;
  slot: EquipSlot;
  models: string[];
  metadata: EquipmentAssetResolution;
}
type PresentationLoader = Pick<AssetLoader, 'resolveEquipmentModel' | 'resolveApprovedAssetModels' | 'loadModelFull'>;
export type PresentationQueue = <T>(load: () => Promise<T>) => Promise<T>;
const plans = new WeakMap<PresentationLoader, Map<string, Promise<CampaignEquipmentModule[]>>>();

/** Recruit gear is a reviewed presentation preset, never a client claim about combat stats. */
export function campaignEquipmentKeys(profileKey: string): Array<{ key: string; slot: EquipSlot }> {
  if (profileKey !== 'civic_battle_prelate_m') return [];
  const profile = PLAYABLE_CHARACTER_PROFILES.find(profile => profile.profileKey === profileKey)!;
  const armor = Object.entries(profile.armor).map(([slot, item]) => ({ key: item.itemKey, slot: slot as EquipSlot }));
  return [...armor, { key: 'weapon_hammer_reliquary_2h', slot: 'mainHand' }];
}

export function resolveCampaignEquipment(loader: PresentationLoader, profileKey: string, asset: CharacterAssetResolution): Promise<CampaignEquipmentModule[]> {
  let cache = plans.get(loader);
  if (!cache) { cache = new Map(); plans.set(loader, cache); }
  const context = { bodyFamily: asset.bodyFamily, bodyVariant: asset.bodyVariant, skeletonId: asset.skeletonId, bindPoseId: asset.bindPoseId };
  const key = `${profileKey}:${JSON.stringify(context)}`;
  let pending = cache.get(key);
  if (!pending) {
    pending = Promise.all(campaignEquipmentKeys(profileKey).map(async module => {
      const fallback = getEquipmentVisualForKey(module.key)?.model ?? '';
      const metadata = await loader.resolveEquipmentModel(module.key, fallback, context);
      const models = await loader.resolveApprovedAssetModels(module.key, 'equipment', context);
      if (metadata.disabled || metadata.bodyModel || !models.length || !models.includes(metadata.model)) {
        throw new Error(`Reviewed campaign equipment unavailable: ${module.key}`);
      }
      return { ...module, models, metadata };
    }));
    cache.set(key, pending);
  }
  return pending;
}

function skeletonsIn(root: THREE.Object3D): Set<THREE.Skeleton> {
  const skeletons = new Set<THREE.Skeleton>();
  root.traverse(node => { if ((node as THREE.SkinnedMesh).isSkinnedMesh) skeletons.add((node as THREE.SkinnedMesh).skeleton); });
  return skeletons;
}
function releaseOverlay(root: THREE.Object3D): void {
  for (const skeleton of skeletonsIn(root)) skeleton.dispose();
  root.removeFromParent();
}

/** Assemble off-scene. A missing part or stale load removes all overlays, without touching shared geometry/materials. */
export async function assembleCampaignEquipment(
  body: THREE.Object3D,
  modules: CampaignEquipmentModule[],
  level: number,
  loader: Pick<PresentationLoader, 'loadModelFull'>,
  run: PresentationQueue = load => load(),
  alive: () => boolean = () => true,
): Promise<void> {
  if (!modules.length) return;
  const target = findFirstSkeleton(body);
  if (!target) throw new Error('Reviewed recruit skeleton unavailable');
  const targetNames = new Set(target.bones.map(bone => bone.name.replace(/\.\d+$/u, '')));
  const overlays: THREE.Object3D[] = [];
  const regions = new Set<string>();
  try {
    for (const module of modules) {
      if (!alive()) throw new Error('Campaign actor released');
      const model = module.models[Math.min(level, module.models.length - 1)];
      const { object } = await run(() => loader.loadModelFull(model, () => new THREE.Group()));
      overlays.push(object);
      if (!alive()) throw new Error('Campaign actor released');
      let meshes = 0;
      object.traverse(node => { if ((node as THREE.Mesh).isMesh) meshes++; });
      if (!meshes) throw new Error(`Reviewed campaign equipment missing: ${module.key}`);
      object.name = `EquipmentOverlay_${module.slot}_${module.key}`;
      Object.assign(object.userData, { equipmentKey: module.key, equipmentSlot: module.slot, equipmentOverlay: true, equipmentFallback: false });
      prepareEquipmentOverlay(object);
      if (module.slot === 'mainHand' || module.slot === 'offHand') {
        const socket = body.getObjectByName(module.slot === 'mainHand' ? 'socket_hand_R' : 'socket_hand_L');
        if (!socket) throw new Error('Reviewed recruit hand socket unavailable');
        const kind = inferWeaponKindFromEquipment(module.key);
        markWeaponAttachment(object, { slot: module.slot, kind, source: 'equipment', key: module.key });
        positionEquipmentWeaponOverlay(object, module.slot, kind, true);
        socket.add(object);
      } else {
        const sourceSkeletons = skeletonsIn(object);
        // The legacy binder accepts partial success; preflight every mesh so no armor stays in bind pose.
        if (!module.metadata.skinned || !sourceSkeletons.size || [...sourceSkeletons].some(skeleton =>
          skeleton.bones.some(bone => !targetNames.has(bone.name.replace(/\.\d+$/u, ''))))) {
          throw new Error(`Campaign armor skeleton mismatch: ${module.key}`);
        }
        if (!bindSkinnedOverlayToPlayer(object, target)) throw new Error('Campaign armor binding failed');
        for (const skeleton of sourceSkeletons) skeleton.dispose();
        object.userData.skinnedEquipmentOverlay = true;
        body.add(object);
        for (const region of module.metadata.coveredRegions ?? []) regions.add(region);
      }
    }
    applyBodyRegionMask(body, regions);
    body.userData.campaignEquipmentComplete = true;
  } catch (error) {
    for (const overlay of overlays) releaseOverlay(overlay);
    throw error;
  }
}

/** Animation drives bones only; snapshot poses remain the sole world movement authority. */
export function campaignAnimationClips(base: THREE.AnimationClip[], pack: THREE.AnimationClip[]): THREE.AnimationClip[] {
  const clips = new Map<string, THREE.AnimationClip>();
  for (const clip of [...base, ...pack]) clips.set(clip.name, sanitizePlayerAnimationClip(clip));
  return [...clips.values()];
}

export interface CampaignNpcPresentation {
  id: string;
  role: string;
  race?: string;
  realm?: 'aegis' | 'riftbound' | null;
  profileKey?: string;
}
const riftRaces = new Set(['chaos', 'greenskin', 'dark_elf']);

/** Preserve authored race/role and reviewed city variants; unbuilt racial sets stay unavailable. */
export function campaignNpcProfile(npc: CampaignNpcPresentation): string | undefined {
  let race = npc.race;
  if (npc.realm && race && (riftRaces.has(race) ? 'riftbound' : 'aegis') !== npc.realm) race = undefined;
  if (!race) {
    const authored = npc.profileKey?.startsWith('npc_riftspire_') ? npc.profileKey.slice('npc_riftspire_'.length) : undefined;
    race = npc.realm === 'aegis' ? 'empire' : authored ?? (npc.realm === 'riftbound' ? 'chaos' : 'empire');
  }
  if (riftRaces.has(race)) return `npc_riftspire_${race}`;
  if (race !== 'empire') return undefined;
  const explicit = npc.profileKey;
  if (explicit === 'civic_battle_prelate_m' || explicit?.startsWith('npc_aegis_city_guard_') || explicit?.startsWith('npc_aegis_people_')) return explicit;
  const military = /guard|captain|commander|raider|caster/.test(npc.role);
  const seed = /captain|commander/.test(npc.role) ? `${npc.id}_captain` : npc.id;
  return (military
    ? aegisNpcGuardVariantFor('guard', 'npc_aegis_guard', seed)
    : aegisNpcCivilianVariantFor(npc.role, 'npc_aegis_civilian', seed))?.profileKey;
}
