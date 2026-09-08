import { describe, expect, it } from 'vitest';
import { drawCityMap } from '../src/ui/hud/cityMap';
import type { ZoneDefinition } from '../src/world/ZoneLoader';

describe('crater map elevation', () => {
  it('mutes the remote part of a stair route while highlighting the current floor', () => {
    const colors: unknown[] = [];
    const context = { strokeStyle: '', save() {}, restore() {}, beginPath() {}, arc() {}, clip() {}, moveTo() {}, lineTo() {},
      stroke() { colors.push(this.strokeStyle); } };
    const zone = { props: [], craterCity: { levels: [], routes: [{ width: 6, points: [
      { x: 0, y: -105, z: 0 }, { x: 10, y: -105, z: 0 },
      { x: 20, y: -150, z: 0 }, { x: 30, y: -175, z: 0 },
    ] }] } } as ZoneDefinition;
    drawCityMap(context as unknown as CanvasRenderingContext2D, zone, { x: 0, y: -105, z: 0 }, 50, 50, 40, 100);
    expect(colors).toEqual(['#debf91', '#debf91', '#454753']);
  });
});
