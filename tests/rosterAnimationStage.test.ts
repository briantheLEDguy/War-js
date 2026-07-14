import { describe, expect, it } from "vitest";
import {
  animationProfileForGroup,
  auditAnimationClipNames,
  REQUIRED_ANIMATION_CLIPS,
} from "../scripts/blender-character-pipeline/tools/roster-generation.mjs";

describe("roster animation stage", () => {
  it("requires the complete canonical nine-clip contract", () => {
    const audit = auditAnimationClipNames(REQUIRED_ANIMATION_CLIPS);
    expect(audit.matches).toBe(true);
    expect(audit.missing).toEqual([]);
    expect(audit.unexpected).toEqual([]);
  });

  it("reports missing and unexpected clips instead of silently accepting a partial pack", () => {
    const audit = auditAnimationClipNames(["idle", "walk", "custom_preview"], ["idle", "walk", "run"]);
    expect(audit.matches).toBe(false);
    expect(audit.missing).toEqual(["run"]);
    expect(audit.unexpected).toEqual(["custom_preview"]);
  });

  it("selects only authored profiles for the two pilot characters", () => {
    expect(animationProfileForGroup({ key: "battle_prelate" })).toBe("battle_prelate_hammer");
    expect(animationProfileForGroup({ key: "warbrute" })).toBe("unarmed");
    expect(animationProfileForGroup({ key: "future_character" })).toBe("unarmed");
  });
});
