import { readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { describe, expect, test } from 'vitest';
import * as THREE from 'three';
import { cityFallback, architectureLods } from '../src/world/CityArchitecture';
import { cityHeightAt } from '../src/world/CityElevation';
import type { ZoneDefinition } from '../src/world/ZoneLoader';
import type { AssetLoader } from '../src/game/AssetLoader';
import { addAegisCivicDecorations, CIVIC_KINDS, civicPositionClear, civicGroundHeight, distanceToCivicSegment } from '../scripts/campaign/aegis-civic-decorations.mjs';

const zone: ZoneDefinition = JSON.parse(readFileSync('public/assets/maps/aegis_capital.json', 'utf8'));
const props = zone.props.filter(p => p.kind.startsWith('aegis_civic_') && p.kind !== 'aegis_civic_hall');
const standing = props.filter(p => p.colliders?.length);

describe('Aegis civic decorations', () => {
  test('covers all districts with lighting, original artwork and furniture', () => {
    expect(new Set(props.map(p => p.kind)).size).toBe(10);
    expect(new Set(props.map(p => p.id)).size).toBe(props.length);
    expect(zone.cityCivicDecorations!.mountedLanterns).toBe(104);
    expect(zone.cityCivicDecorations!.streetlights).toBeGreaterThanOrEqual(25);
    for (const counts of Object.values(zone.cityCivicDecorations!.districtCounts)) {
      expect(counts.lights).toBeGreaterThanOrEqual(8);
      expect(counts.artwork).toBeGreaterThanOrEqual(1);
      expect(counts.furniture).toBeGreaterThanOrEqual(2);
    }
  });

  test('preserves the four shop portal identities and original names', () => {
    const labels = ['The Sable Lantern', 'The Lockkeeper', 'Cinderleaf Apothecary', 'Three Seals Exchange'];
    const signs = props.filter(p => p.kind.startsWith('aegis_civic_sign_'));
    expect(signs.map(p => p.interaction!.label).sort()).toEqual(labels.sort());
    for (const sign of signs) {
      expect(sign.interaction!.type).toBe('house_portal');
      expect(sign.interaction!.id).toMatch(/^aegis_city_enter_/);
      expect(sign.interaction!.maxDistance).toBe(5);
    }
  });

  test('keeps the full road width, canal edge and service approaches clear', () => {
    for (const p of standing) {
      const c = p.colliders![0];
      const radius = Math.hypot(c.width, c.depth) / 2;
      for (const path of zone.paths!) for (let i = 1; i < path.points.length; i++) {
        expect(distanceToCivicSegment(p, path.points[i-1], path.points[i]), p.id)
          .toBeGreaterThan(path.width/2 + radius + .3);
      }
      for (const canal of zone.canals!) {
        const dx = Math.max(0, Math.abs(p.x-canal.x)-canal.width/2);
        const dz = Math.max(0, Math.abs(p.z-canal.z)-canal.depth/2);
        expect(Math.hypot(dx,dz), p.id).toBeGreaterThan(radius);
      }
      for (const service of [...zone.npcs!, ...zone.craftingStations!, ...zone.resourceNodes!]) {
        expect(Math.hypot(p.x-service.x,p.z-service.z), p.id).toBeGreaterThan(radius + 2.5);
      }
    }
  });

  test('clearance respects rotated and scaled collider offsets', () => {
    const fixture = {spawnPoint:{x:100,z:100},canals:[],npcs:[],craftingStations:[],resourceNodes:[],
      rvrObjectives:[],paths:[],props:[{x:0,z:0,rotY:Math.PI/2,scale:2,
        colliders:[{x:5,z:0,width:1,depth:3}]}]};
    expect(civicPositionClear(fixture,{x:0,z:10},.5)).toBe(false);
    expect(civicPositionClear(fixture,{x:0,z:0},.5)).toBe(true);
  });

  test('places freestanding decorations on level ground and matches runtime height sampling', () => {
    for (const p of standing) {
      const height = cityHeightAt(zone.cityElevation!,zone.size,p.x,p.z);
      expect(civicGroundHeight(zone,p.x,p.z)).toBeCloseTo(height,6);
      const c=p.colliders![0], a=p.rotY ?? 0;
      for (const x of [-c.width/2,0,c.width/2]) for (const z of [-c.depth/2,0,c.depth/2]) {
        const sample=cityHeightAt(zone.cityElevation!,zone.size,
          p.x+x*Math.cos(a)+z*Math.sin(a),p.z-x*Math.sin(a)+z*Math.cos(a));
        expect(Math.abs(sample-height),p.id).toBeLessThan(.12);
      }
    }
    const slope={size:2,cityElevation:{segments:1,heights:[0,2,0,2]},
      spawnPoint:{x:100,z:100},canals:[],npcs:[],craftingStations:[],resourceNodes:[],rvrObjectives:[],paths:[],props:[]};
    expect(civicPositionClear(slope,{x:0,z:0},.5)).toBe(false);
  });

  test('does not decorate the other realm', () => {
    const rift = {id:'riftspire_capital', props:[{id:'existing'}]};
    const before = structuredClone(rift);
    addAegisCivicDecorations(rift);
    expect(rift).toEqual(before);
  });

  test.each(CIVIC_KINDS)('ships approved, hash-matching LODs for %s', (kind: string) => {
    const name = `prop_aegis_civic_${kind}`;
    const manifest = JSON.parse(readFileSync(`scripts/blender-character-pipeline/data/approved-assets/${name}.approved.json`, 'utf8'));
    expect(manifest.approvalState).toBe('approved');
    let previous = Infinity;
    for (const level of [0,1,2]) {
      const file = name + (level ? `_lod${level}` : '');
      const bytes = readFileSync(`public/assets/models/${file}.glb`);
      const qc = JSON.parse(readFileSync(`public/assets/models/${file}.qc.json`, 'utf8'));
      const sha = createHash('sha256').update(bytes).digest('hex');
      expect(qc.qcPassed).toBe(true);
      expect(qc.modelSha256).toBe(sha);
      if (!level) expect(manifest.hashes.modelSha256).toBe(sha);
      expect(qc.lod.triangles).toBeLessThan(previous);
      previous = qc.lod.triangles;
      const gltf = JSON.parse(bytes.subarray(20, 20+bytes.readUInt32LE(12)).toString());
      expect(gltf.materials.length).toBeLessThanOrEqual(8);
      // Geometry and material factors are self-contained; no added texture fetches.
      expect(gltf.images ?? []).toHaveLength(0);
    }
  });

  test.each(CIVIC_KINDS)('keeps missing %s assets small and visible at every LOD', async (kind: string) => {
    const name = `aegis_civic_${kind}`;
    const base = cityFallback(name);
    const loader = {loadModel:async (_: string, fallback: () => THREE.Object3D) => fallback()} as unknown as AssetLoader;
    const lod = await architectureLods(base,['missing-lod1.glb','missing-lod2.glb'],name,loader);
    expect(lod.levels).toHaveLength(3);
    for (const level of lod.levels) {
      const bounds = new THREE.Box3().setFromObject(level.object);
      expect(bounds.isEmpty()).toBe(false);
      const size = bounds.getSize(new THREE.Vector3());
      expect(size.x).toBeLessThan(3.1);
      expect(size.z).toBeLessThan(2.2);
      expect(size.y).toBeLessThan(4.7);
    }
  });
});
