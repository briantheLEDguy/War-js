import * as THREE from 'three';
import { TransformControls } from 'three/examples/jsm/controls/TransformControls.js';
import type { AssetLoader, PrimitiveFactory } from '../../game/AssetLoader';
import { AssetLoader as RuntimeAssetLoader } from '../../game/AssetLoader';
import type {
  Vec3,
  VoxelMaterialId,
  WorldColliderObject,
  WorldEditDocument,
  WorldObject,
  WorldPropObject,
  WorldTransform,
  WorldWalkableSurfaceObject,
} from '../../services/types';
import type { Terrain } from '../Terrain';
import type { InteractiveGate, WorldCollider, WorldWalkableSurface } from '../Props';
import {
  applyVoxelBrushToDocument,
  type VoxelBrushTool,
  VoxelTerrainRuntime,
} from './VoxelTerrainRuntime';
import {
  prefabDefaultAssetKeyForKind,
  prefabDefaultCollidersForKind,
  prefabDefaultModelForKind,
  prefabDefaultScaleForKind,
  prefabDefaultWalkablesForKind,
  prefabFallbackKindForKind,
  prefabFootprintForKind,
  prefabLabelForKind,
  type PrefabFootprint,
} from './PrefabCatalog';

export type WorldEditorTool =
  | 'select'
  | 'move'
  | 'rotate'
  | 'scale'
  | VoxelBrushTool
  | 'stamp_prefab'
  | 'collider'
  | 'walkable_surface'
  | 'ruler';

export interface WorldEditorSettings {
  brushSize: number;
  brushStrength: number;
  material: VoxelMaterialId;
  prefabKind: string;
  snapGrid: number;
  snapAngleDeg: number;
}

interface RuntimeOptions {
  scene: THREE.Scene;
  camera: THREE.Camera;
  domElement: HTMLElement;
  loader: AssetLoader;
  terrain: Terrain;
  groundHeightAt: (x: number, z: number, currentY?: number) => number;
  onChange?: (document: WorldEditDocument) => void;
  onSelectionChange?: (object: WorldObject | null) => void;
}

interface SpawnedEditorObject {
  definition: WorldObject;
  object: THREE.Object3D;
  helper: THREE.BoxHelper | null;
}

interface StaticEditorObject extends SpawnedEditorObject {
  baseDefinition: WorldObject;
  refresh?: () => void;
  useAsPlacementSurface?: boolean;
}

interface RegisterStaticObjectOptions {
  refresh?: () => void;
  useAsPlacementSurface?: boolean;
}

interface LoadDocumentOptions {
  preserveHistory?: boolean;
  undoBaseline?: WorldEditDocument | null;
}

interface AddObjectOptions {
  select?: boolean;
}

interface BrushChainState {
  lastPosition: THREE.Vector3;
  direction: THREE.Vector3;
  step: number;
}

const DEFAULT_SETTINGS: WorldEditorSettings = {
  brushSize: 4,
  brushStrength: 0.5,
  material: 'cobblestone',
  prefabKind: 'building',
  snapGrid: 1,
  snapAngleDeg: 15,
};

const DEFAULT_MATERIAL_COLORS: Record<string, string> = {
  grass: '#4f7d37',
  dirt: '#6b4b2f',
  cobblestone: '#77736a',
  stone: '#85817a',
  wood: '#76512d',
  water: '#3f7da8',
};

const TRANSFORM_CONTROL_SIZE = 0.65;

export class WorldEditorRuntime {
  private scene: THREE.Scene;
  private camera: THREE.Camera;
  private domElement: HTMLElement;
  private loader: AssetLoader;
  private terrain: Terrain;
  private groundHeightAt: RuntimeOptions['groundHeightAt'];
  private onChange?: (document: WorldEditDocument) => void;
  private onSelectionChange?: (object: WorldObject | null) => void;

  private document: WorldEditDocument | null = null;
  private active = false;
  private tool: WorldEditorTool = 'select';
  private settings: WorldEditorSettings = { ...DEFAULT_SETTINGS };
  private group = new THREE.Group();
  private previewGroup = new THREE.Group();
  private brushPreview: THREE.Object3D | null = null;
  private previewBuildToken = 0;
  private previewKey = '';
  private brushRotation = new THREE.Euler(0, 0, 0, 'XYZ');
  private brushRotationTouched = false;
  private playerPosition = new THREE.Vector3();
  private playerRotationY = 0;
  private pointerPoint: THREE.Vector3 | null = null;
  private brushChain: BrushChainState | null = null;
  private lastStampPosition: THREE.Vector3 | null = null;
  private voxelRuntime: VoxelTerrainRuntime;
  private controls: TransformControls;
  private raycaster = new THREE.Raycaster();
  private mouse = new THREE.Vector2();
  private groundPlane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
  private pointerDown = false;
  private selectedId: string | null = null;
  private spawned = new Map<string, SpawnedEditorObject>();
  private staticObjects = new Map<string, StaticEditorObject>();
  private colliders: WorldCollider[] = [];
  private cameraColliders: WorldCollider[] = [];
  private walkableSurfaces: WorldWalkableSurface[] = [];
  private gates = new Map<string, InteractiveGate>();
  private undoStack: WorldEditDocument[] = [];
  private redoStack: WorldEditDocument[] = [];

  constructor(options: RuntimeOptions) {
    this.scene = options.scene;
    this.camera = options.camera;
    this.domElement = options.domElement;
    this.loader = options.loader;
    this.terrain = options.terrain;
    this.groundHeightAt = options.groundHeightAt;
    this.onChange = options.onChange;
    this.onSelectionChange = options.onSelectionChange;

    this.group.name = 'world-editor-authored-objects';
    this.previewGroup.name = 'world-editor-placement-preview';
    this.scene.add(this.group);
    this.scene.add(this.previewGroup);
    this.voxelRuntime = new VoxelTerrainRuntime(this.scene);

    this.controls = new TransformControls(this.camera, this.domElement);
    this.controls.setSize(TRANSFORM_CONTROL_SIZE);
    this.controls.visible = false;
    this.controls.enabled = false;
    this.controls.addEventListener('mouseDown', () => this.pushUndoSnapshot());
    this.controls.addEventListener('objectChange', () => {
      this.syncSelectedTransformFromControls();
      this.emitChanged();
    });
    this.scene.add(this.controls);

    this.domElement.addEventListener('pointerdown', this.onPointerDown);
    this.domElement.addEventListener('wheel', this.onWheel, { passive: false });
    window.addEventListener('pointermove', this.onPointerMove);
    window.addEventListener('pointerup', this.onPointerUp);
  }

  get isActive(): boolean {
    return this.active;
  }

  get currentDocument(): WorldEditDocument | null {
    return this.document ? cloneDoc(this.document) : null;
  }

  registerStaticObject(
    definition: WorldObject,
    object: THREE.Object3D,
    options: RegisterStaticObjectOptions = {},
  ): void {
    object.userData.worldEditObjectId = definition.id;
    object.traverse((node) => {
      node.userData.worldEditObjectId = definition.id;
    });
    this.staticObjects.set(definition.id, {
      baseDefinition: cloneObject(definition),
      definition: cloneObject(definition),
      object,
      helper: null,
      refresh: options.refresh,
      useAsPlacementSurface: options.useAsPlacementSurface,
    });
    this.applyStaticObjectOverride(definition.id);
  }

  isStaticObjectSuppressed(id?: string): boolean {
    if (!id || !this.staticObjects.has(id) || !this.document) return false;
    return this.document.objects.some((object) => object.id === id);
  }

  setActive(active: boolean): void {
    this.active = active;
    this.controls.enabled = active && this.selectedId !== null;
    this.controls.visible = this.controls.enabled;
    this.group.visible = true;
    this.previewGroup.visible = active;
    void this.rebuildBrushPreview();
  }

  setTool(tool: WorldEditorTool): void {
    this.tool = tool;
    if (tool === 'move') this.controls.setMode('translate');
    if (tool === 'rotate') this.controls.setMode('rotate');
    if (tool === 'scale') this.controls.setMode('scale');
    this.controls.enabled = this.active && this.selectedId !== null && ['move', 'rotate', 'scale', 'select'].includes(tool);
    this.controls.visible = this.controls.enabled;
    if (tool === 'stamp_prefab' && !this.brushRotationTouched) {
      this.brushRotation.y = this.playerRotationY;
    }
    this.brushChain = null;
    void this.rebuildBrushPreview();
  }

  setSettings(settings: Partial<WorldEditorSettings>): void {
    const previous = this.settings;
    this.settings = { ...this.settings, ...settings };
    this.controls.setTranslationSnap(this.settings.snapGrid > 0 ? this.settings.snapGrid : null);
    this.controls.setRotationSnap(
      this.settings.snapAngleDeg > 0 ? THREE.MathUtils.degToRad(this.settings.snapAngleDeg) : null,
    );
    this.controls.setScaleSnap(this.settings.snapGrid > 0 ? Math.max(0.05, this.settings.snapGrid * 0.25) : null);
    const previewShapeChanged =
      previous.prefabKind !== this.settings.prefabKind ||
      previous.brushSize !== this.settings.brushSize ||
      previous.brushStrength !== this.settings.brushStrength ||
      previous.material !== this.settings.material;
    if (previous.prefabKind !== this.settings.prefabKind) {
      this.lastStampPosition = null;
    }
    if (previewShapeChanged) {
      void this.rebuildBrushPreview();
    } else {
      this.updateBrushPreview();
    }
  }

  async loadDocument(
    document: WorldEditDocument | null,
    active: boolean,
    options: LoadDocumentOptions = {},
  ): Promise<void> {
    this.clearAuthoredObjects();
    this.document = document ? cloneDoc(document) : null;
    this.active = active;
    if (!options.preserveHistory) {
      this.undoStack = [];
      this.redoStack = [];
      if (active && options.undoBaseline) {
        this.pushUndoDocument(options.undoBaseline);
      }
    }
    this.voxelRuntime.load(this.document);
    if (this.document) {
      for (const object of this.document.objects) {
        if (object.hidden || this.staticObjects.has(object.id)) continue;
        await this.spawnEditorObject(object);
      }
    }
    this.applyStaticObjectOverrides();
    this.rebuildStandaloneCollision();
    this.selectObject(null);
    this.setActive(active);
  }

  setPlayerPose(position: Vec3, rotationY: number): void {
    this.playerPosition.set(position.x, position.y, position.z);
    this.playerRotationY = rotationY;
    if (this.tool === 'stamp_prefab' && !this.brushRotationTouched && !this.pointerPoint && !this.lastStampPosition) {
      this.brushRotation.y = rotationY;
    }
    if (!this.pointerDown) this.updateBrushPreview();
  }

  getColliders(): WorldCollider[] {
    return this.colliders;
  }

  getCameraColliders(): WorldCollider[] {
    return this.cameraColliders;
  }

  getWalkableSurfaces(): WorldWalkableSurface[] {
    return this.walkableSurfaces;
  }

  getGates(): InteractiveGate[] {
    return Array.from(this.gates.values());
  }

  undo(): WorldEditDocument | null {
    if (!this.document || this.undoStack.length === 0) return null;
    this.redoStack.push(cloneDoc(this.document));
    const previous = this.undoStack.pop()!;
    void this.loadDocument(previous, this.active, { preserveHistory: true }).then(() => this.emitChanged());
    return previous;
  }

  redo(): WorldEditDocument | null {
    if (!this.document || this.redoStack.length === 0) return null;
    this.pushUndoDocument(this.document);
    const next = this.redoStack.pop()!;
    void this.loadDocument(next, this.active, { preserveHistory: true }).then(() => this.emitChanged());
    return next;
  }

  deleteSelectedObject(): boolean {
    if (!this.document || !this.selectedId) return false;
    const id = this.selectedId;
    const entry = this.spawned.get(id);
    const staticEntry = this.staticObjects.get(id);

    if (staticEntry) {
      const now = Date.now();
      this.pushUndoSnapshot();
      this.upsertDocumentObject({
        ...cloneObject(staticEntry.definition),
        hidden: true,
        transform: object3dToTransform(staticEntry.object),
        createdAt: this.document.objects.find((candidate) => candidate.id === id)?.createdAt ?? now,
        updatedAt: now,
      });
      this.selectObject(null);
      this.applyStaticObjectOverride(id);
      this.rebuildStandaloneCollision();
      this.emitChanged();
      return true;
    }

    const objectExists = this.document.objects.some((candidate) => candidate.id === id);
    if (!objectExists) {
      this.selectObject(null);
      return false;
    }

    this.pushUndoSnapshot();
    this.selectObject(null);
    if (entry) {
      this.group.remove(entry.object);
      disposeObject(entry.object);
      this.unregisterGateForDefinition(entry.definition);
      this.spawned.delete(id);
    }
    this.document.objects = this.document.objects.filter((candidate) => candidate.id !== id);
    this.rebuildStandaloneCollision();
    this.emitChanged();
    return true;
  }

  async stampPrefabAtPlayer(position: Vec3): Promise<void> {
    const y = this.groundHeightAt(position.x, position.z, position.y);
    await this.addStampAt({ x: position.x, y, z: position.z });
  }

  async applyToolAtPlayer(position: Vec3): Promise<void> {
    if (!this.document) return;
    const y = this.groundHeightAt(position.x, position.z, position.y);
    const snapped = this.snapPosition(new THREE.Vector3(position.x, y, position.z));

    if (this.isVoxelTool(this.tool)) {
      this.pushUndoSnapshot();
      this.document = applyVoxelBrushToDocument(this.document, {
        tool: this.tool,
        x: snapped.x,
        y: snapped.y,
        z: snapped.z,
        radius: this.settings.brushSize,
        strength: this.settings.brushStrength,
        material: this.settings.material,
      });
      this.voxelRuntime.load(this.document);
      this.emitChanged();
      return;
    }

    if (this.tool === 'stamp_prefab') {
      this.pushUndoSnapshot();
      await this.addStampAt(snapped);
      return;
    }

    if (this.tool === 'collider') {
      this.pushUndoSnapshot();
      await this.addObject(buildColliderObject(snapped, this.settings.brushSize));
      return;
    }

    if (this.tool === 'walkable_surface') {
      this.pushUndoSnapshot();
      await this.addObject(buildWalkableSurfaceObject(snapped, this.settings.brushSize));
      return;
    }

    if (this.tool === 'select' || this.tool === 'move' || this.tool === 'rotate' || this.tool === 'scale') {
      this.selectNearest(position);
    }
  }

  dispose(): void {
    this.clearAuthoredObjects();
    this.voxelRuntime.dispose();
    this.controls.detach();
    this.scene.remove(this.controls);
    this.scene.remove(this.group);
    this.clearBrushPreview();
    this.scene.remove(this.previewGroup);
    this.domElement.removeEventListener('pointerdown', this.onPointerDown);
    this.domElement.removeEventListener('wheel', this.onWheel);
    window.removeEventListener('pointermove', this.onPointerMove);
    window.removeEventListener('pointerup', this.onPointerUp);
  }

  private onPointerDown = (event: PointerEvent) => {
    if (!this.active || !this.document || event.button !== 0) return;
    if (this.controls.dragging) return;
    this.pointerDown = true;
    this.updateMouse(event);

    if (this.isVoxelTool(this.tool)) {
      this.pushUndoSnapshot();
      this.applyBrushAtPointer(event);
      event.preventDefault();
      return;
    }

    if (this.tool === 'stamp_prefab') {
      this.pushUndoSnapshot();
      void this.startStampChain(event);
      event.preventDefault();
      return;
    }

    if (this.tool === 'collider') {
      this.pushUndoSnapshot();
      this.addColliderAtPointer(event);
      event.preventDefault();
      return;
    }

    if (this.tool === 'walkable_surface') {
      this.pushUndoSnapshot();
      this.addWalkableSurfaceAtPointer(event);
      event.preventDefault();
      return;
    }

    if (this.tool === 'select' || this.tool === 'move' || this.tool === 'rotate' || this.tool === 'scale') {
      this.selectAtPointer(event);
    }
  };

  private onPointerMove = (event: PointerEvent) => {
    if (!this.active || !this.document) return;
    this.pointerPoint = this.pickWorldPoint(event);

    if (!this.pointerDown) {
      this.updateBrushPreview();
      return;
    }

    if (this.tool === 'stamp_prefab') {
      void this.continueStampChain(event);
      event.preventDefault();
      return;
    }

    if (this.isVoxelTool(this.tool)) this.applyBrushAtPointer(event);
  };

  private onPointerUp = () => {
    this.pointerDown = false;
    this.brushChain = null;
    this.updateBrushPreview();
  };

  private onWheel = (event: WheelEvent) => {
    if (!this.active || !this.isPlacementPreviewTool(this.tool)) return;
    const snapDegrees = this.settings.snapAngleDeg > 0 ? this.settings.snapAngleDeg : 5;
    const step = THREE.MathUtils.degToRad(snapDegrees);
    const direction = event.deltaY > 0 ? -1 : 1;

    if (event.shiftKey) {
      this.brushRotation.x += direction * step;
    } else if (event.altKey) {
      this.brushRotation.z += direction * step;
    } else {
      this.brushRotation.y += direction * step;
    }

    this.brushRotationTouched = true;
    if (this.brushChain) {
      this.brushChain.direction = this.currentChainDirection();
      this.brushChain.step = this.currentChainStep();
    }
    this.updateBrushPreview();
    event.preventDefault();
    event.stopPropagation();
  };

  private async addObject(object: WorldObject, options: AddObjectOptions = {}): Promise<void> {
    if (!this.document) return;
    this.document.objects = [...this.document.objects, object];
    await this.spawnEditorObject(object);
    this.rebuildStandaloneCollision();
    if (options.select !== false) this.selectObject(object.id);
    this.emitChanged();
  }

  private async stampAtPointer(event: PointerEvent): Promise<void> {
    const point = this.pickWorldPoint(event);
    if (!point) return;
    const snapped = this.snapPosition(point);
    await this.addStampAt(snapped);
  }

  private startStampChain(event: PointerEvent): void {
    const point = this.pickWorldPoint(event) ?? this.currentPreviewPosition();
    if (!point) return;
    const snapped = this.snapPosition(point);
    const lastPosition = new THREE.Vector3(snapped.x, snapped.y, snapped.z);
    this.brushChain = {
      lastPosition,
      direction: this.currentChainDirection(),
      step: this.currentChainStep(),
    };
    this.lastStampPosition = lastPosition.clone();
    void this.addStampAt(snapped, { select: false });
    this.updateBrushPreview();
  }

  private continueStampChain(event: PointerEvent): void {
    const point = this.pickWorldPoint(event);
    if (!point || !this.brushChain) return;
    const target = new THREE.Vector3(point.x, 0, point.z);
    let delta = target.clone().sub(this.brushChain.lastPosition.clone().setY(0));
    let projection = delta.dot(this.brushChain.direction);
    const sign = projection >= 0 ? 1 : -1;
    const maxAddsPerMove = 16;
    let placed = 0;

    while (Math.abs(projection) >= this.brushChain.step * 0.98 && placed < maxAddsPerMove) {
      const next = this.brushChain.lastPosition
        .clone()
        .add(this.brushChain.direction.clone().multiplyScalar(this.brushChain.step * sign));
      next.y = this.groundHeightAt(next.x, next.z, next.y);
      void this.addStampAt({ x: next.x, y: next.y, z: next.z }, { select: false });
      this.brushChain.lastPosition.copy(next);
      this.lastStampPosition = next.clone();
      delta = target.clone().sub(this.brushChain.lastPosition.clone().setY(0));
      projection = delta.dot(this.brushChain.direction);
      placed += 1;
    }

    this.updateBrushPreview();
  }

  private addColliderAtPointer(event: PointerEvent): void {
    const point = this.pickWorldPoint(event);
    if (!point || !this.document) return;
    const snapped = this.snapPosition(point);
    void this.addObject(buildColliderObject(snapped, this.settings.brushSize));
  }

  private addWalkableSurfaceAtPointer(event: PointerEvent): void {
    const point = this.pickWorldPoint(event);
    if (!point || !this.document) return;
    const snapped = this.snapPosition(point);
    void this.addObject(buildWalkableSurfaceObject(snapped, this.settings.brushSize));
  }

  private applyBrushAtPointer(event: PointerEvent): void {
    if (!this.document || !this.isVoxelTool(this.tool)) return;
    const point = this.pickWorldPoint(event);
    if (!point) return;
    this.document = applyVoxelBrushToDocument(this.document, {
      tool: this.tool,
      x: point.x,
      y: point.y,
      z: point.z,
      radius: this.settings.brushSize,
      strength: this.settings.brushStrength,
      material: this.settings.material,
    });
    this.voxelRuntime.load(this.document);
    this.emitChanged();
  }

  private selectAtPointer(event: PointerEvent): void {
    const objects = [
      ...Array.from(this.spawned.values(), (entry) => entry.object),
      ...Array.from(this.staticObjects.values(), (entry) => entry.object).filter((object) => object.visible),
    ];
    if (objects.length === 0) {
      this.selectObject(null);
      return;
    }
    this.updateMouse(event);
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const hits = this.raycaster.intersectObjects(objects, true);
    const id = hits.length > 0 ? findWorldEditObjectId(hits[0].object) : null;
    this.selectObject(id);
  }

  private selectObject(id: string | null): void {
    this.selectedId = id;
    for (const entry of [...this.spawned.values(), ...this.staticObjects.values()]) entry.helper?.dispose();
    for (const entry of [...this.spawned.values(), ...this.staticObjects.values()]) {
      if (entry.helper) this.group.remove(entry.helper);
      entry.helper = null;
    }

    if (!id) {
      this.controls.detach();
      this.controls.visible = false;
      this.controls.enabled = false;
      this.onSelectionChange?.(null);
      return;
    }

    const entry = this.spawned.get(id) ?? this.staticObjects.get(id);
    if (!entry) {
      this.selectedId = null;
      this.controls.detach();
      this.controls.visible = false;
      this.controls.enabled = false;
      this.onSelectionChange?.(null);
      return;
    }
    this.controls.attach(entry.object);
    this.controls.enabled = this.active;
    this.controls.visible = this.active;
    this.onSelectionChange?.(entry.definition);
  }

  private syncSelectedTransformFromControls(): void {
    if (!this.document || !this.selectedId) return;
    const entry = this.spawned.get(this.selectedId) ?? this.staticObjects.get(this.selectedId);
    if (!entry) return;
    const object = this.document.objects.find((candidate) => candidate.id === this.selectedId)
      ?? cloneObject(entry.definition);
    object.transform = object3dToTransform(entry.object);
    object.hidden = false;
    object.createdAt = object.createdAt || Date.now();
    object.updatedAt = Date.now();
    entry.definition = object;
    this.upsertDocumentObject(object);
    entry.helper?.update();
    if (this.staticObjects.has(this.selectedId)) {
      this.staticObjects.get(this.selectedId)?.refresh?.();
    }
    this.rebuildStandaloneCollision();
  }

  private async spawnEditorObject(definition: WorldObject): Promise<void> {
    if (definition.hidden) return;
    if (definition.type === 'prop') {
      await this.spawnPropObject(definition);
      return;
    }
    const object = createUtilityObject(definition);
    applyTransform(object, definition.transform);
    object.userData.worldEditObjectId = definition.id;
    object.traverse((node) => {
      node.userData.worldEditObjectId = definition.id;
    });
    this.group.add(object);
    this.spawned.set(definition.id, { definition, object, helper: null });
  }

  private async addStampAt(position: Vec3, options: AddObjectOptions = {}): Promise<void> {
    const object = buildPropObject(this.settings.prefabKind, position, eulerToVec3(this.brushRotation));
    this.lastStampPosition = new THREE.Vector3(position.x, position.y, position.z);
    await this.addObject(object, options);
  }

  private async spawnPropObject(definition: WorldPropObject): Promise<void> {
    const fallback = primitiveForKind(definition.kind);
    const model = definition.assetKey
      ? await this.loader.resolveStaticModel(definition.assetKey, definition.model ?? `${definition.kind}.glb`)
      : definition.model;
    const animated = definition.interaction?.type === 'gate' && model
      ? await this.loader.loadModelWithAnimations(model, fallback)
      : null;
    const object = animated
      ? animated.object
      : model
        ? await this.loader.loadModel(model, fallback)
        : fallback();
    applyTransform(object, definition.transform);
    object.userData.worldEditObjectId = definition.id;
    object.traverse((node) => {
      node.userData.worldEditObjectId = definition.id;
      if (definition.interaction?.type === 'gate') {
        node.userData.interactionId = definition.interaction.id;
      }
      if ((node as THREE.Mesh).isMesh) {
        const mesh = node as THREE.Mesh;
        mesh.castShadow = true;
        mesh.receiveShadow = true;
      }
    });
    if (definition.interaction?.type === 'gate') {
      const actions = new Map<string, THREE.AnimationAction>();
      const mixer = animated && animated.animations.length > 0
        ? new THREE.AnimationMixer(object)
        : null;
      if (mixer && animated) {
        for (const clip of animated.animations) {
          actions.set(clip.name, mixer.clipAction(clip));
        }
      }
      const startsOpen = definition.interaction.startsOpen ?? false;
      this.gates.set(definition.interaction.id, {
        id: definition.interaction.id,
        label: definition.interaction.label ?? 'Gate',
        object,
        mixer,
        actions,
        fallbackVisual: hasGateFallbackLeaves(object)
          ? {
              progress: startsOpen ? 1 : 0,
              target: startsOpen ? 1 : 0,
              speed: 4,
            }
          : null,
        isOpen: startsOpen,
        maxDistance: definition.interaction.maxDistance ?? 18,
        openClip: definition.interaction.openClip ?? 'open',
        closeClip: definition.interaction.closeClip ?? 'close',
      });
      applyGateFallbackVisual(object, startsOpen ? 1 : 0);
    }
    this.group.add(object);
    this.spawned.set(definition.id, { definition, object, helper: null });
    this.rebuildStandaloneCollision();
  }

  private clearAuthoredObjects(): void {
    this.controls.detach();
    for (const entry of this.spawned.values()) {
      this.group.remove(entry.object);
      entry.helper?.dispose();
    }
    this.group.clear();
    this.spawned.clear();
    this.colliders = [];
    this.cameraColliders = [];
    this.walkableSurfaces = [];
    this.gates.clear();
  }

  private unregisterGateForDefinition(definition: WorldObject): void {
    if (definition.type === 'prop' && definition.interaction?.type === 'gate') {
      this.gates.delete(definition.interaction.id);
    }
  }

  private applyStaticObjectOverrides(): void {
    for (const id of this.staticObjects.keys()) {
      this.applyStaticObjectOverride(id);
    }
  }

  private applyStaticObjectOverride(id: string): void {
    const entry = this.staticObjects.get(id);
    if (!entry) return;

    const override = this.document?.objects.find((object) => object.id === id);
    const definition = override ? cloneObject(override) : cloneObject(entry.baseDefinition);
    entry.definition = definition;
    entry.object.visible = definition.hidden !== true;
    if (!definition.hidden) {
      applyTransform(entry.object, definition.transform);
    }
    entry.refresh?.();
  }

  private upsertDocumentObject(object: WorldObject): void {
    if (!this.document) return;
    const index = this.document.objects.findIndex((candidate) => candidate.id === object.id);
    const next = cloneObject(object);
    if (index >= 0) {
      this.document.objects[index] = next;
    } else {
      this.document.objects = [...this.document.objects, next];
    }
  }

  private rebuildStandaloneCollision(): void {
    const colliders: WorldCollider[] = [];
    const walkables: WorldWalkableSurface[] = [];
    if (this.document) {
      for (const object of this.document.objects) {
        if (object.hidden) continue;
        if (object.type === 'collider') colliders.push(colliderFromObject(object));
        if (object.type === 'walkableSurface') walkables.push(walkableFromObject(object));
        if (object.type === 'prop') {
          colliders.push(...propCollidersFromObject(object));
          walkables.push(...propWalkablesFromObject(object));
        }
      }
    }
    this.colliders = colliders;
    this.cameraColliders = colliders;
    this.walkableSurfaces = walkables;
  }

  private selectNearest(position: Vec3): void {
    let best: { id: string; distance: number } | null = null;
    for (const entry of [...this.spawned.values(), ...this.staticObjects.values()]) {
      if (!entry.object.visible) continue;
      const distance = entry.object.position.distanceTo(new THREE.Vector3(position.x, position.y, position.z));
      if (!best || distance < best.distance) best = { id: entry.definition.id, distance };
    }
    this.selectObject(best && best.distance <= Math.max(8, this.settings.brushSize * 2) ? best.id : null);
  }

  private pickWorldPoint(event: PointerEvent): THREE.Vector3 | null {
    this.updateMouse(event);
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const candidates: THREE.Object3D[] = [this.terrain.mesh, this.voxelRuntime.object, ...Array.from(this.spawned.values(), (v) => v.object)]
      .filter((object): object is THREE.Object3D => Boolean(object) && object.visible);
    const hits = this.raycaster.intersectObjects(candidates, true)
      .filter((hit) => this.canUseHitAsPlacementSurface(hit.object));
    if (hits[0]) return hits[0].point.clone();

    const point = new THREE.Vector3();
    return this.raycaster.ray.intersectPlane(this.groundPlane, point) ? point : null;
  }

  private canUseHitAsPlacementSurface(object: THREE.Object3D): boolean {
    const id = findWorldEditObjectId(object);
    if (!id) return true;
    if (this.tool !== 'stamp_prefab' && !this.isVoxelTool(this.tool)) return true;
    return this.staticObjects.get(id)?.useAsPlacementSurface === true;
  }

  private updateMouse(event: PointerEvent): void {
    const rect = this.domElement.getBoundingClientRect();
    this.mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.mouse.y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
  }

  private snapPosition(point: THREE.Vector3): Vec3 {
    const snap = Math.max(0, this.settings.snapGrid);
    const x = snap > 0 ? Math.round(point.x / snap) * snap : point.x;
    const z = snap > 0 ? Math.round(point.z / snap) * snap : point.z;
    return { x, y: this.groundHeightAt(x, z, point.y), z };
  }

  private async rebuildBrushPreview(): Promise<void> {
    const key = [
      this.active,
      this.tool,
      this.settings.prefabKind,
      this.settings.brushSize,
      this.settings.brushStrength,
      this.settings.material,
    ].join(':');
    if (key === this.previewKey && this.brushPreview) {
      this.updateBrushPreview();
      return;
    }
    this.previewKey = key;
    const token = ++this.previewBuildToken;
    this.clearBrushPreview();

    if (!this.active || !this.isPreviewTool(this.tool)) return;

    const preview = await this.createPreviewObject();
    if (token !== this.previewBuildToken) {
      disposeObject(preview);
      return;
    }
    this.brushPreview = preview;
    this.previewGroup.add(preview);
    this.updateBrushPreview();
  }

  private async createPreviewObject(): Promise<THREE.Object3D> {
    if (this.isVoxelTool(this.tool)) {
      return createVoxelBrushPreview(
        this.settings.brushSize,
        this.settings.brushStrength,
        this.selectedMaterialColor(),
      );
    }

    if (this.tool === 'collider') {
      const preview = createUtilityObject(buildColliderObject({ x: 0, y: 0, z: 0 }, this.settings.brushSize));
      applyGhostMaterial(preview, 0x48ff75, 0.32);
      return preview;
    }
    if (this.tool === 'walkable_surface') {
      const preview = createUtilityObject(buildWalkableSurfaceObject({ x: 0, y: 0, z: 0 }, this.settings.brushSize));
      applyGhostMaterial(preview, 0x48ff75, 0.32);
      return preview;
    }

    if (this.tool === 'stamp_prefab') {
      return this.createPrefabPreviewObject();
    }

    const fallback = primitiveForKind(this.settings.prefabKind);
    const preview = fallback();
    applyGhostMaterial(preview, 0x48ff75, 0.42);
    preview.traverse((node) => {
      node.userData.worldEditPreview = true;
    });
    return preview;
  }

  private async createPrefabPreviewObject(): Promise<THREE.Object3D> {
    const fallback = primitiveForKind(this.settings.prefabKind);
    const assetKey = defaultAssetKeyForKind(this.settings.prefabKind);
    const fallbackModel = defaultModelForKind(this.settings.prefabKind) ?? '';
    const model = assetKey
      ? await this.loader.resolveStaticModel(assetKey, fallbackModel)
      : fallbackModel;
    const object = model
      ? await this.loader.loadModel(model, fallback)
      : fallback();
    applyGhostMaterial(object, 0x48ff75, 0.42);

    const preview = new THREE.Group();
    preview.name = `world-editor-${this.settings.prefabKind}-preview`;
    preview.add(object, createFootprintPreview(footprintForKind(this.settings.prefabKind)));
    preview.traverse((node) => {
      node.userData.worldEditPreview = true;
    });
    return preview;
  }

  private clearBrushPreview(): void {
    if (!this.brushPreview) return;
    this.previewGroup.remove(this.brushPreview);
    disposeObject(this.brushPreview);
    this.brushPreview = null;
  }

  private updateBrushPreview(): void {
    if (!this.brushPreview) return;
    const point = this.currentPreviewPosition();
    if (!point) {
      this.brushPreview.visible = false;
      return;
    }
    this.brushPreview.visible = this.active && this.isPreviewTool(this.tool);
    this.brushPreview.position.set(point.x, point.y, point.z);
    this.brushPreview.rotation.copy(this.brushRotation);
    this.brushPreview.scale.set(1, 1, 1);
  }

  private currentPreviewPosition(): THREE.Vector3 | null {
    if (!this.active) return null;
    if (this.brushChain) {
      return this.brushChain.lastPosition
        .clone()
        .add(this.brushChain.direction.clone().multiplyScalar(this.brushChain.step));
    }
    if (this.pointerPoint && !this.pointerDown) {
      const snapped = this.snapPosition(this.pointerPoint);
      return new THREE.Vector3(snapped.x, snapped.y, snapped.z);
    }
    if (this.pointerPoint && this.tool !== 'stamp_prefab') {
      const snapped = this.snapPosition(this.pointerPoint);
      return new THREE.Vector3(snapped.x, snapped.y, snapped.z);
    }
    if (this.pointerPoint && !this.lastStampPosition) {
      const snapped = this.snapPosition(this.pointerPoint);
      return new THREE.Vector3(snapped.x, snapped.y, snapped.z);
    }
    if (this.lastStampPosition && this.tool === 'stamp_prefab') {
      const next = this.lastStampPosition.clone().add(this.currentChainDirection().multiplyScalar(this.currentChainStep()));
      next.y = this.groundHeightAt(next.x, next.z, next.y);
      return next;
    }

    const footprint = footprintForKind(this.settings.prefabKind);
    const distance = this.isVoxelTool(this.tool)
      ? Math.max(this.settings.brushSize + 2, 4)
      : Math.max(footprint.width, footprint.depth, this.settings.brushSize, 4);
    const forward = new THREE.Vector3(
      Math.sin(this.playerRotationY),
      0,
      Math.cos(this.playerRotationY),
    );
    const point = this.playerPosition.clone().add(forward.multiplyScalar(distance));
    const snapped = this.snapPosition(point);
    return new THREE.Vector3(snapped.x, snapped.y, snapped.z);
  }

  private currentChainDirection(): THREE.Vector3 {
    const footprint = footprintForKind(this.settings.prefabKind);
    const y = this.brushRotation.y;
    const direction = footprint.chainAxis === 'x'
      ? new THREE.Vector3(Math.cos(y), 0, -Math.sin(y))
      : new THREE.Vector3(Math.sin(y), 0, Math.cos(y));
    return direction.normalize();
  }

  private currentChainStep(): number {
    const footprint = footprintForKind(this.settings.prefabKind);
    return footprint.chainAxis === 'x' ? footprint.width : footprint.depth;
  }

  private isPlacementPreviewTool(tool: WorldEditorTool): boolean {
    return tool === 'stamp_prefab' || tool === 'collider' || tool === 'walkable_surface';
  }

  private isPreviewTool(tool: WorldEditorTool): boolean {
    return this.isPlacementPreviewTool(tool) || this.isVoxelTool(tool);
  }

  private selectedMaterialColor(): number {
    const paletteColor = this.document?.palette.materials.find((material) => material.id === this.settings.material)?.color;
    return new THREE.Color(paletteColor ?? DEFAULT_MATERIAL_COLORS[this.settings.material] ?? '#48ff75').getHex();
  }

  private isVoxelTool(tool: WorldEditorTool): tool is VoxelBrushTool {
    return [
      'voxel_add',
      'voxel_subtract',
      'voxel_smooth',
      'voxel_flatten',
      'voxel_roughen',
      'paint_material',
      'fill_erase',
    ].includes(tool);
  }

  private pushUndoSnapshot(): void {
    if (!this.document) return;
    this.pushUndoDocument(this.document);
    this.redoStack = [];
  }

  private pushUndoDocument(document: WorldEditDocument): void {
    const snapshot = cloneDoc(document);
    const last = this.undoStack[this.undoStack.length - 1];
    if (last && JSON.stringify(last) === JSON.stringify(snapshot)) return;
    this.undoStack.push(snapshot);
  }

  private emitChanged(): void {
    if (!this.document) return;
    this.document.updatedAt = Date.now();
    this.onChange?.(cloneDoc(this.document));
  }
}

function buildPropObject(kind: string, position: Vec3, rotation?: Vec3): WorldPropObject {
  const now = Date.now();
  const id = makeObjectId(kind);
  const interaction = defaultInteractionForKind(kind, id);
  return {
    id,
    type: 'prop',
    kind,
    label: prefabLabelForKind(kind),
    model: defaultModelForKind(kind),
    assetKey: defaultAssetKeyForKind(kind),
    transform: {
      ...defaultTransform(position),
      rotation: rotation ?? { x: 0, y: 0, z: 0 },
      scale: prefabDefaultScaleForKind(kind),
    },
    colliders: defaultCollidersForKind(kind, interaction?.id),
    walkableSurfaces: defaultWalkablesForKind(kind),
    interaction,
    createdAt: now,
    updatedAt: now,
  };
}

function buildColliderObject(position: Vec3, size: number): WorldColliderObject {
  const now = Date.now();
  return {
    id: makeObjectId('collider'),
    type: 'collider',
    label: 'Editor Collider',
    transform: defaultTransform(position),
    width: Math.max(1, size),
    depth: Math.max(1, size),
    blocksWhen: 'always',
    createdAt: now,
    updatedAt: now,
  };
}

function buildWalkableSurfaceObject(position: Vec3, size: number): WorldWalkableSurfaceObject {
  const now = Date.now();
  return {
    id: makeObjectId('walkable'),
    type: 'walkableSurface',
    label: 'Editor Walkable Surface',
    transform: defaultTransform(position),
    width: Math.max(1, size),
    depth: Math.max(1, size),
    fromY: 0,
    toY: 0,
    axis: 'z',
    createdAt: now,
    updatedAt: now,
  };
}

function defaultTransform(position: Vec3): WorldTransform {
  return {
    position,
    rotation: { x: 0, y: 0, z: 0 },
    scale: { x: 1, y: 1, z: 1 },
  };
}

function eulerToVec3(euler: THREE.Euler): Vec3 {
  return {
    x: round(euler.x),
    y: round(euler.y),
    z: round(euler.z),
  };
}

function createUtilityObject(definition: WorldColliderObject | WorldWalkableSurfaceObject): THREE.Object3D {
  if (definition.type === 'collider') {
    const material = new THREE.MeshBasicMaterial({
      color: 0xff6655,
      transparent: true,
      opacity: 0.22,
      depthWrite: false,
    });
    const geometry = new THREE.BoxGeometry(definition.width, 1.4, definition.depth);
    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.y = 0.7;
    const edges = new THREE.LineSegments(
      new THREE.EdgesGeometry(geometry),
      new THREE.LineBasicMaterial({ color: 0xffc2b8, transparent: true, opacity: 0.8 }),
    );
    edges.position.y = 0.7;
    const group = new THREE.Group();
    group.name = definition.id;
    group.add(mesh, edges);
    return group;
  }

  const material = new THREE.MeshBasicMaterial({
    color: 0x6ad6ff,
    transparent: true,
    opacity: 0.25,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const geometry = new THREE.BoxGeometry(definition.width, 0.12, definition.depth);
  const mesh = new THREE.Mesh(geometry, material);
  mesh.position.y = 0.06;
  const edges = new THREE.LineSegments(
    new THREE.EdgesGeometry(geometry),
    new THREE.LineBasicMaterial({ color: 0xc6f2ff, transparent: true, opacity: 0.85 }),
  );
  edges.position.y = 0.06;
  const group = new THREE.Group();
  group.name = definition.id;
  group.add(mesh, edges);
  return group;
}

function createVoxelBrushPreview(radius: number, strength: number, materialColor: number): THREE.Object3D {
  const r = Math.max(0.5, radius);
  const group = new THREE.Group();
  group.name = 'world-editor-voxel-brush-preview';

  const ghostMaterial = new THREE.MeshBasicMaterial({
    color: 0x48ff75,
    transparent: true,
    opacity: 0.16,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const materialFill = new THREE.MeshBasicMaterial({
    color: materialColor,
    transparent: true,
    opacity: Math.min(0.46, 0.16 + strength * 0.24),
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  const ringMaterial = new THREE.MeshBasicMaterial({
    color: 0x48ff75,
    transparent: true,
    opacity: 0.88,
    depthWrite: false,
    side: THREE.DoubleSide,
  });

  const ghost = new THREE.Mesh(new THREE.CylinderGeometry(r * 1.03, r * 1.03, 0.18, 56), ghostMaterial);
  ghost.position.y = 0.09;
  const fill = new THREE.Mesh(new THREE.CylinderGeometry(r, r, 0.12, 56), materialFill);
  fill.position.y = 0.1;
  const ring = new THREE.Mesh(new THREE.RingGeometry(Math.max(0.01, r - 0.08), r, 72), ringMaterial);
  ring.rotation.x = -Math.PI / 2;
  ring.position.y = 0.18;

  group.add(ghost, fill, ring);
  group.traverse((node) => {
    node.userData.worldEditPreview = true;
  });
  return group;
}

function createFootprintPreview(footprint: PrefabFootprint): THREE.Object3D {
  const group = new THREE.Group();
  group.name = 'world-editor-footprint-preview';
  const halfW = footprint.width / 2;
  const halfD = footprint.depth / 2;
  const y = 0.08;
  const material = new THREE.LineBasicMaterial({
    color: 0xb6ff8a,
    transparent: true,
    opacity: 0.9,
  });
  const outlinePoints = [
    new THREE.Vector3(-halfW, y, -halfD),
    new THREE.Vector3(halfW, y, -halfD),
    new THREE.Vector3(halfW, y, halfD),
    new THREE.Vector3(-halfW, y, halfD),
    new THREE.Vector3(-halfW, y, -halfD),
  ];
  const outline = new THREE.Line(new THREE.BufferGeometry().setFromPoints(outlinePoints), material);

  const axisMaterial = new THREE.LineBasicMaterial({
    color: 0x48ff75,
    transparent: true,
    opacity: 0.95,
  });
  const axisPoints = footprint.chainAxis === 'x'
    ? [new THREE.Vector3(-halfW, y + 0.02, 0), new THREE.Vector3(halfW, y + 0.02, 0)]
    : [new THREE.Vector3(0, y + 0.02, -halfD), new THREE.Vector3(0, y + 0.02, halfD)];
  const axis = new THREE.Line(new THREE.BufferGeometry().setFromPoints(axisPoints), axisMaterial);
  group.add(outline, axis);
  return group;
}

function applyTransform(object: THREE.Object3D, transform: WorldTransform): void {
  object.position.set(transform.position.x, transform.position.y, transform.position.z);
  object.rotation.set(transform.rotation.x, transform.rotation.y, transform.rotation.z);
  object.scale.set(transform.scale.x, transform.scale.y, transform.scale.z);
}

function object3dToTransform(object: THREE.Object3D): WorldTransform {
  return {
    position: { x: round(object.position.x), y: round(object.position.y), z: round(object.position.z) },
    rotation: { x: round(object.rotation.x), y: round(object.rotation.y), z: round(object.rotation.z) },
    scale: { x: round(object.scale.x), y: round(object.scale.y), z: round(object.scale.z) },
  };
}

function colliderFromObject(object: WorldColliderObject): WorldCollider {
  return {
    id: object.id,
    x: object.transform.position.x,
    z: object.transform.position.z,
    width: object.width * object.transform.scale.x,
    depth: object.depth * object.transform.scale.z,
    rotY: object.transform.rotation.y,
    minY: object.minY === undefined ? undefined : object.transform.position.y + object.minY * object.transform.scale.y,
    maxY: object.maxY === undefined ? undefined : object.transform.position.y + object.maxY * object.transform.scale.y,
    blocksWhen: object.blocksWhen ?? 'always',
    interactionId: object.interactionId,
    sourceObjectId: object.id,
  };
}

function walkableFromObject(object: WorldWalkableSurfaceObject): WorldWalkableSurface {
  return {
    id: object.id,
    x: object.transform.position.x,
    z: object.transform.position.z,
    width: object.width * object.transform.scale.x,
    depth: object.depth * object.transform.scale.z,
    rotY: object.transform.rotation.y,
    fromY: object.transform.position.y + object.fromY * object.transform.scale.y,
    toY: object.transform.position.y + object.toY * object.transform.scale.y,
    axis: object.axis ?? 'z',
    sourceObjectId: object.id,
  };
}

function propCollidersFromObject(object: WorldPropObject): WorldCollider[] {
  return (object.colliders ?? []).map((collider, index) => ({
    id: collider.id ?? `${object.id}-collider-${index}`,
    x: object.transform.position.x + (collider.x ?? 0) * object.transform.scale.x,
    z: object.transform.position.z + (collider.z ?? 0) * object.transform.scale.z,
    width: collider.width * object.transform.scale.x,
    depth: collider.depth * object.transform.scale.z,
    rotY: object.transform.rotation.y + (collider.rotY ?? 0),
    minY: collider.minY === undefined ? undefined : object.transform.position.y + collider.minY * object.transform.scale.y,
    maxY: collider.maxY === undefined ? undefined : object.transform.position.y + collider.maxY * object.transform.scale.y,
    blocksWhen: collider.blocksWhen ?? 'always',
    interactionId: collider.interactionId,
    sourceObjectId: object.id,
  }));
}

function propWalkablesFromObject(object: WorldPropObject): WorldWalkableSurface[] {
  return (object.walkableSurfaces ?? []).map((surface, index) => ({
    id: surface.id ?? `${object.id}-walkable-${index}`,
    x: object.transform.position.x + (surface.x ?? 0) * object.transform.scale.x,
    z: object.transform.position.z + (surface.z ?? 0) * object.transform.scale.z,
    width: surface.width * object.transform.scale.x,
    depth: surface.depth * object.transform.scale.z,
    rotY: object.transform.rotation.y + (surface.rotY ?? 0),
    fromY: object.transform.position.y + (surface.fromY ?? 0) * object.transform.scale.y,
    toY: object.transform.position.y + (surface.toY ?? 0) * object.transform.scale.y,
    axis: surface.axis ?? 'z',
    sourceObjectId: object.id,
  }));
}

function defaultModelForKind(kind: string): string | undefined {
  return prefabDefaultModelForKind(kind);
}

function defaultAssetKeyForKind(kind: string): string | undefined {
  return prefabDefaultAssetKeyForKind(kind);
}

function defaultInteractionForKind(kind: string, id: string): WorldPropObject['interaction'] {
  if (kind === 'castle_gate') {
    return {
      id: `${id}-gate`,
      type: 'gate',
      label: 'Castle Gate',
      maxDistance: 20,
      openClip: 'open',
      closeClip: 'close',
    };
  }
  if (kind === 'castle_door') {
    return {
      id: `${id}-door`,
      type: 'gate',
      label: 'Castle Door',
      maxDistance: 14,
      openClip: 'open',
      closeClip: 'close',
    };
  }
  return undefined;
}

function defaultCollidersForKind(kind: string, interactionId?: string): WorldPropObject['colliders'] {
  return prefabDefaultCollidersForKind(kind, interactionId);
}

function defaultWalkablesForKind(kind: string): WorldPropObject['walkableSurfaces'] {
  return prefabDefaultWalkablesForKind(kind);
}

function footprintForKind(kind: string): PrefabFootprint {
  return prefabFootprintForKind(kind);
}

function applyGhostMaterial(root: THREE.Object3D, color: number, opacity: number): void {
  const material = new THREE.MeshBasicMaterial({
    color,
    transparent: true,
    opacity,
    depthWrite: false,
    side: THREE.DoubleSide,
  });
  root.traverse((node) => {
    if (!(node as THREE.Mesh).isMesh) return;
    const mesh = node as THREE.Mesh;
    mesh.material = material;
    mesh.castShadow = false;
    mesh.receiveShadow = false;
  });
}

function disposeObject(root: THREE.Object3D): void {
  root.traverse((node) => {
    if (!(node as THREE.Mesh).isMesh && !(node as THREE.Line).isLine) return;
    const renderable = node as THREE.Mesh | THREE.Line;
    renderable.geometry?.dispose();
    const materials = Array.isArray(renderable.material) ? renderable.material : [renderable.material];
    for (const material of materials) material?.dispose();
  });
}

function primitiveForKind(kind: string): PrimitiveFactory {
  const primitives = RuntimeAssetLoader.primitives as unknown as Record<string, PrimitiveFactory>;
  const fallbackKind = prefabFallbackKindForKind(kind);
  if (fallbackKind && primitives[fallbackKind]) return primitives[fallbackKind];
  return primitives[kind] ?? primitives.rock;
}

function hasGateFallbackLeaves(object: THREE.Object3D): boolean {
  let found = false;
  object.traverse((node) => {
    if (typeof node.userData.gateLeafSide === 'number') found = true;
  });
  return found;
}

function applyGateFallbackVisual(object: THREE.Object3D, progress: number): void {
  const clamped = Math.max(0, Math.min(1, progress));
  object.traverse((node) => {
    const side = node.userData.gateLeafSide;
    if (typeof side !== 'number') return;
    node.rotation.y = -side * (Math.PI / 2) * clamped;
  });
}

function findWorldEditObjectId(object: THREE.Object3D | null): string | null {
  let node: THREE.Object3D | null = object;
  while (node) {
    const id = node.userData.worldEditObjectId as string | undefined;
    if (id) return id;
    node = node.parent;
  }
  return null;
}

function makeObjectId(prefix: string): string {
  return `gm-${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}

function cloneDoc(document: WorldEditDocument): WorldEditDocument {
  return JSON.parse(JSON.stringify(document)) as WorldEditDocument;
}

function cloneObject<T extends WorldObject>(object: T): T {
  return JSON.parse(JSON.stringify(object)) as T;
}

function round(value: number): number {
  return Math.round(value * 1000) / 1000;
}
