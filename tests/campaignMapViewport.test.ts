import { describe, expect, test } from 'vitest';
import {
  calculateEffectiveMapScale,
  calculateMapFitScale,
  calculateMapViewportLayout,
  calculateZoomAnchor,
  calculateZoomedScroll,
  shouldStartMapPan,
} from '../src/ui/hud/campaignMapViewport';
import { campaignMapNodeTarget } from '../src/ui/hud/campaignMapModel';

describe('campaign map viewport geometry', () => {
  test('fits wide, tall, and already-fitting scenes without exceeding unity scale', () => {
    expect(calculateMapFitScale({ width: 900, height: 500 }, { width: 1200, height: 600 })).toBeCloseTo(0.74, 2);
    expect(calculateMapFitScale({ width: 500, height: 900 }, { width: 600, height: 1200 })).toBeCloseTo(0.74, 2);
    expect(calculateMapFitScale({ width: 900, height: 700 }, { width: 600, height: 400 })).toBe(1);
  });

  test('combines fitted scale and user zoom and centers smaller scenes', () => {
    expect(calculateEffectiveMapScale(0.5, 1)).toBe(0.5);
    expect(calculateEffectiveMapScale(0.5, 1.8)).toBeCloseTo(0.9);

    expect(calculateMapViewportLayout(
      { width: 1000, height: 700 },
      { width: 600, height: 400 },
      1,
    )).toMatchObject({ width: 1000, height: 700, offsetX: 200, offsetY: 150 });
  });

  test('expands the physical scroll surface when zoomed and preserves relative spacing', () => {
    const layout = calculateMapViewportLayout(
      { width: 500, height: 400 },
      { width: 600, height: 800 },
      1.5,
    );
    expect(layout).toMatchObject({ width: 900, height: 1200, offsetX: 0, offsetY: 0 });

    const firstMarker = { x: 120, y: 240 };
    const secondMarker = { x: 220, y: 340 };
    expect({
      x: (secondMarker.x - firstMarker.x) * layout.scale,
      y: (secondMarker.y - firstMarker.y) * layout.scale,
    }).toEqual({ x: 150, y: 150 });
  });

  test('keeps the point below the cursor fixed while zooming', () => {
    const anchor = calculateZoomAnchor(
      { left: 180, top: 90 },
      { x: 240, y: 160 },
      0.75,
    );
    const scroll = calculateZoomedScroll(anchor, 1.2);
    expect(scroll.left + 240).toBeCloseTo(anchor.contentX * 1.2);
    expect(scroll.top + 160).toBeCloseTo(anchor.contentY * 1.2);
  });

  test('navigates node clicks one tier deeper and leaves interactive buttons free to click', () => {
    expect(campaignMapNodeTarget('campaign', 'dawnline_expanse')).toEqual({
      level: 'route',
      zoneId: 'dawnline_expanse',
    });
    expect(campaignMapNodeTarget('route', 'dawnline_expanse')).toEqual({
      level: 'zone',
      zoneId: 'dawnline_expanse',
    });
    expect(shouldStartMapPan(0, true)).toBe(false);
    expect(shouldStartMapPan(0, false)).toBe(true);
    expect(shouldStartMapPan(2, false)).toBe(false);
  });
});
