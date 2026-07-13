export const BATTLE_PRELATE_V19_DEVELOPMENT_MODEL =
  '__model-development/battle-prelate-v19.glb';
export const BATTLE_PRELATE_V19_DEVELOPMENT_ROUTE =
  `/${BATTLE_PRELATE_V19_DEVELOPMENT_MODEL}`;
export const BATTLE_PRELATE_V19_SHA256 =
  '02e44d3ae6192682de93cd15bd9441d75c5c55173f3e7c1a41099b79ae6ffc4a';

export interface DevelopmentCharacterAsset {
  assetId: string;
  model: string;
  bodyFamily: string;
  bodyVariant: 'm' | 'f';
  skeletonId: string;
  bindPoseId: string;
  developmentOnly: true;
  equipmentMode: 'assembled';
}

const BATTLE_PRELATE_V19: DevelopmentCharacterAsset = {
  assetId: 'chr.civic_humanoid_v2.battle_prelate_m.runtime_assembled_review.v19',
  model: BATTLE_PRELATE_V19_DEVELOPMENT_MODEL,
  bodyFamily: 'civic_humanoid_v2',
  bodyVariant: 'm',
  skeletonId: 'humanoid_game_v2',
  bindPoseId: 'a_pose_v2',
  developmentOnly: true,
  equipmentMode: 'assembled',
};

/**
 * Returns a review candidate only when the caller has explicitly established
 * that it is running under Vite's development server. Production resolution
 * remains entirely registry- and approval-driven.
 */
export function developmentCharacterAssetFor(
  profileKey: string,
  bodyVariant: string | null | undefined,
  developmentMode: boolean,
): DevelopmentCharacterAsset | null {
  if (!developmentMode || profileKey !== 'civic_battle_prelate_m') return null;

  const normalizedVariant = bodyVariant?.trim().toLowerCase();
  if (normalizedVariant && normalizedVariant !== BATTLE_PRELATE_V19.bodyVariant) return null;
  return { ...BATTLE_PRELATE_V19 };
}
