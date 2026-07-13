export const BATTLE_PRELATE_DEVELOPMENT_REVISION = 'v20';
export const BATTLE_PRELATE_DEVELOPMENT_MODEL =
  `__model-development/battle-prelate-${BATTLE_PRELATE_DEVELOPMENT_REVISION}.glb`;
export const BATTLE_PRELATE_DEVELOPMENT_ROUTE =
  `/${BATTLE_PRELATE_DEVELOPMENT_MODEL}`;
export const BATTLE_PRELATE_DEVELOPMENT_SHA256 =
  'ed108de374db56a7fbc9778e48725f9981170448c0eff5781c1501ff700a7f7c';

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

const BATTLE_PRELATE_DEVELOPMENT_CANDIDATE: DevelopmentCharacterAsset = {
  assetId: `chr.civic_humanoid_v2.battle_prelate_m.runtime_assembled_review.${BATTLE_PRELATE_DEVELOPMENT_REVISION}`,
  model: BATTLE_PRELATE_DEVELOPMENT_MODEL,
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
  if (
    normalizedVariant
    && normalizedVariant !== BATTLE_PRELATE_DEVELOPMENT_CANDIDATE.bodyVariant
  ) return null;
  return { ...BATTLE_PRELATE_DEVELOPMENT_CANDIDATE };
}
