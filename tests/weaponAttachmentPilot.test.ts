import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';

const recipePath = path.resolve(
  'scripts/blender-character-pipeline/data/body-families/weapon-attachment-pilot.recipe.json',
);
const recipe = JSON.parse(readFileSync(recipePath, 'utf8'));

describe('zero-cost weapon attachment pilot', () => {
  it('is draft-only, local-only, and bound to the canonical right-hand socket', () => {
    expect(recipe.lifecycle).toMatchObject({
      status: 'draft',
      runtimeReady: false,
      promotionEligible: false,
      humanReviewRequired: true,
    });
    expect(recipe.costPolicy).toEqual({
      currencyBudget: 0,
      networkAllowed: false,
      paidServicesAllowed: false,
    });
    expect(recipe.attachment).toMatchObject({
      mode: 'rigid_socket',
      skeletonId: 'humanoid_game_v2',
      bindPoseId: 'a_pose_v2',
      targetSocket: 'socket_hand_R',
      socketParentBone: 'hand_R',
      gripNode: 'weapon_grip_socket_hand_R',
      localGripTranslation: [0, 0, 0],
    });
    expect(recipe.outputPolicy).toMatchObject({
      ignored: true,
      writeRuntimeIndex: false,
      writeApprovedManifest: false,
      writePublicModels: false,
    });
  });

  it('prefers the CC0 culturalibre hammer and keeps the cleaver project-original', () => {
    expect(recipe.preferredHammerSource).toMatchObject({
      packId: 'equipment01',
      license: 'CC0-1.0',
      author: 'culturalibre',
      relativeMarker: 'clothes/culturalibre_war_hammer/culturalibre_war_hammer.mhclo',
      useWhenInstalled: true,
    });
    const hammer = recipe.weapons.find((weapon: { kind: string }) => weapon.kind === 'hammer');
    const cleaver = recipe.weapons.find((weapon: { kind: string }) => weapon.kind === 'cleaver');
    expect(hammer).toMatchObject({
      bodyFamily: 'civic_humanoid_v2',
      sourcePreference: 'preferredHammerSource',
    });
    expect(cleaver).toMatchObject({
      bodyFamily: 'mire_brutish_v1',
      sourcePreference: 'original_project_mesh',
    });
  });
});
