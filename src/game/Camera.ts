import * as THREE from 'three';
import { useGameStore } from '../state/gameStore';
import type { Input } from './Input';
import { resolveCameraCollision } from './CameraCollision';

const MOUSE_YAW_SENSITIVITY = 0.005;
const MOUSE_PITCH_SENSITIVITY = 0.003;
const PITCH_LIMIT = Math.PI / 2 - 0.01;

export interface CameraCollider {
  id: string;
  x: number;
  z: number;
  width: number;
  depth: number;
  rotY: number;
  minY?: number;
  maxY?: number;
}
type TerrainHeightResolver = (x: number, z: number) => number;

/**
 * Third-person follow camera. Orbit with either mouse button + drag on canvas,
 * scroll to zoom. Smoothly tracks target.
 * On touch devices: single-finger drag orbits, two-finger pinch zooms.
 */
export class FollowCamera {
  camera: THREE.PerspectiveCamera;
  private yaw = 0;
  private pitch = 0.45;
  private distance = 7;
  private minDist = 3;
  private maxDist = 14;
  private minPitch = -PITCH_LIMIT;
  private maxPitch = PITCH_LIMIT;
  private indoorMode = false;
  private outdoorDistance = 7;
  private outdoorYaw = 0;
  private outdoorPitch = 0.45;

  private lastMouseX = 0;
  private lastMouseY = 0;
  private canvas: HTMLElement;
  private dragButtons = new Set<number>();
  private activePointerId: number | null = null;

  // Touch orbit state: last known position per active touch id
  private touchLastPos = new Map<number, { x: number; y: number }>();
  private pinchStartDist = 0;
  private pinchStartCamDist = 0;

  private onPointerMove = (e: PointerEvent) => {
    if (e.pointerType !== 'mouse') return;
    if (useGameStore.getState().gmBuildMode && (e.buttons & 1) !== 0) {
      this.syncDragButtons(e.buttons & ~1);
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
      return;
    }
    this.syncDragButtons(e.buttons);
    if (this.dragButtons.size === 0) {
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
      return;
    }
    e.preventDefault();
    const dx = e.movementX || e.clientX - this.lastMouseX;
    const dy = e.movementY || e.clientY - this.lastMouseY;
    this.lastMouseX = e.clientX;
    this.lastMouseY = e.clientY;
    this.applyOrbitDelta(dx, dy, 'mouse');
  };
  private onPointerDown = (e: PointerEvent) => {
    if (e.pointerType !== 'mouse') return;
    if (useGameStore.getState().gmBuildMode && e.button === 0) return;
    if (e.button === 0 || e.button === 2) {
      e.preventDefault();
      this.syncDragButtons(e.buttons);
      this.activePointerId = e.pointerId;
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
      try { this.canvas.setPointerCapture(e.pointerId); } catch { /* ignore */ }
    }
  };
  private onPointerUp = (e: PointerEvent) => {
    if (e.pointerType !== 'mouse') return;
    this.syncDragButtons(e.buttons);
    if (this.dragButtons.size === 0 && this.activePointerId === e.pointerId) {
      try { this.canvas.releasePointerCapture(e.pointerId); } catch { /* ignore */ }
      this.activePointerId = null;
    }
  };
  private onPointerCancel = (e: PointerEvent) => {
    if (e.pointerType !== 'mouse') return;
    this.dragButtons.clear();
    if (this.activePointerId === e.pointerId) this.activePointerId = null;
  };
  private onWheel = (e: WheelEvent) => {
    if (useGameStore.getState().gmBuildMode) return;
    const { zoomSensitivity } = useGameStore.getState().settings;
    this.distance = Math.max(
      this.minDist,
      Math.min(this.maxDist, this.distance + e.deltaY * 0.01 * zoomSensitivity),
    );
    e.preventDefault();
  };

  private syncDragButtons(buttons: number) {
    this.dragButtons.clear();
    if ((buttons & 1) !== 0) this.dragButtons.add(0);
    if ((buttons & 2) !== 0) this.dragButtons.add(2);
  }

  private applyOrbitDelta(dx: number, dy: number, source: 'mouse' | 'touch') {
    const settings = useGameStore.getState().settings;
    const sensitivity = source === 'mouse'
      ? settings.mouseLookSensitivity
      : settings.touchLookSensitivity;
    const xDirection = settings.invertCameraX ? -1 : 1;
    const yDirection = settings.invertCameraY ? -1 : 1;
    this.yaw -= dx * MOUSE_YAW_SENSITIVITY * sensitivity * xDirection;
    this.pitch = Math.max(
      this.minPitch,
      Math.min(this.maxPitch, this.pitch - dy * MOUSE_PITCH_SENSITIVITY * sensitivity * yDirection),
    );
  }

  private onTouchStart = (e: TouchEvent) => {
    for (let i = 0; i < e.changedTouches.length; i++) {
      const t = e.changedTouches[i];
      this.touchLastPos.set(t.identifier, { x: t.clientX, y: t.clientY });
    }
    // Record pinch baseline when a second finger lands
    if (e.touches.length === 2) {
      const [a, b] = [e.touches[0], e.touches[1]];
      this.pinchStartDist = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      this.pinchStartCamDist = this.distance;
    }
  };

  private onTouchMove = (e: TouchEvent) => {
    e.preventDefault();
    if (e.touches.length === 1) {
      // Single finger → orbit
      const t = e.touches[0];
      const last = this.touchLastPos.get(t.identifier);
      if (last) {
        const dx = t.clientX - last.x;
        const dy = t.clientY - last.y;
        this.applyOrbitDelta(dx, dy, 'touch');
      }
      this.touchLastPos.set(t.identifier, { x: t.clientX, y: t.clientY });
    } else if (e.touches.length === 2) {
      // Two fingers → pinch zoom
      const [a, b] = [e.touches[0], e.touches[1]];
      const newDist = Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
      if (this.pinchStartDist > 0) {
        const scale = this.pinchStartDist / newDist;
        this.distance = Math.max(this.minDist, Math.min(this.maxDist, this.pinchStartCamDist * scale));
      }
      // Update last positions
      this.touchLastPos.set(a.identifier, { x: a.clientX, y: a.clientY });
      this.touchLastPos.set(b.identifier, { x: b.clientX, y: b.clientY });
    }
  };

  private onTouchEnd = (e: TouchEvent) => {
    for (let i = 0; i < e.changedTouches.length; i++) {
      this.touchLastPos.delete(e.changedTouches[i].identifier);
    }
    if (e.touches.length < 2) {
      this.pinchStartDist = 0;
      // Re-seed last position for the remaining finger so orbit doesn't jump
      if (e.touches.length === 1) {
        const t = e.touches[0];
        this.touchLastPos.set(t.identifier, { x: t.clientX, y: t.clientY });
      }
    }
  };

  constructor(canvas: HTMLElement, aspect: number) {
    this.canvas = canvas;
    this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 1200);
    canvas.addEventListener('pointerdown', this.onPointerDown);
    canvas.addEventListener('pointermove', this.onPointerMove);
    canvas.addEventListener('pointerup', this.onPointerUp);
    canvas.addEventListener('pointercancel', this.onPointerCancel);
    canvas.addEventListener('wheel', this.onWheel, { passive: false });
    canvas.addEventListener('touchstart', this.onTouchStart, { passive: true });
    canvas.addEventListener('touchmove', this.onTouchMove, { passive: false });
    canvas.addEventListener('touchend', this.onTouchEnd, { passive: true });
    canvas.addEventListener('touchcancel', this.onTouchEnd, { passive: true });
  }

  get yawAngle() {
    return this.yaw;
  }

  get forwardYaw() {
    return this.yaw + Math.PI;
  }

  setIndoorMode(enabled: boolean): void {
    if (this.indoorMode === enabled) return;
    this.indoorMode = enabled;
    if (enabled) {
      this.outdoorDistance = this.distance;
      this.outdoorYaw = this.yaw;
      this.outdoorPitch = this.pitch;
      this.minDist = 1.65;
      this.maxDist = 3.8;
      this.distance = 2.2;
      this.yaw = 0;
      this.pitch = 0.42;
      return;
    }
    this.minDist = 3;
    this.maxDist = 14;
    this.distance = Math.max(this.minDist, Math.min(this.maxDist, this.outdoorDistance));
    this.yaw = this.outdoorYaw;
    this.pitch = Math.max(this.minPitch, Math.min(this.maxPitch, this.outdoorPitch));
  }

  update(
    target: THREE.Vector3,
    _input: Input,
    colliders: CameraCollider[] = [],
    terrainHeightAt?: TerrainHeightResolver,
    objects: THREE.Object3D[] = [],
  ) {
    const focus = new THREE.Vector3(target.x, target.y + 0.9, target.z);
    const desired = new THREE.Vector3(
      target.x + Math.sin(this.yaw) * Math.cos(this.pitch) * this.distance,
      focus.y + Math.sin(this.pitch) * this.distance,
      target.z + Math.cos(this.yaw) * Math.cos(this.pitch) * this.distance,
    );
    const nearHeight = this.camera.near * Math.tan(THREE.MathUtils.degToRad(this.camera.fov / 2));
    const padding = Math.max(0.35, Math.hypot(nearHeight, nearHeight * this.camera.aspect, this.camera.near));
    const resolved = resolveCameraCollision(focus, desired, colliders, terrainHeightAt, objects, padding);
    this.camera.position.copy(resolved);
    this.camera.lookAt(resolved.clone().sub(desired.clone().sub(focus)));
  }

  resize(aspect: number) {
    this.camera.aspect = aspect;
    this.camera.updateProjectionMatrix();
  }

  dispose() {
    this.canvas.removeEventListener('pointerdown', this.onPointerDown);
    this.canvas.removeEventListener('pointermove', this.onPointerMove);
    this.canvas.removeEventListener('pointerup', this.onPointerUp);
    this.canvas.removeEventListener('pointercancel', this.onPointerCancel);
    this.canvas.removeEventListener('wheel', this.onWheel);
    this.canvas.removeEventListener('touchstart', this.onTouchStart);
    this.canvas.removeEventListener('touchmove', this.onTouchMove);
    this.canvas.removeEventListener('touchend', this.onTouchEnd);
    this.canvas.removeEventListener('touchcancel', this.onTouchEnd);
  }
}
