import { describe, expect, it } from "vitest";
import {
  animationProfileForGroup,
  auditAnimationClipNames,
  REQUIRED_ANIMATION_CLIPS,
} from "../scripts/blender-character-pipeline/tools/roster-generation.mjs";

describe("roster animation stage", () => {
  it("requires animation-free bodies for separate native animation import", () => {
    const audit = auditAnimationClipNames(REQUIRED_ANIMATION_CLIPS);
    expect(audit.matches).toBe(true);
    expect(audit.missing).toEqual([]);
    expect(audit.unexpected).toEqual([]);
    expect(REQUIRED_ANIMATION_CLIPS).toEqual([]);
    expect(auditAnimationClipNames(["idle"]).matches).toBe(false);
  });

  it("reports missing and unexpected clips instead of silently accepting a partial pack", () => {
    const audit = auditAnimationClipNames(["idle", "walk", "custom_preview"], ["idle", "walk", "run"]);
    expect(audit.matches).toBe(false);
    expect(audit.missing).toEqual(["run"]);
    expect(audit.unexpected).toEqual(["custom_preview"]);
  });

  it("routes four approved characters to supplied styles and leaves unknown rigs unassigned", () => {
    expect(animationProfileForGroup({ key: "battle_prelate" })).toBe("two");
    expect(animationProfileForGroup({ key: "warbrute" })).toBe("shield");
    expect(animationProfileForGroup({ key: "sunfire_templar" })).toBe("shield");
    expect(animationProfileForGroup({ key: "ember_arcanist" })).toBe("spell");
    expect(animationProfileForGroup({ key: "future_character" })).toBeNull();
  });
});
