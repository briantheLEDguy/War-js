import { describe, expect, it } from 'vitest';
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve('authoring/blender/orvr-frontier');
const source = JSON.parse(fs.readFileSync(path.join(root, 'source/frontier_collection.json'), 'utf8'));

describe('authored frontier siege asset source', () => {
  it('retains literal control cages with valid topology and UVs for every face corner', () => {
    expect(Object.keys(source.parts).length).toBeGreaterThanOrEqual(25);
    for (const part of Object.values(source.parts) as any[]) {
      expect(part.source_kind).toBe('literal_authored_control_cage');
      // A fitted cloth repair can legitimately be a six-corner surface;
      // volume is supplied by its retained Solidify finishing modifier.
      expect(part.vertices.length).toBeGreaterThanOrEqual(3);
      expect(part.description.length).toBeGreaterThan(30);
      expect(part.corner_uv.length).toBe(part.faces.length);
      for (const point of part.vertices) {
        expect(point.length).toBe(3);
        expect(point.every(Number.isFinite)).toBe(true);
      }
      for (const [index, face] of part.faces.entries()) {
        expect(face.length).toBeGreaterThanOrEqual(3);
        expect(new Set(face).size).toBe(face.length);
        expect(face.every((vertex: number) => Number.isInteger(vertex) && vertex >= 0 && vertex < part.vertices.length)).toBe(true);
        const origin=part.vertices[face[0]];
        const noncollinear=face.slice(1,-1).some((vertex: number, offset: number) => {
          const a=part.vertices[vertex].map((value: number, axis: number) => value-origin[axis]);
          const b=part.vertices[face[offset+2]].map((value: number, axis: number) => value-origin[axis]);
          return Math.hypot(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])>1e-10;
        });
        expect(noncollinear, `${part.id} face ${index} must have surface area`).toBe(true);
        expect(part.corner_uv[index].length).toBe(face.length);
        expect(part.corner_uv[index].every((uv: number[]) => uv.length === 2 && uv.every((v) => Number.isFinite(v) && v >= 0 && v <= 1))).toBe(true);
      }
    }
  });

  it('resolves finite placements and preserves honest asset limitations', () => {
    expect(Object.keys(source.assets)).toEqual([
      'frontier_supply_wagon', 'frontier_battering_ram', 'frontier_oil_cauldron', 'frontier_field_catapult', 'frontier_keep_gate',
    ]);
    for (const asset of Object.values(source.assets) as any[]) {
      const groups = new Set<string>();
      expect(asset.limitations.length).toBeGreaterThan(0);
      for (const instance of asset.instances) {
        if (instance.group) groups.add(instance.group);
        else expect(source.parts[instance.part]).toBeDefined();
        if (instance.parent) expect(groups.has(instance.parent)).toBe(true);
        for (const key of ['location', 'rotation_degrees', 'scale']) {
          expect(instance[key].length).toBe(3);
          expect(instance[key].every(Number.isFinite)).toBe(true);
        }
        expect(instance.scale.every((v: number) => v !== 0)).toBe(true);
      }
    }
  });

  it('does not substitute primitive generation or claim review approval', () => {
    for (const filename of fs.readdirSync(path.join(root, 'tools')).filter((name) => name.endsWith('.py'))) {
      const script = fs.readFileSync(path.join(root, 'tools', filename), 'utf8');
      expect(script).not.toMatch(/bpy\.ops\.mesh\.primitive_|bmesh\.ops\.create_(?:cube|uvsphere|icosphere|cone|grid)/);
    }
    expect(source.review_status).toBe('unreviewed_source');
    const code = fs.readFileSync(path.join(root, 'tools/validate_collection.mjs'), 'utf8');
    expect(code).toContain('visualApproval: false');
  });
});
