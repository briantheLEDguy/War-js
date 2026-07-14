import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import path from "node:path";
import {
  classifyWearable,
  getResource,
  socketFor,
  validateStageRequest,
} from "../scripts/blender-character-pipeline/pipeline-tools/character-contract.mjs";
import { inspectGlb } from "../scripts/blender-character-pipeline/pipeline-tools/inspect-glb.mjs";

describe("typed modular-character contract", () => {
  it("keeps rigid, skinned, and loose attachment methods distinct", () => {
    expect(classifyWearable({ slot: "weapon", kind: "rigid", method: "bone_parent" }).kind).toBe("rigid");
    expect(classifyWearable({ slot: "chest", kind: "skinned", method: "data_transfer_nearest_face_interpolated" }).kind).toBe("skinned");
    expect(classifyWearable({ slot: "cape", kind: "loose", method: "cloth_pinned" }).kind).toBe("loose");
    expect(() => classifyWearable({ slot: "chest", kind: "rigid" })).toThrow(/classified as skinned/);
    expect(() => validateStageRequest("fit_wearable", { assetId: "wep.test.sabre", slot: "weapon", kind: "rigid", method: "bone_parent" })).toThrow(/attach_rigid_item/);
  });

  it("resolves semantic sockets from the canonical socket map", () => {
    expect(socketFor("socket_hand_R").parentBone).toBe("hand_R");
    expect(socketFor("socket_belt_L").parentBone).toBe("hips");
    expect(getResource("rig://humanoid-v1/sockets").semanticAliases.hand_r_weapon).toBe("socket_hand_R");
  });

  it("requires the canonical body and rest-pose pair for base assembly", () => {
    const request = validateStageRequest("assemble_base_character", {
      bodyFamily: "civic_humanoid_v2",
      bodyVariant: "m",
    });
    expect(request.skeletonId).toBe("humanoid_game_v2");
    expect(request.bindPoseId).toBe("a_pose_v2");
    expect(() => validateStageRequest("assemble_base_character", { bodyFamily: "unknown", bodyVariant: "m" })).toThrow(/body archetype/);
  });

  it("exposes stable pose/export resources and a real generated fixture", () => {
    const posePack = getResource("test://pose-packs/core").posePacks[0];
    expect(posePack.poses).toContain("attack_melee");
    expect(getResource("export://profiles").profiles.runtime_glb_v1.maxInfluencesPerVertex).toBe(4);
    const fixture = path.resolve("scripts/blender-character-pipeline/test-assets/test_socketed_sabre_civic_m.glb");
    const indexPath = path.resolve("scripts/blender-character-pipeline/test-assets/fixture-index.json");
    expect(readFileSync(indexPath, "utf8")).toContain("chr.test.civic.socketed_sabre");
    const inspection = inspectGlb(fixture, {
      skeletonId: "humanoid_game_v2",
      requiredNodes: ["socket_hand_R", "weapon_grip_socket_hand_R", "weapon_strike_head"],
      requiredAnimations: ["idle", "walk", "attack_melee"],
      requireSkin: true,
      minJointCount: 56,
    });
    expect(inspection.valid).toBe(true);
  });
});
