import { afterEach, describe, expect, test, vi } from 'vitest';
import {
  BATTLE_PRELATE_DEVELOPMENT_MODEL,
  BATTLE_PRELATE_DEVELOPMENT_REVISION,
  BATTLE_PRELATE_DEVELOPMENT_ROUTE,
  BATTLE_PRELATE_DEVELOPMENT_SHA256,
  developmentCharacterAssetFor,
} from '../src/config/developmentModelCandidates';
import { AssetLoader } from '../src/game/AssetLoader';

type TestAssetIndex = {
  schemaVersion: number;
  characterProfiles?: Record<string, unknown>;
  equipment?: Record<string, unknown>;
};

function installAssetFetch(index: TestAssetIndex, availableModels: string[]): void {
  const available = new Set(availableModels);
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.includes('asset-index.json')) {
      return new Response(JSON.stringify(index), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      });
    }

    const modelName = url.split('/').pop()?.split('?')[0] ?? '';
    return new Response(null, {
      status: available.has(modelName) ? 200 : 404,
      headers: { 'content-type': 'model/gltf-binary' },
    });
  }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('approval-aware character model resolution', () => {
  test('loads approved and compatible entries while preserving safe legacy entries', async () => {
    installAssetFetch({
      schemaVersion: 2,
      characterProfiles: {
        approved: {
          assetId: 'chr.approved',
          model: 'approved.glb',
          bodyFamily: 'civic_humanoid_v2',
          bodyVariant: 'f',
          skeletonId: 'humanoid_game_v2',
          bindPoseId: 'a_pose_v1',
          lifecycleStatus: 'approved',
          runtimeReady: true,
          reviewStatus: 'approved',
        },
        legacy: {
          assetId: 'chr.legacy',
          model: 'legacy.glb',
        },
      },
    }, ['approved.glb', 'legacy.glb']);

    const loader = new AssetLoader();
    await expect(loader.resolveCharacterAsset('approved', 'f')).resolves.toEqual({
      assetId: 'chr.approved',
      model: 'approved.glb',
      bodyFamily: 'civic_humanoid_v2',
      bodyVariant: 'f',
      skeletonId: 'humanoid_game_v2',
      bindPoseId: 'a_pose_v1',
    });
    await expect(loader.resolveCharacterModel('legacy')).resolves.toBe('legacy.glb');
    await expect(loader.resolveCharacterModel('approved', 'm')).resolves.toBeNull();
  });

  test.each(['draft', 'review', 'blocked'])('rejects %s lifecycle entries', async (status) => {
    installAssetFetch({
      schemaVersion: 2,
      characterProfiles: {
        candidate: {
          assetId: 'chr.candidate',
          model: 'candidate.glb',
          lifecycleStatus: status,
          runtimeReady: true,
        },
      },
    }, ['candidate.glb']);

    await expect(new AssetLoader().resolveCharacterModel('candidate')).resolves.toBeNull();
  });

  test('rejects legacy negative reviews and approved entries whose file is missing', async () => {
    installAssetFetch({
      schemaVersion: 2,
      characterProfiles: {
        pendingLegacy: {
          assetId: 'chr.pending',
          model: 'pending.glb',
          reviewStatus: 'review',
        },
        missing: {
          assetId: 'chr.missing',
          model: 'missing.glb',
          lifecycleStatus: 'approved',
          runtimeReady: true,
        },
      },
    }, ['pending.glb']);

    const loader = new AssetLoader();
    await expect(loader.resolveCharacterModel('pendingLegacy')).resolves.toBeNull();
    await expect(loader.resolveCharacterModel('missing')).resolves.toBeNull();
    await expect(loader.resolveCharacterModel('not-indexed')).resolves.toBeNull();
  });
});

describe('development-only assembled character integration', () => {
  test('selects only the current male Battle Prelate candidate in development mode', () => {
    expect(developmentCharacterAssetFor('civic_battle_prelate_m', 'm', true)).toMatchObject({
      assetId: expect.stringContaining(`.${BATTLE_PRELATE_DEVELOPMENT_REVISION}`),
      model: BATTLE_PRELATE_DEVELOPMENT_MODEL,
      bodyFamily: 'civic_humanoid_v2',
      bodyVariant: 'm',
      skeletonId: 'humanoid_game_v2',
      bindPoseId: 'a_pose_v2',
      developmentOnly: true,
      equipmentMode: 'assembled',
    });
    expect(BATTLE_PRELATE_DEVELOPMENT_ROUTE).toBe(`/${BATTLE_PRELATE_DEVELOPMENT_MODEL}`);
    expect(BATTLE_PRELATE_DEVELOPMENT_SHA256).toMatch(
      /^(?:[a-f0-9]{64}|__REPLACE_WITH_BATTLE_PRELATE_V20_SHA256__)$/u,
    );
    expect(developmentCharacterAssetFor('civic_battle_prelate_m', 'f', true)).toBeNull();
    expect(developmentCharacterAssetFor('civic_battle_prelate_f', 'f', true)).toBeNull();
  });

  test('cannot select the candidate when development mode is disabled', () => {
    expect(developmentCharacterAssetFor('civic_battle_prelate_m', 'm', false)).toBeNull();
  });

  test('uses the virtual development route without changing registry approval state', async () => {
    installAssetFetch({
      schemaVersion: 2,
      characterProfiles: {
        civic_battle_prelate_m: {
          assetId: 'chr.unapproved',
          model: 'must-not-load.glb',
          lifecycleStatus: 'review',
          runtimeReady: false,
        },
      },
    }, [BATTLE_PRELATE_DEVELOPMENT_MODEL.split('/').at(-1) ?? '']);

    const resolution = await new AssetLoader().resolveCharacterAsset(
      'civic_battle_prelate_m',
      'm',
    );

    expect(resolution).toMatchObject({
      model: BATTLE_PRELATE_DEVELOPMENT_MODEL,
      developmentOnly: true,
      equipmentMode: 'assembled',
    });
    const fetchMock = vi.mocked(fetch);
    expect(fetchMock.mock.calls.some(([input]) => (
      String(input).includes(BATTLE_PRELATE_DEVELOPMENT_ROUTE)
    ))).toBe(true);
    expect(fetchMock.mock.calls.some(([input]) => String(input).includes('must-not-load.glb'))).toBe(false);
  });

  test('falls through to approval-aware resolution when the pinned route is unavailable', async () => {
    installAssetFetch({
      schemaVersion: 2,
      characterProfiles: {
        civic_battle_prelate_m: {
          assetId: 'chr.approved',
          model: 'approved-published.glb',
          bodyVariant: 'm',
          lifecycleStatus: 'approved',
          reviewStatus: 'approved',
          runtimeReady: true,
        },
      },
    }, ['approved-published.glb']);

    await expect(new AssetLoader().resolveCharacterModel(
      'civic_battle_prelate_m',
      'm',
    )).resolves.toBe('approved-published.glb');
  });
});

describe('body-compatible equipment resolution', () => {
  const compatibleFemale = {
    bodyFamily: 'civic_humanoid_v2',
    bodyVariant: 'f',
    skeletonId: 'humanoid_game_v2',
    bindPoseId: 'a_pose_v1',
  } as const;

  test('selects an approved gender variant and its matching base body', async () => {
    installAssetFetch({
      schemaVersion: 2,
      equipment: {
        prelateChest: {
          assetId: 'armor.prelate.chest',
          variants: {
            m: {
              model: 'prelate_chest_m.glb',
              bodyModel: 'prelate_body_m.glb',
              bodyFamily: 'civic_humanoid_v2',
              bodyVariant: 'm',
              skeletonId: 'humanoid_game_v2',
              bindPoseId: 'a_pose_v1',
              lifecycleStatus: 'approved',
              reviewStatus: 'approved',
              runtimeReady: true,
              skinned: true,
            },
            f: {
              model: 'prelate_chest_f.glb',
              bodyModel: 'prelate_body_f.glb',
              bodyFamily: 'civic_humanoid_v2',
              bodyVariant: 'f',
              skeletonId: 'humanoid_game_v2',
              bindPoseId: 'a_pose_v1',
              lifecycleStatus: 'approved',
              reviewStatus: 'approved',
              runtimeReady: true,
              skinned: true,
              coveredRegions: ['torso'],
            },
          },
        },
      },
    }, ['prelate_chest_f.glb', 'prelate_body_f.glb']);

    const loader = new AssetLoader();
    await expect(loader.resolveEquipmentModel(
      'prelateChest',
      'equipment_armor_chain.glb',
      compatibleFemale,
    )).resolves.toEqual({
      model: 'prelate_chest_f.glb',
      bodyModel: 'prelate_body_f.glb',
      bodyFamily: 'civic_humanoid_v2',
      bodyVariant: 'f',
      skeletonId: 'humanoid_game_v2',
      bindPoseId: 'a_pose_v1',
      skinned: true,
      coveredRegions: ['torso'],
    });
    await expect(loader.resolveEquipmentBaseBodyModel(
      ['prelateChest'],
      compatibleFemale,
    )).resolves.toBe('prelate_body_f.glb');
  });

  test.each([
    ['body family', { ...compatibleFemale, bodyFamily: 'mire_brutish_v1' }],
    ['body variant', { ...compatibleFemale, bodyVariant: 'm' }],
    ['skeleton', { ...compatibleFemale, skeletonId: 'humanoid_v1' }],
    ['bind pose', { ...compatibleFemale, bindPoseId: 't_pose_v1' }],
  ])('disables equipment with an incompatible %s', async (_label, context) => {
    installAssetFetch({
      schemaVersion: 2,
      equipment: {
        chest: {
          model: 'chest_f.glb',
          bodyFamily: 'civic_humanoid_v2',
          bodyVariant: 'f',
          skeletonId: 'humanoid_game_v2',
          bindPoseId: 'a_pose_v1',
          lifecycleStatus: 'approved',
          runtimeReady: true,
        },
      },
    }, ['chest_f.glb']);

    await expect(new AssetLoader().resolveEquipmentModel(
      'chest',
      'legacy_chest.glb',
      context,
    )).resolves.toEqual({
      model: 'legacy_chest.glb',
      bodyModel: null,
      disabled: true,
    });
  });

  test('keeps legacy flat calls working and disables rejected or missing indexed models', async () => {
    installAssetFetch({
      schemaVersion: 2,
      equipment: {
        legacy: {
          assetId: 'armor.legacy',
          model: 'legacy.glb',
          runtimeReady: true,
        },
        blocked: {
          assetId: 'armor.blocked',
          model: 'blocked.glb',
          lifecycleStatus: 'blocked',
          runtimeReady: true,
        },
        missing: {
          assetId: 'armor.missing',
          model: 'missing.glb',
          lifecycleStatus: 'approved',
          runtimeReady: true,
        },
      },
    }, ['legacy.glb', 'blocked.glb']);

    const loader = new AssetLoader();
    const legacyResolution = await loader.resolveEquipmentModel('legacy', 'fallback.glb');
    expect(legacyResolution.model).toBe('legacy.glb');
    expect(legacyResolution.disabled).toBeUndefined();
    await expect(loader.resolveEquipmentModel('blocked', 'fallback.glb')).resolves.toEqual({
      model: 'fallback.glb',
      bodyModel: null,
      disabled: true,
    });
    await expect(loader.resolveEquipmentModel('missing', 'fallback.glb')).resolves.toEqual({
      model: 'fallback.glb',
      bodyModel: null,
      disabled: true,
    });
    await expect(loader.resolveEquipmentModel('not-indexed', 'fallback.glb')).resolves.toEqual({
      model: 'fallback.glb',
      bodyModel: null,
    });
  });
});
