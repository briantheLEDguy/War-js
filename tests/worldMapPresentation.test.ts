import { describe, expect, test, vi } from 'vitest';
import { applyZonePaths } from '../src/world/PathKit';
import type { PathDefinition, ZoneDefinition } from '../src/world/ZoneLoader';
import { drawPaths, findMapHoverTarget, MAP_CANVAS_OVERSCAN, prepareVisibleZoneCanvas } from '../src/ui/hud/WorldMapPanel';
import { isMapPathProp, layoutMapSymbols, mapResolutionScale, ZONE_MAP_MAX_ZOOM } from '../src/ui/hud/worldMapPresentation';

describe('zone atlas presentation', () => {
  const paths: PathDefinition[] = [
    { id: 'main', style: 'dirt_trail', width: 6, points: [{ x: -40, z: 0 }, { x: 0, z: 0 }, { x: 40, z: 20 }] },
    { id: 'branch', style: 'cobblestone_avenue', width: 4, points: [{ x: 0, z: 0 }, { x: 0, z: 30 }] },
  ];

  test('excludes all generated road chunks and junction caps from landmark icons', () => {
    const zone = applyZonePaths({ paths, props: [] } as unknown as ZoneDefinition);
    expect(zone.props.length).toBeGreaterThan(10);
    expect(zone.props.every(isMapPathProp)).toBe(true);
    expect(isMapPathProp({ kind: 'bridge', x: 0, z: 0 })).toBe(false);
    expect(isMapPathProp({ kind: 'building', x: 0, z: 0 })).toBe(false);
  });

  test('draws continuous network layers with matching junction coordinates and no dashes', () => {
    const strokes: Array<{ width: number; points: number[][] }> = [];
    let points: number[][] = [];
    const ctx = {
      save: vi.fn(), restore: vi.fn(), rect: vi.fn(), clip: vi.fn(),
      lineWidth: 0, lineCap: '', lineJoin: '', strokeStyle: '',
      beginPath: () => { points = []; },
      moveTo: (x: number, y: number) => points.push([x, y]),
      lineTo: (x: number, y: number) => points.push([x, y]),
      stroke: () => strokes.push({ width: ctx.lineWidth, points }),
    };
    drawPaths(ctx as unknown as CanvasRenderingContext2D, paths, {
      size: 100, scale: 1, screenScale: 1, left: 0, top: 0, width: 100, height: 100,
      toCanvas: p => ({ x: p.x, y: p.z }),
    });
    expect(strokes).toHaveLength(6);
    expect(strokes.map(stroke => stroke.width)).toEqual([8, 6, 6, 4, 3, 2]);
    expect(strokes[0].points[1]).toEqual(strokes[1].points[0]);
    expect(ctx.lineJoin).toBe('round');
    expect(ctx.lineCap).toBe('round');
  });

  test.each([0.72, 1, 2.15, 8])('separates coincident objectives and resources at %sx zoom', scale => {
    const symbols = Array.from({ length: 40 }, (_, i) => ({
      id: `marker-${i}`, position: { x: 100, y: 120 }, radius: 12 / scale, priority: i === 0,
    }));
    const layout = layoutMapSymbols(symbols, scale);
    expect(layout[0].position).toEqual(symbols[0].position);
    expect(layoutMapSymbols([...symbols].reverse(), scale)).toEqual(layout);
    for (let i = 0; i < layout.length; i++) for (let j = i + 1; j < layout.length; j++) {
      expect(Math.hypot(layout[i].position.x - layout[j].position.x, layout[i].position.y - layout[j].position.y) * scale).toBeGreaterThanOrEqual(27 - 1e-8);
    }
    expect(symbols.every(symbol => symbol.position.x === 100 && symbol.position.y === 120)).toBe(true);
  });

  test('leaves separated locations in place and hits the drawn symbol instead of a nearby priority marker', () => {
    const symbols = [
      { id: 'objective', position: { x: 20, y: 20 }, radius: 10, priority: true, label: 'Objective', kind: 'Objective', color: '#fff' },
      { id: 'resource', position: { x: 25, y: 20 }, radius: 9, label: 'Ore', kind: 'Resource', color: '#fff' },
    ];
    expect(findMapHoverTarget(symbols, 25, 20)?.id).toBe('resource');
    const layout = layoutMapSymbols(symbols, 1);
    for (const symbol of layout) expect(findMapHoverTarget(layout, symbol.position.x, symbol.position.y)?.id).toBe(symbol.id);
    const separated = symbols.map((symbol, i) => ({ ...symbol, position: { x: i * 100, y: 100 } }));
    expect(layoutMapSymbols(separated, 1)).toEqual(separated);
  });

  test('supports item-level zoom while bounding a high-DPI backing store', () => {
    expect(ZONE_MAP_MAX_ZOOM).toBe(8);
    const resolution = mapResolutionScale(1200, 800, 2, ZONE_MAP_MAX_ZOOM);
    expect(1200 * resolution).toBe(4096);
    expect(800 * resolution).toBeLessThan(4096);
    expect(mapResolutionScale(600, 400, 2, 1)).toBe(2);
  });

  test.each([1, 2, 8])('rasterizes only the visible high-DPI window at %sx zoom', zoom => {
    vi.stubGlobal('window', { devicePixelRatio: 2 });
    try {
      const ctx = { setTransform: vi.fn(), clearRect: vi.fn(), fillRect: vi.fn() };
      const canvas = {
        width: 0, height: 0, style: {},
        parentElement: { clientWidth: 800, clientHeight: 600, getBoundingClientRect: () => ({ left: 400 - 400 * zoom, top: 300 - 300 * zoom }) },
        closest: () => ({ clientLeft: 1, clientTop: 1, clientWidth: 800, clientHeight: 600, getBoundingClientRect: () => ({ left: -1, top: -1, width: 817, height: 617 }) }),
      };
      const result = prepareVisibleZoneCanvas(canvas as unknown as HTMLCanvasElement, ctx as unknown as CanvasRenderingContext2D, zoom);
      expect(result).toEqual({ width: 800, height: 600 });
      const gutter = zoom === 1 ? 0 : MAP_CANVAS_OVERSCAN;
      expect([canvas.width, canvas.height]).toEqual([(800 + gutter * 2) * 2, (600 + gutter * 2) * 2]);
      expect(ctx.setTransform).toHaveBeenLastCalledWith(zoom * 2, 0, 0, zoom * 2, -(400 * zoom - 400 - gutter) * 2, -(300 * zoom - 300 - gutter) * 2);
      expect(ctx.setTransform).toHaveBeenNthCalledWith(1, 1, 0, 0, 1, 0, 0);
      expect(ctx.clearRect).toHaveBeenCalledWith(0, 0, canvas.width, canvas.height);
      expect(ctx.fillRect).toHaveBeenCalledWith(0, 0, canvas.width, canvas.height);
      // A same-size redraw must also erase pixels from the previous crop.
      prepareVisibleZoneCanvas(canvas as unknown as HTMLCanvasElement, ctx as unknown as CanvasRenderingContext2D, zoom);
      expect(ctx.clearRect).toHaveBeenCalledTimes(2);
    } finally {
      vi.unstubAllGlobals();
    }
  });

  test.each([0, 600])('clips buffered crops to the scene at the top/bottom edge (%s)', scrollTop => {
    vi.stubGlobal('window', { devicePixelRatio: 1 });
    try {
      const ctx = { setTransform: vi.fn(), clearRect: vi.fn(), fillRect: vi.fn() };
      const canvas = {
        width: 0, height: 0, style: {} as Record<string, string>,
        parentElement: { clientWidth: 800, clientHeight: 600, getBoundingClientRect: () => ({ left: 0, top: -scrollTop }) },
        closest: () => ({ clientLeft: 0, clientTop: 0, clientWidth: 800, clientHeight: 600, getBoundingClientRect: () => ({ left: 0, top: 0 }) }),
      };
      prepareVisibleZoneCanvas(canvas as unknown as HTMLCanvasElement, ctx as unknown as CanvasRenderingContext2D, 2);
      const top = Number.parseFloat(canvas.style.top), height = Number.parseFloat(canvas.style.height);
      expect(top).toBeGreaterThanOrEqual(0);
      expect(top + height).toBeLessThanOrEqual(600);
      expect(height * 2).toBe(600 + MAP_CANVAS_OVERSCAN);
    } finally {
      vi.unstubAllGlobals();
    }
  });
});
