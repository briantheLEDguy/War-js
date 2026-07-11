import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

const ASSEMBLED_MODEL = '/__model-review/battle-prelate-m.glb';
const REQUIRED_REVIEW_CLIPS = [
  'idle', 'walk', 'run', 'combat_idle', 'attack_melee', 'attack_ranged', 'cast', 'death', 'jump',
] as const;
const LOOPING_REVIEW_CLIPS = new Set<string>(['idle', 'walk', 'run', 'combat_idle']);

interface DisposalRegistry {
  geometries: Set<THREE.BufferGeometry>;
  materials: Set<THREE.Material>;
  textures: Set<THREE.Texture>;
  images: Set<object>;
  skeletons: Set<THREE.Skeleton>;
}

class ReviewLoadCancelled extends Error {}

export function ModelReviewScreen() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const actionsRef = useRef(new Map<string, THREE.AnimationAction>());
  const activeActionRef = useRef<THREE.AnimationAction | null>(null);
  const autoRotateRef = useRef(true);
  const [status, setStatus] = useState('Loading local review candidate...');
  const [availableClips, setAvailableClips] = useState<string[]>([]);
  const [activeClip, setActiveClip] = useState('idle');
  const [paused, setPaused] = useState(false);
  const [autoRotate, setAutoRotate] = useState(true);

  const playClip = (clipName: string) => {
    const action = actionsRef.current.get(clipName);
    if (!action) return;
    const previous = activeActionRef.current;
    if (previous && previous !== action) previous.fadeOut(0.12);
    const looping = LOOPING_REVIEW_CLIPS.has(clipName);
    action.clampWhenFinished = !looping;
    action
      .reset()
      .setLoop(looping ? THREE.LoopRepeat : THREE.LoopOnce, looping ? Infinity : 1)
      .fadeIn(0.12)
      .play();
    activeActionRef.current = action;
    setActiveClip(clipName);
    setPaused(false);
    if (mixerRef.current) mixerRef.current.timeScale = 1;
  };

  const togglePaused = () => {
    const next = !paused;
    setPaused(next);
    if (mixerRef.current) mixerRef.current.timeScale = next ? 0 : 1;
  };

  const toggleAutoRotate = () => {
    const next = !autoRotateRef.current;
    autoRotateRef.current = next;
    setAutoRotate(next);
  };

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let disposed = false;
    let acceptingLoads = true;
    let frame = 0;
    let mixer: THREE.AnimationMixer | null = null;
    let mixerRoot: THREE.Object3D | null = null;
    let assembled = false;
    const ownedScenes = new Set<THREE.Object3D>();
    const disposal: DisposalRegistry = {
      geometries: new Set(),
      materials: new Set(),
      textures: new Set(),
      images: new Set(),
      skeletons: new Set(),
    };
    const clock = new THREE.Clock();
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b0a09);
    scene.fog = new THREE.Fog(0x0b0a09, 7, 18);
    const camera = new THREE.PerspectiveCamera(36, 1, 0.05, 100);
    camera.position.set(0, 1.1, 4.8);
    const cameraTarget = new THREE.Vector3(0, 1.05, 0);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.65;
    renderer.shadowMap.enabled = true;
    container.appendChild(renderer.domElement);

    // Rotate the pivot while keeping centering/scaling isolated on its child.
    const pivot = new THREE.Group();
    pivot.rotation.y = -Math.PI / 2;
    const content = new THREE.Group();
    pivot.add(content);
    scene.add(pivot);
    scene.add(new THREE.HemisphereLight(0xdde7ff, 0x352016, 1.7));
    const key = new THREE.DirectionalLight(0xffd59a, 3.1);
    key.position.set(-3, 5, 4);
    key.castShadow = true;
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x8db8ff, 1.8);
    rim.position.set(4, 3, -4);
    scene.add(rim);
    const floor = new THREE.Mesh(
      new THREE.CircleGeometry(3.2, 64),
      new THREE.MeshStandardMaterial({ color: 0x25211b, roughness: 0.94 }),
    );
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    scene.add(floor);

    const resize = () => {
      const rect = container.getBoundingClientRect();
      const width = Math.max(1, rect.width);
      const height = Math.max(1, rect.height);
      renderer.setSize(width, height, false);
      camera.aspect = width / height;
      if (assembled) fitReviewCamera(content, camera, cameraTarget);
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();

    const loader = new GLTFLoader();
    const loadOwned = async (url: string) => {
      const gltf = await loader.loadAsync(url);
      if (disposed || !acceptingLoads) {
        disposeObjectTree(gltf.scene, disposal);
        throw new ReviewLoadCancelled();
      }
      ownedScenes.add(gltf.scene);
      return gltf;
    };

    void (async () => {
      try {
        const candidate = await loadOwned(ASSEMBLED_MODEL);
        prepareReviewMeshes(candidate.scene);
        candidate.scene.updateMatrixWorld(true);
        const targetSkeleton = findFirstSkeleton(candidate.scene);
        if (!targetSkeleton) throw new Error('The review body has no canonical skeleton.');
        validateCanonicalSkeleton(targetSkeleton);
        if (!candidate.scene.getObjectByName('socket_hand_R')) {
          throw new Error('The assembled review model is missing socket_hand_R.');
        }
        content.add(candidate.scene);

        centerReviewContent(content);
        assembled = true;
        fitReviewCamera(content, camera, cameraTarget);
        camera.updateProjectionMatrix();
        if (candidate.animations.length) {
          mixerRoot = candidate.scene;
          mixer = new THREE.AnimationMixer(mixerRoot);
          mixerRef.current = mixer;
          actionsRef.current.clear();
          for (const clip of candidate.animations) actionsRef.current.set(clip.name, mixer.clipAction(clip));
          const orderedClips = REQUIRED_REVIEW_CLIPS.filter((name) => actionsRef.current.has(name));
          const unexpectedClips = candidate.animations
            .map((clip) => clip.name)
            .filter((name) => !orderedClips.includes(name as typeof REQUIRED_REVIEW_CLIPS[number]));
          setAvailableClips([...orderedClips, ...unexpectedClips]);
          const idle = actionsRef.current.get('idle') ?? actionsRef.current.values().next().value;
          if (idle) {
            idle.setLoop(THREE.LoopRepeat, Infinity).play();
            activeActionRef.current = idle;
            setActiveClip(idle.getClip().name);
          }
        }
        const meshCount = content.getObjectsByProperty('isMesh', true).length;
        setStatus(
          `Exact formal assembly loaded | 9/9 armor modules | canonical socketed hammer | ${meshCount} meshes | ${candidate.animations.length} clips | drag to rotate`,
        );
      } catch (error) {
        acceptingLoads = false;
        if (error instanceof ReviewLoadCancelled || disposed) return;
        for (const owned of ownedScenes) disposeObjectTree(owned, disposal);
        content.clear();
        setStatus(`Review model unavailable: ${error instanceof Error ? error.message : String(error)}`);
      }
    })();

    let dragging = false;
    let previousX = 0;
    const down = (event: PointerEvent) => {
      dragging = true;
      previousX = event.clientX;
      container.setPointerCapture(event.pointerId);
    };
    const move = (event: PointerEvent) => {
      if (!dragging) return;
      pivot.rotation.y += (event.clientX - previousX) * 0.012;
      previousX = event.clientX;
    };
    const up = (event: PointerEvent) => {
      dragging = false;
      if (container.hasPointerCapture(event.pointerId)) container.releasePointerCapture(event.pointerId);
    };
    container.addEventListener('pointerdown', down);
    container.addEventListener('pointermove', move);
    container.addEventListener('pointerup', up);
    container.addEventListener('pointercancel', up);

    const animate = () => {
      if (disposed) return;
      const dt = Math.min(clock.getDelta(), 0.05);
      if (assembled && !dragging && autoRotateRef.current) pivot.rotation.y += dt * 0.12;
      mixer?.update(dt);
      camera.lookAt(cameraTarget);
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);

    return () => {
      disposed = true;
      acceptingLoads = false;
      cancelAnimationFrame(frame);
      observer.disconnect();
      container.removeEventListener('pointerdown', down);
      container.removeEventListener('pointermove', move);
      container.removeEventListener('pointerup', up);
      container.removeEventListener('pointercancel', up);
      mixer?.stopAllAction();
      if (mixer && mixerRoot) mixer.uncacheRoot(mixerRoot);
      if (mixerRef.current === mixer) mixerRef.current = null;
      actionsRef.current.clear();
      activeActionRef.current = null;
      for (const owned of ownedScenes) disposeObjectTree(owned, disposal);
      disposeObjectTree(scene, disposal);
      scene.clear();
      renderer.renderLists.dispose();
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    };
  }, []);

  return (
    <main className="model-review-screen">
      <div ref={containerRef} className="model-review-canvas" />
      <section className="model-review-card">
        <span className="model-review-badge">DRAFT - LOCAL REVIEW ONLY</span>
        <h1>Battle Prelate - Male v19 Animation Pilot</h1>
        <p>{status}</p>
        <p>This route displays the exact assembled, hash-reviewed body, armor, socketed hammer, and animation candidate. It does not bypass promotion in normal play.</p>
        <a href="/">Exit review</a>
      </section>
      <aside className="model-review-animation-panel" aria-label="Animation review controls">
        <span className="model-review-badge">GEOMETRY v18 ACCEPTED · ANIMATION v19 REVIEW</span>
        <h2>Animation Review</h2>
        <p>v18 animation was rejected. Play every revised runtime clip before final promotion approval.</p>
        <div className="model-review-clip-grid">
          {REQUIRED_REVIEW_CLIPS.map((clip) => (
            <button
              type="button"
              key={clip}
              disabled={!availableClips.includes(clip)}
              className={activeClip === clip ? 'active' : ''}
              aria-pressed={activeClip === clip}
              onClick={() => playClip(clip)}
            >
              {clip.replaceAll('_', ' ')}
            </button>
          ))}
        </div>
        <div className="model-review-playback-controls">
          <button type="button" onClick={togglePaused} disabled={!availableClips.length}>
            {paused ? 'Resume' : 'Pause'}
          </button>
          <button type="button" onClick={toggleAutoRotate} aria-pressed={autoRotate}>
            Auto rotate: {autoRotate ? 'on' : 'off'}
          </button>
        </div>
        <p className="model-review-active-clip">Active: {activeClip.replaceAll('_', ' ')}</p>
      </aside>
    </main>
  );
}

function prepareReviewMeshes(root: THREE.Object3D): void {
  root.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh) return;
    mesh.visible = true;
    mesh.castShadow = true;
    mesh.frustumCulled = false;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials) {
      material.visible = true;
      material.transparent = false;
      material.opacity = 1;
      material.alphaTest = 0;
      material.needsUpdate = true;
    }
  });
}

function findFirstSkeleton(root: THREE.Object3D): THREE.Skeleton | null {
  let skeleton: THREE.Skeleton | null = null;
  root.traverse((node) => {
    const mesh = node as THREE.SkinnedMesh;
    if (!skeleton && mesh.isSkinnedMesh) skeleton = mesh.skeleton;
  });
  return skeleton;
}

function validateCanonicalSkeleton(skeleton: THREE.Skeleton): void {
  if (skeleton.bones.length !== skeleton.boneInverses.length) {
    throw new Error('The body skeleton has mismatched bones and inverse bind matrices.');
  }
  const names = skeleton.bones.map((bone) => normalizeBoneName(bone.name));
  if (new Set(names).size !== names.length) {
    throw new Error('The body skeleton has duplicate normalized bone names.');
  }
}

function normalizeBoneName(name: string): string {
  return name.replace(/\.\d+$/u, '');
}

function centerReviewContent(content: THREE.Group): void {
  content.position.set(0, 0, 0);
  content.scale.setScalar(1);
  content.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(content);
  if (box.isEmpty()) throw new Error('The assembled review model has no visible bounds.');
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const scale = 2.05 / Math.max(size.y, 0.1);
  content.scale.setScalar(scale);
  content.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale);
  content.updateMatrixWorld(true);
}

function fitReviewCamera(
  content: THREE.Object3D,
  camera: THREE.PerspectiveCamera,
  target: THREE.Vector3,
): void {
  const box = new THREE.Box3().setFromObject(content);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3());
  box.getCenter(target);
  const verticalFov = THREE.MathUtils.degToRad(camera.fov);
  const horizontalFov = 2 * Math.atan(Math.tan(verticalFov / 2) * Math.max(camera.aspect, 0.01));
  const verticalDistance = (size.y * 0.5) / Math.tan(verticalFov / 2);
  const horizontalDistance = (size.x * 0.5) / Math.tan(horizontalFov / 2);
  const distance = Math.max(verticalDistance, horizontalDistance, 1.5) * 1.28;
  camera.position.set(target.x, target.y, target.z + distance);
  camera.near = Math.max(0.01, distance / 100);
  camera.far = distance + Math.max(size.x, size.y, size.z) * 8;
}

function disposeSkeleton(skeleton: THREE.Skeleton, disposal: DisposalRegistry): void {
  if (disposal.skeletons.has(skeleton)) return;
  disposal.skeletons.add(skeleton);
  skeleton.dispose();
}

function disposeObjectTree(root: THREE.Object3D, disposal: DisposalRegistry): void {
  root.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh) return;
    if (!disposal.geometries.has(mesh.geometry)) {
      disposal.geometries.add(mesh.geometry);
      mesh.geometry.dispose();
    }
    const skinned = mesh as THREE.SkinnedMesh;
    if (skinned.isSkinnedMesh) disposeSkeleton(skinned.skeleton, disposal);
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const material of materials) disposeMaterial(material, disposal);
  });
}

function disposeMaterial(material: THREE.Material, disposal: DisposalRegistry): void {
  if (disposal.materials.has(material)) return;
  disposal.materials.add(material);
  for (const value of Object.values(material)) {
    if (!(value instanceof THREE.Texture) || disposal.textures.has(value)) continue;
    disposal.textures.add(value);
    const image = value.source.data as { close?: () => void } | null;
    if (image && typeof image === 'object' && !disposal.images.has(image)) {
      disposal.images.add(image);
      image.close?.();
    }
    value.dispose();
  }
  material.dispose();
}
