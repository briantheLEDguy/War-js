import * as THREE from 'three';
import type { Input } from './Input';

/**
 * Third-person follow camera. Orbit with right mouse button + drag on canvas,
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
  private dragging = false;

  // Touch orbit state: last known position per active touch id
  private touchLastPos = new Map<number, { x: number; y: number }>();
  private pinchStartDist = 0;
  private pinchStartCamDist = 0;

  private onMouseMove = (e: MouseEvent) => {
    if (!this.dragging) {
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
      return;
    }
    const dx = e.clientX - this.lastMouseX;
    const dy = e.clientY - this.lastMouseY;
    this.lastMouseX = e.clientX;
    this.lastMouseY = e.clientY;
    this.yaw -= dx * 0.005;
    this.pitch = Math.max(this.minPitch, Math.min(this.maxPitch, this.pitch - dy * 0.003));
  };
  private onMouseDown = (e: MouseEvent) => {
    if (e.button === 2) {
      this.dragging = true;
      this.lastMouseX = e.clientX;
      this.lastMouseY = e.clientY;
    }
  };
  private onMouseUp = (e: MouseEvent) => {
    if (e.button === 2) this.dragging = false;
  };
  private onWheel = (e: WheelEvent) => {
    this.distance = Math.max(this.minDist, Math.min(this.maxDist, this.distance + e.deltaY * 0.01));
    e.preventDefault();
  };

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
        this.yaw -= dx * 0.005;
        this.pitch = Math.max(this.minPitch, Math.min(this.maxPitch, this.pitch - dy * 0.003));
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
    canvas.addEventListener('mousedown', this.onMouseDown);
    window.addEventListener('mouseup', this.onMouseUp);
    window.addEventListener('mousemove', this.onMouseMove);
    canvas.addEventListener('wheel', this.onWheel, { passive: false });
    canvas.addEventListener('touchstart', this.onTouchStart, { passive: true });
    canvas.addEventListener('touchmove', this.onTouchMove, { passive: false });
    canvas.addEventListener('touchend', this.onTouchEnd, { passive: true });
    canvas.addEventListener('touchcancel', this.onTouchEnd, { passive: true });
  }

  get yawAngle() {
    return this.yaw;
  }

  update(target: THREE.Vector3, _input: Input) {
    const cx = target.x + Math.sin(this.yaw) * Math.cos(this.pitch) * this.distance;
    const cy = target.y + Math.sin(this.pitch) * this.distance + 1.2;
    const cz = target.z + Math.cos(this.yaw) * Math.cos(this.pitch) * this.distance;
    this.camera.position.set(cx, cy, cz);
    this.camera.lookAt(target.x, target.y + 1.2, target.z);
  }

  resize(aspect: number) {
    this.camera.aspect = aspect;
    this.camera.updateProjectionMatrix();
  }

  dispose() {
    this.canvas.removeEventListener('mousedown', this.onMouseDown);
    window.removeEventListener('mouseup', this.onMouseUp);
    window.removeEventListener('mousemove', this.onMouseMove);
    this.canvas.removeEventListener('wheel', this.onWheel);
    this.canvas.removeEventListener('touchstart', this.onTouchStart);
    this.canvas.removeEventListener('touchmove', this.onTouchMove);
    this.canvas.removeEventListener('touchend', this.onTouchEnd);
    this.canvas.removeEventListener('touchcancel', this.onTouchEnd);
  }
}
