import { describe, expect, it } from 'vitest';
import { PointLight, Scene } from 'three';
import { CityLighting } from '../src/world/CityLighting';
import type { CraterCityDefinition } from '../src/world/CraterCity';

describe('bounded crater room lighting', () => {
  it('selects lights on the occupied floor, reuses slots and disposes them', () => {
    const scene = new Scene();
    const city = { lights: [0, 2, 4, 6].map(x => ({ x, y: -101, z: 0, color: '#ffc582', intensity: 100, distance: 40 })) } as CraterCityDefinition;
    const lighting = new CityLighting(city, scene);
    lighting.update({ x: 0, y: -105, z: 0 });
    const slots = [...scene.children] as PointLight[];
    expect(slots).toHaveLength(2);
    expect(slots.map(l => l.position.x)).toEqual([0, 2]);
    expect(slots.every(l => l.intensity === 100 && !l.castShadow)).toBe(true);
    lighting.update({ x: 0, y: -130, z: 0 });
    expect(slots.every(l => l.intensity === 0)).toBe(true);
    lighting.update({ x: 6, y: -105, z: 0 });
    expect(scene.children).toEqual(slots);
    expect(slots.map(l => l.position.x)).toEqual([6, 4]);
    lighting.dispose();
    expect(scene.children).toHaveLength(0);
  });
});
