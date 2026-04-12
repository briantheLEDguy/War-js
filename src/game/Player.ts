import * as THREE from 'three';
import type { CharacterState } from '../services/types';
import type { Terrain } from '../world/Terrain';
import { AssetLoader } from './AssetLoader';
import type { FollowCamera } from './Camera';
import type { Input } from './Input';

const MOVE_SPEED = 6.0;
const TURN_SPEED = 6.0;
const JUMP_V = 6.2;
const GRAVITY = 18.0;

export class Player {
  object!: THREE.Object3D;
  position = new THREE.Vector3();
  rotationY = 0;
  private verticalV = 0;
  private grounded = true;

  constructor(public character: CharacterState, private terrain: Terrain) {}

  async build(loader: AssetLoader, scene: THREE.Scene): Promise<void> {
    const modelName =
      this.character.race === 'greenskin'
        ? 'character_greenskin.glb'
        : this.character.race === 'dark_elf'
        ? 'character_dark_elf.glb'
        : this.character.race === 'chaos'
        ? 'character_chaos.glb'
        : this.character.race === 'dwarf'
        ? 'character_dwarf.glb'
        : this.character.race === 'high_elf'
        ? 'character_high_elf.glb'
        : 'character_empire.glb';
    const color =
      this.character.race === 'greenskin'
        ? 0x3d6a2a
        : this.character.race === 'dark_elf'
        ? 0x4a2060
        : this.character.race === 'chaos'
        ? 0x5a1a1a
        : this.character.race === 'dwarf'
        ? 0x8a5a2a
        : this.character.race === 'high_elf'
        ? 0x7a9aa8
        : 0x7a6425;
    this.object = await loader.loadModel(modelName, () => AssetLoader.primitives.humanoid(color));
    this.position.set(
      this.character.position.x,
      this.terrain.heightAt(this.character.position.x, this.character.position.z),
      this.character.position.z,
    );
    this.rotationY = this.character.rotationY;
    this.object.position.copy(this.position);
    this.object.rotation.y = this.rotationY;
    scene.add(this.object);
  }

  update(dt: number, input: Input, camera: FollowCamera) {
    // Input relative to camera yaw
    let mx = 0;
    let mz = 0;
    if (input.isDown('KeyW')) mz -= 1;
    if (input.isDown('KeyS')) mz += 1;
    if (input.isDown('KeyA')) mx -= 1;
    if (input.isDown('KeyD')) mx += 1;
    const len = Math.hypot(mx, mz);
    if (len > 0) {
      mx /= len;
      mz /= len;
    }
    // Rotate input vector by camera yaw (camera yaw = angle around Y)
    const yaw = camera.yawAngle;
    const sin = Math.sin(yaw);
    const cos = Math.cos(yaw);
    const wx = mx * cos - mz * sin;
    const wz = mx * sin + mz * cos;

    if (len > 0) {
      this.position.x += wx * MOVE_SPEED * dt;
      this.position.z += wz * MOVE_SPEED * dt;
      // Face movement direction (smooth)
      const targetYaw = Math.atan2(wx, wz);
      this.rotationY = lerpAngle(this.rotationY, targetYaw, Math.min(1, TURN_SPEED * dt));
    }

    // Ground check and jump
    const groundY = this.terrain.heightAt(this.position.x, this.position.z);
    if (this.grounded && input.wasPressed('Space')) {
      this.verticalV = JUMP_V;
      this.grounded = false;
    }
    if (!this.grounded) {
      this.verticalV -= GRAVITY * dt;
      this.position.y += this.verticalV * dt;
      if (this.position.y <= groundY) {
        this.position.y = groundY;
        this.verticalV = 0;
        this.grounded = true;
      }
    } else {
      this.position.y = groundY;
    }

    this.object.position.copy(this.position);
    this.object.rotation.y = this.rotationY;
  }
}

function lerpAngle(a: number, b: number, t: number): number {
  let d = (b - a) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return a + d * t;
}
