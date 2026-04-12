import * as THREE from 'three';
import type { Input } from './Input';

/**
 * Third-person follow camera. Orbit with right mouse button + drag on canvas,
 * scroll to zoom. Smoothly tracks target.
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

  constructor(canvas: HTMLElement, aspect: number) {
    this.canvas = canvas;
    this.camera = new THREE.PerspectiveCamera(60, aspect, 0.1, 1200);
    canvas.addEventListener('mousedown', this.onMouseDown);
    window.addEventListener('mouseup', this.onMouseUp);
    window.addEventListener('mousemove', this.onMouseMove);
    canvas.addEventListener('wheel', this.onWheel, { passive: false });
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
  }
}
