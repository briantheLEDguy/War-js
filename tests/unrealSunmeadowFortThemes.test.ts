import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { redesignT1 } from '../scripts/unreal/t1-layouts';
import { sunmeadowFortThemes } from '../scripts/unreal/sunmeadow-fort-themes';
const source = () => redesignT1(JSON.parse(readFileSync('public/assets/maps/sunmeadow_march.json', 'utf8')));
describe('Sunmeadow faction fort authoring', () => {
  it('retains gameplay assemblies and authors different faction silhouettes and materials', () => {
    const zone = source(), before = structuredClone(zone), themes = sunmeadowFortThemes(zone);
    expect(zone).toEqual(before); expect(themes.map(t => t.objectiveId)).toEqual(zone.orvrLayout!.keeps.map(k => k.objectiveId));
    expect(themes[0].additions).toHaveLength(2); expect(themes[1].additions).toHaveLength(4);
    expect(themes[0].additions[0].assetKey).not.toBe(themes[1].additions[0].assetKey);
    expect(themes[0].wallMaterial).not.toBe(themes[1].wallMaterial);
    expect(themes[1].gatehouseMaterials).toHaveLength(10);
    expect(themes[0].additions.every(a => a.uniformScale === 1)).toBe(true);
    expect(themes[1].additions.every(a => a.uniformScale > 1 && a.uniformScale < 2)).toBe(true);
    expect(themes.every(t => !t.appearanceApproved && !t.gameplayAnchorsMoved)).toBe(true);
  });
  it('rotates additions with a complete retained keep', () => {
    const zone = source(), first = sunmeadowFortThemes(zone)[0], keep = zone.orvrLayout!.keeps[0];
    keep.heading = (keep.heading ?? 0) + Math.PI / 2; const rotated = sunmeadowFortThemes(zone)[0];
    first.additions.forEach((p, i) => {
      expect(rotated.additions[i].x - keep.x).toBeCloseTo(p.z - keep.z);
      expect(rotated.additions[i].z - keep.z).toBeCloseTo(-(p.x - keep.x));
    });
  });
  it('uses the retained zero-heading default and rejects invalid rotations', () => {
    const zone = source(), before = sunmeadowFortThemes(zone);
    delete zone.orvrLayout!.keeps[0].heading;
    expect(sunmeadowFortThemes(zone)).toEqual(before);
    zone.orvrLayout!.keeps[0].heading = NaN;
    expect(() => sunmeadowFortThemes(zone)).toThrow('Invalid themed keep transform');
  });
  it('rejects missing or duplicate-realm keeps', () => {
    const zone = source(); zone.orvrLayout!.keeps[1].realm = 'aegis';
    expect(() => sunmeadowFortThemes(zone)).toThrow('both retained keeps');
  });
});