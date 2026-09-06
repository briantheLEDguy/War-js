import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { AssetLoader } from '../../game/AssetLoader';
import { startForegroundLoop } from '../../game/ForegroundFrameLoop';
import { Player } from '../../game/Player';
import { setupPreviewReflections } from '../../game/PreviewReflections';
import type { CharacterState } from '../../services/types';
import type { Terrain } from '../../world/Terrain';
import { NOVITIATE_ARMOR_ITEM_CATALOG } from '../../data/novitiateArmor';
import { characterForArmorPreview, supportsNovitiatePreview, type ArmorPreviewMode } from './armorPreview';

interface CharacterPreviewStageProps {
  character: CharacterState | null;
}

type PreviewRace = CharacterState['race'];

const PREVIEW_CAMERA_TARGET = new THREE.Vector3(0, 1.18, 0);

export function CharacterPreviewStage({ character }: CharacterPreviewStageProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [armorSelection, setArmorSelection] = useState<{ characterId: string; mode: ArmorPreviewMode } | null>(null);
  const [novitiateReady, setNovitiateReady] = useState(false);
  const compatible = supportsNovitiatePreview(character);
  const armorMode = compatible && novitiateReady && armorSelection && armorSelection.characterId === character?.id
    ? armorSelection.mode : 'current';

  useEffect(() => {
    let cancelled = false;
    setNovitiateReady(false);
    if (compatible) {
      const loader = new AssetLoader();
      const context = { bodyFamily: 'civic_battle_prelate_m', bodyVariant: 'm', skeletonId: 'humanoid_game_v2', bindPoseId: 'a_pose_v2' };
      void Promise.all(Object.values(NOVITIATE_ARMOR_ITEM_CATALOG).map(async (item) => {
        const resolved = await loader.resolveEquipmentModel(item.key, item.visual!.model, context);
        return resolved.skinned === true && !resolved.disabled && resolved.model === item.visual!.model;
      })).then((ready) => { if (!cancelled) setNovitiateReady(ready.every(Boolean)); })
        .catch(() => { if (!cancelled) setNovitiateReady(false); });
    }
    return () => { cancelled = true; };
  }, [compatible, character?.id]);
  const previewKey = useMemo(() => {
    if (!character) return 'empty';
    return [
      character.id,
      character.race,
      character.className,
      character.bodyVariant,
      equipmentSignature(character),
      armorMode,
    ].join(':');
  }, [character, armorMode]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container || !character) return;

    let cancelled = false;
    const baseYaw = Number.isFinite(character.rotationY) ? character.rotationY : 0;
    const startYaw = baseYaw - 0.48;
    let targetYaw = startYaw;
    let currentYaw = startYaw;
    let dragging = false;
    let lastPointerX = 0;

    const loader = new AssetLoader();
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 80);
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    const previewRoot = new THREE.Group();
    const environmentRoot = new THREE.Group();
    const modelRoot = new THREE.Group();
    const clockLight = new THREE.DirectionalLight(0xffe2b8, 1.2);
    const rimLight = new THREE.DirectionalLight(0x9fc4ff, 0.85);
    const fillLight = new THREE.PointLight(0xffd9aa, 0.8, 8);
    const previewTerrain = { heightAt: () => 0 } as unknown as Terrain;
    const previewCharacter: CharacterState = {
      ...characterForArmorPreview(character, armorMode),
      position: { x: 0, y: 0, z: 0 },
      rotationY: 0,
    };
    let player: Player | null = null;

    scene.add(environmentRoot);
    scene.add(previewRoot);
    previewRoot.add(modelRoot);

    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.42;
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    const disposeReflections = setupPreviewReflections(scene, renderer);
    container.appendChild(renderer.domElement);

    const hemi = new THREE.HemisphereLight(0xd8e4ff, 0x1a0c08, 0.92);
    scene.add(hemi);
    clockLight.position.set(-3.5, 6.5, 4.2);
    clockLight.castShadow = true;
    clockLight.shadow.mapSize.set(1024, 1024);
    clockLight.shadow.camera.near = 0.5;
    clockLight.shadow.camera.far = 20;
    clockLight.shadow.camera.left = -7;
    clockLight.shadow.camera.right = 7;
    clockLight.shadow.camera.top = 7;
    clockLight.shadow.camera.bottom = -7;
    scene.add(clockLight);
    rimLight.position.set(4.5, 3.2, -5.5);
    scene.add(rimLight);
    fillLight.position.set(0, 2.0, 3.2);
    scene.add(fillLight);

    const resize = () => {
      const rect = container.getBoundingClientRect();
      const width = Math.max(1, Math.floor(rect.width));
      const height = Math.max(1, Math.floor(rect.height));
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      camera.position.set(0, 2.05, width < 520 ? 5.3 : 4.75);
      camera.lookAt(PREVIEW_CAMERA_TARGET);
    };

    const resizeObserver = new ResizeObserver(resize);
    resizeObserver.observe(container);
    resize();

    const onPointerDown = (event: PointerEvent) => {
      dragging = true;
      lastPointerX = event.clientX;
      try { container.setPointerCapture(event.pointerId); } catch { /* ignore */ }
    };
    const onPointerMove = (event: PointerEvent) => {
      if (!dragging) return;
      const delta = event.clientX - lastPointerX;
      lastPointerX = event.clientX;
      targetYaw += delta * 0.012;
    };
    const onPointerUp = (event: PointerEvent) => {
      dragging = false;
      try { container.releasePointerCapture(event.pointerId); } catch { /* ignore */ }
    };

    container.addEventListener('pointerdown', onPointerDown);
    container.addEventListener('pointermove', onPointerMove);
    container.addEventListener('pointerup', onPointerUp);
    container.addEventListener('pointercancel', onPointerUp);

    void buildPreviewEnvironment(environmentRoot, loader, character.race, clockLight, rimLight, fillLight)
      .then(() => {
        if (cancelled) return;
        environmentRoot.traverse(markShadowed);
      })
      .catch((err) => { if (!cancelled) console.warn('[CharacterPreviewStage] environment fallback:', err); })
      .finally(() => { if (cancelled) loader.dispose(environmentRoot); });

    void (async () => {
      try {
        player = new Player(previewCharacter, previewTerrain, () => 0);
        await player.build(loader, scene);
        if (cancelled || !player.object) {
          if (player.object) loader.dispose(player.object);
          player?.object?.removeFromParent();
          return;
        }
        player.object.removeFromParent();
        modelRoot.add(player.object);
        centerCharacter(modelRoot);
        await player.applyEquipmentVisuals(previewCharacter.equipment, loader);
        if (cancelled) {
          loader.dispose(modelRoot);
          modelRoot.clear();
          return;
        }
        centerCharacter(modelRoot);
      } catch (err) {
        if (!cancelled) console.warn('[CharacterPreviewStage] character fallback:', err);
      } finally {
        if (cancelled) loader.dispose(scene, modelRoot, ...(player?.object ? [player.object] : []));
      }
    })();

    const animate = (_time: number, delta: number) => {
      if (cancelled) return;
      const dt = Math.min(0.05, delta / 1000);
      if (!dragging) targetYaw += dt * 0.018;
      currentYaw = THREE.MathUtils.lerp(currentYaw, targetYaw, Math.min(1, dt * 8));
      previewRoot.rotation.y = currentYaw;
      player?.updateVisuals(dt);
      renderer.render(scene, camera);
    };
    const stopAnimation = startForegroundLoop(animate);

    return () => {
      cancelled = true;
      stopAnimation();
      resizeObserver.disconnect();
      container.removeEventListener('pointerdown', onPointerDown);
      container.removeEventListener('pointermove', onPointerMove);
      container.removeEventListener('pointerup', onPointerUp);
      container.removeEventListener('pointercancel', onPointerUp);
      disposeReflections();
      player?.disposeAnimations();
      loader.dispose(scene);
      scene.clear();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    };
  }, [previewKey, character, armorMode]);

  return (
    <section
      className={`character-preview-stage ${character ? `race-${character.race}` : ''}${compatible ? ' has-armor-preview' : ''}`}
      aria-label="Selected character preview"
    >
      <div ref={containerRef} className="character-preview-canvas" />
      <div className="character-preview-vignette" aria-hidden="true" />
      {compatible && character && (
        <div className="character-armor-preview">
          <span>Armor preview</span>
          <div className="model-review-segmented" role="group" aria-label="Armor preview">
            <button type="button" aria-pressed={armorMode === 'current'} onClick={() => setArmorSelection({ characterId: character.id, mode: 'current' })}>Current armor</button>
            <button type="button" aria-pressed={armorMode === 'novitiate'} disabled={!novitiateReady} onClick={() => setArmorSelection({ characterId: character.id, mode: 'novitiate' })}>Novitiate armor</button>
          </div>
          <small>{novitiateReady ? 'Preview only. Enter World uses your equipped armor.' : 'Novitiate armor is not installed.'}</small>
        </div>
      )}
    </section>
  );
}

function equipmentSignature(character: CharacterState): string {
  return Object.entries(character.equipment ?? {})
    .map(([slot, entry]) => {
      if (!entry) return `${slot}=`;
      return `${slot}=${typeof entry === 'string' ? entry : entry.key}`;
    })
    .sort()
    .join('|');
}

function centerCharacter(modelRoot: THREE.Group): void {
  modelRoot.position.set(0, 0, 0);
  modelRoot.scale.setScalar(1);

  const box = new THREE.Box3().setFromObject(modelRoot);
  if (!Number.isFinite(box.min.y) || box.isEmpty()) return;

  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  modelRoot.position.set(-center.x, -box.min.y, -center.z);
  const targetHeight = 2.08;
  const scale = THREE.MathUtils.clamp(targetHeight / Math.max(size.y, 0.1), 0.78, 1.28);
  modelRoot.scale.setScalar(scale);
}

function markShadowed(node: THREE.Object3D): void {
  const mesh = node as THREE.Mesh;
  if (!mesh.isMesh) return;
  mesh.castShadow = true;
  mesh.receiveShadow = true;
}

async function buildPreviewEnvironment(
  root: THREE.Group,
  loader: AssetLoader,
  race: PreviewRace,
  keyLight: THREE.DirectionalLight,
  rimLight: THREE.DirectionalLight,
  fillLight: THREE.PointLight,
): Promise<void> {
  root.clear();
  const palette = racePalette(race);
  const scene = root.parent as THREE.Scene;
  scene.background = new THREE.Color(palette.sky);
  scene.fog = new THREE.Fog(palette.fog, 6, 16);
  keyLight.color.setHex(palette.key);
  keyLight.intensity = palette.keyIntensity;
  rimLight.color.setHex(palette.rim);
  rimLight.intensity = palette.rimIntensity;
  fillLight.color.setHex(palette.fill);
  fillLight.intensity = palette.fillIntensity;

  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(4.2, 48),
    new THREE.MeshStandardMaterial({
      color: palette.ground,
      roughness: 0.92,
      metalness: 0.02,
    }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  root.add(floor);

  const backPlate = new THREE.Mesh(
    new THREE.CylinderGeometry(4.35, 4.35, 0.18, 48, 1, true, Math.PI * 0.05, Math.PI * 0.9),
    new THREE.MeshStandardMaterial({
      color: palette.backdrop,
      roughness: 0.94,
      side: THREE.DoubleSide,
    }),
  );
  backPlate.position.set(0, 1.15, -2.65);
  backPlate.rotation.y = Math.PI;
  root.add(backPlate);

  addGroundRim(root, palette.accent);

  switch (race) {
    case 'empire':
      await addEmpireEnvironment(root, loader);
      break;
    case 'dwarf':
      addDwarfEnvironment(root);
      break;
    case 'high_elf':
      addHighElfEnvironment(root);
      break;
    case 'chaos':
      await addChaosEnvironment(root, loader);
      break;
    case 'greenskin':
      await addGreenskinEnvironment(root, loader);
      break;
    case 'dark_elf':
      await addDarkElfEnvironment(root, loader);
      break;
    default:
      addDwarfEnvironment(root);
      break;
  }
}

function racePalette(race: PreviewRace) {
  switch (race) {
    case 'empire':
      return {
        sky: 0x15100d, fog: 0x1d120b, ground: 0x30291e, backdrop: 0x2b2118,
        accent: 0xa23822, key: 0xffd38c, rim: 0x8fb9ff, fill: 0xffd2a1,
        keyIntensity: 1.45, rimIntensity: 1.0, fillIntensity: 0.85,
      };
    case 'dwarf':
      return {
        sky: 0x0d0c0a, fog: 0x1a130c, ground: 0x24211c, backdrop: 0x2d2922,
        accent: 0xb56b2c, key: 0xffbd6f, rim: 0x95a6b8, fill: 0xffa95f,
        keyIntensity: 1.35, rimIntensity: 0.75, fillIntensity: 0.9,
      };
    case 'high_elf':
      return {
        sky: 0x101821, fog: 0x182437, ground: 0x303a3d, backdrop: 0x22313a,
        accent: 0x9bbbd0, key: 0xe7f3ff, rim: 0x9ccaff, fill: 0xd8eaff,
        keyIntensity: 1.55, rimIntensity: 1.1, fillIntensity: 0.85,
      };
    case 'chaos':
      return {
        sky: 0x0d0708, fog: 0x24100f, ground: 0x2a1d18, backdrop: 0x211111,
        accent: 0x9f201c, key: 0xff6b3f, rim: 0xa12c2e, fill: 0xd06a45,
        keyIntensity: 1.8, rimIntensity: 1.45, fillIntensity: 1.25,
      };
    case 'greenskin':
      return {
        sky: 0x0b0e0a, fog: 0x1a2216, ground: 0x25301f, backdrop: 0x192116,
        accent: 0x6f842e, key: 0xd4bf72, rim: 0x6aa04a, fill: 0xc0a862,
        keyIntensity: 1.55, rimIntensity: 1.25, fillIntensity: 1.15,
      };
    case 'dark_elf':
      return {
        sky: 0x0d0a18, fog: 0x1b1028, ground: 0x211a27, backdrop: 0x1d142b,
        accent: 0x87509a, key: 0xd8b6f0, rim: 0x9b62df, fill: 0xb68ad8,
        keyIntensity: 1.45, rimIntensity: 1.35, fillIntensity: 1.1,
      };
  }
}

function addGroundRim(root: THREE.Group, color: number): void {
  const mat = new THREE.MeshStandardMaterial({
    color,
    emissive: color,
    emissiveIntensity: 0.06,
    roughness: 0.75,
  });
  for (const radius of [2.0, 3.25]) {
    const ring = new THREE.Mesh(new THREE.TorusGeometry(radius, 0.012, 8, 72), mat);
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.018;
    root.add(ring);
  }
}

async function addEmpireEnvironment(root: THREE.Group, loader: AssetLoader): Promise<void> {
  await addModel(root, loader, 'banner_post.glb', AssetLoader.primitives.banner_post, [-2.4, 0, -1.1], 1.0, -0.25);
  await addModel(root, loader, 'castle_stairs.glb', AssetLoader.primitives.castle_stairs, [2.4, -0.02, -2.2], 0.16, -0.45);
  addStoneBlocks(root, 0x5a5347, 0x3b352e);
}

function addDwarfEnvironment(root: THREE.Group): void {
  addStoneBlocks(root, 0x4a463b, 0x2a2824);
  addForge(root, -2.35, -1.2);
  addForge(root, 2.35, -1.45);
  addRockCluster(root, -2.25, -2.25, 0x5d584e);
  addRockCluster(root, 2.15, -2.15, 0x6b6254);
}

function addHighElfEnvironment(root: THREE.Group): void {
  addPaleColumns(root);
  const treeA = AssetLoader.primitives.pnw_western_red_cedar();
  treeA.position.set(-2.55, 0, -1.85);
  treeA.scale.setScalar(0.42);
  root.add(treeA);
  const treeB = AssetLoader.primitives.pnw_douglas_fir();
  treeB.position.set(2.55, 0, -2.1);
  treeB.scale.setScalar(0.34);
  root.add(treeB);
}

async function addChaosEnvironment(root: THREE.Group, loader: AssetLoader): Promise<void> {
  await addStaticProp(root, loader, 'preview_twisted_tree', 'prop_preview_twisted_tree_t1.glb', buildTwistedTreeFallback, [-2.45, 0, -1.65], 0.86, 0.35);
  await addStaticProp(root, loader, 'preview_jagged_stone', 'prop_preview_jagged_stone_t1.glb', buildJaggedStoneFallback, [2.25, 0, -1.9], 0.95, -0.4);
  await addStaticProp(root, loader, 'preview_dreary_reeds', 'prop_preview_dreary_reeds_t1.glb', buildDrearyReedsFallback, [0.85, 0, -2.65], 0.8, 0.1);
}

async function addGreenskinEnvironment(root: THREE.Group, loader: AssetLoader): Promise<void> {
  await addStaticProp(root, loader, 'preview_blight_shrub', 'prop_preview_blight_shrub_t1.glb', buildBlightShrubFallback, [-2.3, 0, -1.55], 1.05, -0.25);
  await addStaticProp(root, loader, 'preview_dreary_reeds', 'prop_preview_dreary_reeds_t1.glb', buildDrearyReedsFallback, [2.2, 0, -1.8], 1.05, 0.5);
  await addStaticProp(root, loader, 'preview_jagged_stone', 'prop_preview_jagged_stone_t1.glb', buildJaggedStoneFallback, [0, 0, -2.7], 0.72, 0.25);
}

async function addDarkElfEnvironment(root: THREE.Group, loader: AssetLoader): Promise<void> {
  await addStaticProp(root, loader, 'preview_twisted_tree', 'prop_preview_twisted_tree_t1.glb', buildTwistedTreeFallback, [2.35, 0, -1.75], 0.72, -0.55);
  await addStaticProp(root, loader, 'preview_blight_shrub', 'prop_preview_blight_shrub_t1.glb', buildBlightShrubFallback, [-2.35, 0, -1.55], 0.85, 0.4);
  await addStaticProp(root, loader, 'preview_jagged_stone', 'prop_preview_jagged_stone_t1.glb', buildJaggedStoneFallback, [-0.5, 0, -2.75], 0.68, -0.35);
}

async function addStaticProp(
  root: THREE.Group,
  loader: AssetLoader,
  staticKey: string,
  fallbackModel: string,
  fallback: () => THREE.Object3D,
  position: [number, number, number],
  scale: number,
  rotY: number,
): Promise<void> {
  const model = await loader.resolveStaticModel(staticKey, fallbackModel);
  await addModel(root, loader, model, fallback, position, scale, rotY);
}

async function addModel(
  root: THREE.Group,
  loader: AssetLoader,
  model: string,
  fallback: () => THREE.Object3D,
  position: [number, number, number],
  scale: number,
  rotY: number,
): Promise<void> {
  const object = await loader.loadModel(model, fallback);
  object.position.set(...position);
  object.rotation.y = rotY;
  object.scale.setScalar(scale);
  root.add(object);
}

function addStoneBlocks(root: THREE.Group, light: number, dark: number): void {
  const lightMat = new THREE.MeshStandardMaterial({ color: light, roughness: 0.9 });
  const darkMat = new THREE.MeshStandardMaterial({ color: dark, roughness: 0.96 });
  for (let i = 0; i < 9; i += 1) {
    const x = -3.2 + i * 0.8;
    const block = new THREE.Mesh(new THREE.BoxGeometry(0.72, 0.34 + (i % 3) * 0.12, 0.45), i % 2 ? darkMat : lightMat);
    block.position.set(x, block.geometry.parameters.height / 2, -2.85);
    root.add(block);
  }
}

function addForge(root: THREE.Group, x: number, z: number): void {
  const stone = new THREE.MeshStandardMaterial({ color: 0x2d2924, roughness: 0.9 });
  const coal = new THREE.MeshStandardMaterial({ color: 0x090807, roughness: 0.8 });
  const ember = new THREE.MeshStandardMaterial({ color: 0xff7a21, emissive: 0xff5a12, emissiveIntensity: 0.8 });
  const base = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.52, 0.38, 12), stone);
  base.position.set(x, 0.19, z);
  root.add(base);
  const fire = new THREE.Mesh(new THREE.ConeGeometry(0.22, 0.46, 8), ember);
  fire.position.set(x, 0.62, z);
  root.add(fire);
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.3, 0.12, 12), coal);
  cap.position.set(x, 0.42, z);
  root.add(cap);
}

function addRockCluster(root: THREE.Group, x: number, z: number, color: number): void {
  const mat = new THREE.MeshStandardMaterial({ color, roughness: 0.94, flatShading: true });
  for (let i = 0; i < 4; i += 1) {
    const rock = new THREE.Mesh(new THREE.DodecahedronGeometry(0.32 + i * 0.05, 0), mat);
    rock.position.set(x + Math.cos(i) * 0.35, 0.2, z + Math.sin(i * 1.7) * 0.28);
    rock.scale.y = 0.55 + i * 0.12;
    root.add(rock);
  }
}

function addPaleColumns(root: THREE.Group): void {
  const stone = new THREE.MeshStandardMaterial({ color: 0xb8c4c3, roughness: 0.72 });
  const trim = new THREE.MeshStandardMaterial({ color: 0x9cb0bb, roughness: 0.64, metalness: 0.08 });
  for (const x of [-2.45, 2.45]) {
    const column = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.2, 2.4, 18), stone);
    column.position.set(x, 1.2, -1.95);
    root.add(column);
    for (const y of [0.18, 2.28]) {
      const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.32, 0.16, 18), trim);
      cap.position.set(x, y, -1.95);
      root.add(cap);
    }
  }
}

function buildTwistedTreeFallback(): THREE.Object3D {
  const group = new THREE.Group();
  const bark = new THREE.MeshStandardMaterial({ color: 0x211713, roughness: 0.96 });
  const thorn = new THREE.MeshStandardMaterial({ color: 0x3a1a17, roughness: 0.88 });
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.28, 2.25, 9), bark);
  trunk.position.y = 1.12;
  trunk.rotation.z = -0.18;
  group.add(trunk);
  for (const [x, y, z, rz] of [
    [-0.42, 1.8, 0, 0.9],
    [0.42, 1.55, -0.08, -0.85],
    [0.18, 2.15, 0.06, -0.32],
  ]) {
    const branch = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.08, 1.0, 7), bark);
    branch.position.set(x, y, z);
    branch.rotation.z = rz;
    group.add(branch);
  }
  for (const [x, y, z] of [[-0.62, 1.95, 0], [0.58, 1.72, -0.05], [0.28, 2.43, 0.06]]) {
    const spike = new THREE.Mesh(new THREE.ConeGeometry(0.075, 0.35, 6), thorn);
    spike.position.set(x, y, z);
    group.add(spike);
  }
  return group;
}

function buildBlightShrubFallback(): THREE.Object3D {
  const group = new THREE.Group();
  const stem = new THREE.MeshStandardMaterial({ color: 0x22180f, roughness: 0.96 });
  const leaf = new THREE.MeshStandardMaterial({ color: 0x26331c, roughness: 0.92 });
  for (let i = 0; i < 11; i += 1) {
    const angle = i * 0.72;
    const height = 0.45 + (i % 4) * 0.11;
    const reed = new THREE.Mesh(new THREE.CylinderGeometry(0.018, 0.035, height, 5), stem);
    reed.position.set(Math.cos(angle) * 0.32, height / 2, Math.sin(angle) * 0.22);
    reed.rotation.z = Math.sin(angle) * 0.35;
    group.add(reed);
    const clump = new THREE.Mesh(new THREE.SphereGeometry(0.12, 7, 5), leaf);
    clump.position.set(Math.cos(angle) * 0.42, height, Math.sin(angle) * 0.3);
    clump.scale.set(1.4, 0.45, 0.8);
    group.add(clump);
  }
  return group;
}

function buildJaggedStoneFallback(): THREE.Object3D {
  const group = new THREE.Group();
  const stone = new THREE.MeshStandardMaterial({ color: 0x302c2b, roughness: 0.94, flatShading: true });
  const stain = new THREE.MeshStandardMaterial({ color: 0x471313, roughness: 0.88 });
  for (let i = 0; i < 5; i += 1) {
    const spike = new THREE.Mesh(new THREE.ConeGeometry(0.18 + i * 0.025, 0.85 + i * 0.2, 5), i === 2 ? stain : stone);
    spike.position.set(-0.45 + i * 0.22, (0.85 + i * 0.2) / 2, -0.05 + Math.sin(i) * 0.14);
    spike.rotation.z = -0.25 + i * 0.12;
    spike.rotation.y = i * 0.4;
    group.add(spike);
  }
  return group;
}

function buildDrearyReedsFallback(): THREE.Object3D {
  const group = new THREE.Group();
  const reedMat = new THREE.MeshStandardMaterial({ color: 0x2b2a18, roughness: 0.98 });
  const seedMat = new THREE.MeshStandardMaterial({ color: 0x464018, roughness: 0.94 });
  for (let i = 0; i < 15; i += 1) {
    const angle = i * 0.61;
    const radius = 0.18 + (i % 5) * 0.08;
    const height = 0.65 + (i % 3) * 0.18;
    const reed = new THREE.Mesh(new THREE.CylinderGeometry(0.009, 0.018, height, 5), reedMat);
    reed.position.set(Math.cos(angle) * radius, height / 2, Math.sin(angle) * radius * 0.7);
    reed.rotation.z = Math.sin(angle) * 0.28;
    group.add(reed);
    const seed = new THREE.Mesh(new THREE.SphereGeometry(0.035, 6, 4), seedMat);
    seed.position.set(reed.position.x + Math.sin(angle) * 0.06, height + 0.05, reed.position.z);
    seed.scale.y = 1.7;
    group.add(seed);
  }
  return group;
}
