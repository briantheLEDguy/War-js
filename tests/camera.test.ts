import * as THREE from 'three';
import { afterEach, describe, expect, test, vi } from 'vitest';
import { FollowCamera } from '../src/game/Camera';
import { resolveCameraCollision } from '../src/game/CameraCollision';
import type { Input } from '../src/game/Input';
import { useGameStore } from '../src/state/gameStore';

const input = {} as Input;
const cameras: FollowCamera[] = [];
const initialSettings = useGameStore.getState().settings;
afterEach(() => {
  for (const camera of cameras.splice(0)) camera.dispose();
  useGameStore.setState({ settings: initialSettings });
});

function event(canvas: EventTarget, type: string, properties: Record<string, unknown>) {
  canvas.dispatchEvent(Object.assign(new Event(type, { cancelable: true }), properties));
}

function makeCamera(indoor = false) {
  const canvas = new EventTarget();
  const camera = new FollowCamera(canvas as HTMLElement, 16 / 9);
  cameras.push(camera);
  camera.setIndoorMode(indoor);
  const drag = (dy: number) => {
    event(canvas, 'pointerdown', { pointerType: 'mouse', button: 0, buttons: 1, pointerId: 1, clientX: 0, clientY: 0 });
    event(canvas, 'pointermove', { pointerType: 'mouse', buttons: 1, movementX: 0, movementY: dy, clientX: 0, clientY: dy });
    event(canvas, 'pointerup', { pointerType: 'mouse', buttons: 0, pointerId: 1 });
  };
  return { camera, canvas, drag };
}

function box(x: number, y: number, z: number, width = 2, height = 2, depth = 1) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(width, height, depth), new THREE.MeshBasicMaterial());
  mesh.position.set(x, y, z);
  return mesh;
}

describe('follow camera controls', () => {
  test('reaches a level horizon without an artificial downward offset', () => {
    const { camera, drag } = makeCamera();
    drag(150);
    camera.update(new THREE.Vector3(), input, [], () => 0);
    expect(camera.camera.getWorldDirection(new THREE.Vector3()).y).toBeCloseTo(0);
  });
  test.each([false, true])('looks nearly straight up and down with mouse indoors=%s', indoor => {
    const { camera, drag } = makeCamera(indoor);
    drag(2000);
    camera.update(new THREE.Vector3(), input, [], () => 0);
    expect(camera.camera.getWorldDirection(new THREE.Vector3()).y).toBeGreaterThan(0.999);
    expect(camera.camera.position.y).toBeGreaterThanOrEqual(0.45);
    drag(-4000);
    camera.update(new THREE.Vector3(), input, [], () => 0);
    expect(camera.camera.getWorldDirection(new THREE.Vector3()).y).toBeLessThan(-0.999);
  });

  test('touch orbit uses the full range and inversion settings', () => {
    const { camera, canvas } = makeCamera();
    const touch = { identifier: 1, clientX: 0, clientY: 0 };
    event(canvas, 'touchstart', { changedTouches: [touch], touches: [touch] });
    event(canvas, 'touchmove', { touches: [{ ...touch, clientY: 2000 }] });
    camera.update(new THREE.Vector3(), input);
    expect(camera.camera.getWorldDirection(new THREE.Vector3()).y).toBeGreaterThan(0.999);
    useGameStore.setState({ settings: { ...initialSettings, invertCameraY: true } });
    event(canvas, 'touchmove', { touches: [{ ...touch, clientY: 6000 }] });
    camera.update(new THREE.Vector3(), input);
    expect(camera.camera.getWorldDirection(new THREE.Vector3()).y).toBeLessThan(-0.999);
  });

  test('restores outdoor angle and zoom after leaving an interior', () => {
    const { camera, drag } = makeCamera();
    drag(230);
    camera.update(new THREE.Vector3(), input);
    const before = camera.camera.position.clone();
    camera.setIndoorMode(true);
    drag(-3000);
    camera.setIndoorMode(false);
    camera.update(new THREE.Vector3(), input);
    expect(camera.camera.position.distanceTo(before)).toBeLessThan(0.00001);
  });

  test('restores requested zoom after moving away from an obstruction', () => {
    const { camera } = makeCamera();
    camera.update(new THREE.Vector3(), input);
    const before = camera.camera.position.clone();
    camera.update(new THREE.Vector3(), input, [], undefined, [box(0, 2, 3, 5, 5)]);
    expect(camera.camera.position.length()).toBeLessThan(before.length());
    camera.update(new THREE.Vector3(), input);
    expect(camera.camera.position.distanceTo(before)).toBeLessThan(0.00001);
  });
});

describe('camera obstruction resolution', () => {
  const focus = new THREE.Vector3(0, 2, 0);
  const desired = new THREE.Vector3(0, 2, 8);
  const collider = { id: 'wall', x: 0, z: 4, width: 4, depth: 1, rotY: 0, minY: 0, maxY: 3 };

  test('stops before a finite or rotated collider', () => {
    for (const rotY of [0, Math.PI / 4]) {
      const result = resolveCameraCollision(focus, desired, [{ ...collider, rotY }]);
      expect(result.z).toBeGreaterThan(0);
      expect(result.z).toBeLessThan(3.2);
      expect(result.y).toBe(2);
    }
  });

  test('can orbit over low props and under overhead geometry', () => {
    for (const bounds of [{ minY: 0, maxY: 1 }, { minY: 3, maxY: 5 }]) {
      expect(resolveCameraCollision(focus, desired, [{ ...collider, ...bounds }])).toEqual(desired);
    }
  });

  test('blocks an elevated camera even when the player is below the obstacle', () => {
    const result = resolveCameraCollision(focus, new THREE.Vector3(0, 8, 8), [{ ...collider, minY: 4, maxY: 7 }]);
    expect(result.z).toBeLessThan(3.2);
  });

  test('handles overlapping blockers without a sideways jump or minimum-distance clipping', () => {
    const result = resolveCameraCollision(focus, desired, [{ ...collider, z: 0 }, { ...collider, x: 0.1, z: 0 }]);
    expect(result).toEqual(focus);
  });

  test('finds an intervening ridge even when the endpoint is above ground', () => {
    const terrain = (_x: number, z: number) => z > 2 && z < 3 ? 4 : 0;
    const result = resolveCameraCollision(focus, desired, [], terrain);
    expect(result.z).toBeLessThanOrEqual(2);
    expect(result.z).toBeGreaterThan(1.9);
  });

  test('keeps steep upward views above terrain without lifting them into a ceiling', () => {
    const result = resolveCameraCollision(focus, new THREE.Vector3(0, -10, 0.01), [], () => 0, [box(0, 3, 0, 10, 0.1, 10)]);
    expect(result.y).toBeGreaterThanOrEqual(0.45);
    expect(result.y).toBeLessThan(0.451);
  });

  test('detects arbitrary props and ceiling meshes without authored colliders', () => {
    expect(resolveCameraCollision(focus, desired, [], undefined, [box(0, 2, 4)]).z).toBeLessThan(3.2);
    const result = resolveCameraCollision(focus, new THREE.Vector3(0, 9, 0), [], undefined, [box(0, 4, 0, 8, 0.2, 8)]);
    expect(result.y).toBeLessThan(3.6);
    expect(result.y).toBeGreaterThan(3.4);
  });

  test('protects the near plane when the center ray misses an edge', () => {
    const result = resolveCameraCollision(focus, desired, [], undefined, [box(0.4, 2, 4, 0.2, 4, 1)]);
    expect(result.z).toBeLessThan(3.2);
  });

  test('uses hidden instancing sources and high-detail LOD geometry', () => {
    const lod = new THREE.LOD();
    const wall = box(0, 2, 4);
    wall.visible = false;
    lod.addLevel(wall, 0);
    lod.addLevel(new THREE.Group(), 10);
    lod.visible = false;
    expect(resolveCameraCollision(focus, desired, [], undefined, [lod]).z).toBeLessThan(3.2);
  });

  test('allows travel through an opening within a large object bounding box', () => {
    const arch = new THREE.Group();
    arch.add(box(-3, 2, 4), box(3, 2, 4), box(0, 5, 4, 8, 1));
    expect(resolveCameraCollision(focus, desired, [], undefined, [arch])).toEqual(desired);
  });

  test('detects a back-facing single-sided surface without mutating materials', () => {
    const wall = new THREE.Mesh(new THREE.PlaneGeometry(5, 5), new THREE.MeshBasicMaterial());
    wall.position.set(0, 2, 4);
    const result = resolveCameraCollision(focus, desired, [], undefined, [wall]);
    expect(result.z).toBeCloseTo(3.65);
    expect(wall.material.side).toBe(THREE.FrontSide);
  });

  test('uses current transforms when a prop moves or an animated gate opens', () => {
    const gate = box(0, 2, 4);
    expect(resolveCameraCollision(focus, desired, [], undefined, [gate]).z).toBeLessThan(3.2);
    gate.position.y = 10;
    expect(resolveCameraCollision(focus, desired, [], undefined, [gate])).toEqual(desired);
  });

  test('skips triangle queries for geometry outside the camera path', () => {
    const distant = box(100, 2, 4);
    const raycast = vi.spyOn(distant, 'raycast');
    resolveCameraCollision(focus, desired, [], undefined, [distant]);
    expect(raycast).not.toHaveBeenCalled();
  });
});
