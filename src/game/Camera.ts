import * as THREE from 'three';
import { useGameStore } from '../state/gameStore';
import type { Input } from './Input';

const MOUSE_YAW_SENSITIVITY = 0.005;
const MOUSE_PITCH_SENSITIVITY = 0.003;
const CAMERA_COLLISION_PADDING = 0.35;

export interface CameraCollider {
  id: string;
  x: number;
  z: number;
  width: number;
  depth: number;
  rotY: number;
}

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
  private minPitch = 0.1;
  private maxPitch = 1.3;

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

  update(target: THREE.Vector3, _input: Input, colliders: CameraCollider[] = []) {
    const focus = new THREE.Vector3(target.x, target.y + 0.9, target.z);
    const desired = new THREE.Vector3(
      target.x + Math.sin(this.yaw) * Math.cos(this.pitch) * this.distance,
      target.y + Math.sin(this.pitch) * this.distance + 1.2,
      target.z + Math.cos(this.yaw) * Math.cos(this.pitch) * this.distance,
    );
    const resolved = resolveCameraCollision(focus, desired, colliders);
    this.camera.position.copy(resolved);
    this.camera.lookAt(focus);
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

function resolveCameraCollision(
  focus: THREE.Vector3,
  desired: THREE.Vector3,
  colliders: CameraCollider[],
): THREE.Vector3 {
  if (colliders.length === 0) return desired;

  const direction = desired.clone().sub(focus);
  const distance = direction.length();
  if (distance <= 0.001) return desired;

  let nearestT = 1;
  for (const collider of colliders) {
    const t = intersectSegmentWithColliderXZ(
      focus,
      desired,
      collider,
      CAMERA_COLLISION_PADDING,
    );
    if (t !== null && t < nearestT) nearestT = t;
  }

  const resolved = nearestT < 1
    ? focus.clone().add(direction.multiplyScalar(Math.max(0.05, nearestT - CAMERA_COLLISION_PADDING / distance)))
    : desired.clone();

  for (let pass = 0; pass < 3; pass += 1) {
    let moved = false;
    for (const collider of colliders) {
      moved = pushPointOutsideColliderXZ(resolved, collider, CAMERA_COLLISION_PADDING) || moved;
    }
    if (!moved) break;
  }

  return resolved;
}

function intersectSegmentWithColliderXZ(
  start: THREE.Vector3,
  end: THREE.Vector3,
  collider: CameraCollider,
  padding: number,
): number | null {
  const startLocal = toColliderLocal(start.x, start.z, collider);
  const endLocal = toColliderLocal(end.x, end.z, collider);
  const dx = endLocal.x - startLocal.x;
  const dz = endLocal.z - startLocal.z;
  const halfW = collider.width / 2 + padding;
  const halfD = collider.depth / 2 + padding;

  let tMin = 0;
  let tMax = 1;
  const clippedX = clipSegmentAxis(startLocal.x, dx, -halfW, halfW, tMin, tMax);
  if (!clippedX) return null;
  tMin = clippedX.tMin;
  tMax = clippedX.tMax;

  const clippedZ = clipSegmentAxis(startLocal.z, dz, -halfD, halfD, tMin, tMax);
  if (!clippedZ) return null;

  return clippedZ.tMin;
}

function clipSegmentAxis(
  start: number,
  delta: number,
  min: number,
  max: number,
  tMin: number,
  tMax: number,
): { tMin: number; tMax: number } | null {
  if (Math.abs(delta) < 0.00001) {
    return start < min || start > max ? null : { tMin, tMax };
  }

  const inv = 1 / delta;
  let t1 = (min - start) * inv;
  let t2 = (max - start) * inv;
  if (t1 > t2) [t1, t2] = [t2, t1];
  const nextMin = Math.max(tMin, t1);
  const nextMax = Math.min(tMax, t2);
  return nextMin > nextMax ? null : { tMin: nextMin, tMax: nextMax };
}

function pushPointOutsideColliderXZ(
  point: THREE.Vector3,
  collider: CameraCollider,
  padding: number,
): boolean {
  const local = toColliderLocal(point.x, point.z, collider);
  const halfW = collider.width / 2 + padding;
  const halfD = collider.depth / 2 + padding;
  if (local.x < -halfW || local.x > halfW || local.z < -halfD || local.z > halfD) {
    return false;
  }

  const penX = halfW - Math.abs(local.x);
  const penZ = halfD - Math.abs(local.z);
  let pushX = 0;
  let pushZ = 0;
  if (penX < penZ) {
    pushX = (local.x >= 0 ? 1 : -1) * (penX + 0.01);
  } else {
    pushZ = (local.z >= 0 ? 1 : -1) * (penZ + 0.01);
  }

  const cos = Math.cos(collider.rotY);
  const sin = Math.sin(collider.rotY);
  point.x += pushX * cos - pushZ * sin;
  point.z += pushX * sin + pushZ * cos;
  return true;
}

function toColliderLocal(
  x: number,
  z: number,
  collider: CameraCollider,
): { x: number; z: number } {
  const dx = x - collider.x;
  const dz = z - collider.z;
  const cos = Math.cos(collider.rotY);
  const sin = Math.sin(collider.rotY);
  return {
    x: dx * cos + dz * sin,
    z: -dx * sin + dz * cos,
  };
}
