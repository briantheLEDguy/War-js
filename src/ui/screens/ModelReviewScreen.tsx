import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';

type RosterKind = 'playable' | 'npc' | 'creature';
type BodyVariant = 'm' | 'f';
type WeaponMode = 'one_handed' | 'two_handed' | 'dual_wield';

interface ReviewArtifact {
  kind: string;
  path: string;
  sha256: string;
}

interface ReviewRevision {
  revision: number;
  status: string;
  modelStage: string;
  animationStage: string;
  runtimeEligible: false;
  artifacts: ReviewArtifact[];
  qc: {
    passed: boolean;
    errors: string[];
    reportCount?: number;
    modelCount?: number;
    reviewImageCount?: number;
    npcCombinationCount?: number;
    secondaryReviewProfileKeys?: string[];
  };
  review?: { decision: string; reviewer: string; reviewedAt: string };
  error?: { code: string; message: string };
}

interface ReviewGroup {
  kind: RosterKind;
  key: string;
  displayName: string;
  race?: string;
  realm: string;
  bodyVariant?: BodyVariant;
  roleKits?: string[];
  liveProfileKeys?: string[];
  bodyPlan?: string;
}

interface ReviewItem {
  kind: RosterKind;
  key: string;
  displayName: string;
  group: ReviewGroup;
  revisions: ReviewRevision[];
}

interface ReviewCatalog {
  runId: string;
  reviewToken: string;
  counts: Record<string, number>;
  items: ReviewItem[];
}

const HUMANOID_CHECKS = [
  ['anatomyNatural', 'Anatomy reads naturally'],
  ['materialsPbr', 'PBR materials are coherent'],
  ['seamsAcceptable', 'Seams are acceptable'],
  ['clippingAcceptable', 'Clipping is acceptable'],
  ['stressPosesAcceptable', 'Stress poses deform cleanly'],
  ['weaponSocketsAcceptable', 'All weapon modes clear the body'],
] as const;

const CREATURE_CHECKS = [
  ['materialsPbr', 'PBR materials are coherent'],
  ['seamsAcceptable', 'Seams are acceptable'],
  ['clippingAcceptable', 'Clipping is acceptable'],
  ['stressPosesAcceptable', 'Stress pose deforms cleanly'],
  ['rigMarkersAcceptable', 'Root, contact, attack, and hit markers are correct'],
] as const;

const TERMINAL_JOB_STATES = new Set(['completed', 'failed', 'cancelled']);

export function ModelReviewScreen() {
  const [catalog, setCatalog] = useState<ReviewCatalog | null>(null);
  const [kind, setKind] = useState<RosterKind>('playable');
  const [itemIndex, setItemIndex] = useState(0);
  const [versionIndex, setVersionIndex] = useState(-1);
  const [variant, setVariant] = useState<BodyVariant>('m');
  const [viewMode, setViewMode] = useState<'bare' | 'equipped'>('equipped');
  const [weaponMode, setWeaponMode] = useState<WeaponMode>('one_handed');
  const [autoRotate, setAutoRotate] = useState(true);
  const [showStress, setShowStress] = useState(false);
  const [secondaryEvidenceIndex, setSecondaryEvidenceIndex] = useState(-1);
  const [checks, setChecks] = useState<Record<string, boolean>>({});
  const [visitedVariants, setVisitedVariants] = useState<BodyVariant[]>(['m']);
  const [visitedWeaponModes, setVisitedWeaponModes] = useState<WeaponMode[]>(['one_handed']);
  const [reviewedNpcProfiles, setReviewedNpcProfiles] = useState<string[]>([]);
  const [reviewer, setReviewer] = useState('');
  const [notes, setNotes] = useState('');
  const [message, setMessage] = useState('Loading roster review queue...');
  const [busy, setBusy] = useState(false);

  const loadCatalog = async (runId?: string) => {
    const suffix = runId ? `?runId=${encodeURIComponent(runId)}` : '';
    const response = await fetch(`/__model-review/catalog${suffix}`, { cache: 'no-store' });
    if (!response.ok) throw new Error(`Review catalog failed (${response.status}).`);
    const next = await response.json() as ReviewCatalog;
    setCatalog(next);
    setMessage(`Run ${next.runId}: ${next.counts.generationGroups} generation groups.`);
  };

  useEffect(() => {
    let stored = '';
    try {
      stored = localStorage.getItem('war-js-model-reviewer')?.trim() ?? '';
    } catch {
      // Review remains usable when browser privacy settings block local storage.
    }
    setReviewer(stored);
    void loadCatalog().catch((error) => setMessage(error instanceof Error ? error.message : String(error)));
  }, []);

  const items = useMemo(() => catalog?.items.filter((item) => item.kind === kind) ?? [], [catalog, kind]);
  const item = items[itemIndex] ?? null;
  const revision = item?.revisions[versionIndex] ?? null;

  useEffect(() => {
    setItemIndex(0);
  }, [kind]);

  useEffect(() => {
    setVersionIndex(item?.revisions.length ? item.revisions.length - 1 : -1);
    setVariant(item?.group.bodyVariant ?? 'm');
    setViewMode('equipped');
    setWeaponMode('one_handed');
    setVisitedVariants(item?.kind === 'playable' ? ['m'] : []);
    setVisitedWeaponModes(item?.kind === 'creature' ? [] : ['one_handed']);
    setChecks({});
    setReviewedNpcProfiles([]);
    setNotes('');
    setShowStress(false);
    setSecondaryEvidenceIndex(-1);
  }, [item?.kind, item?.key]);

  useEffect(() => {
    setChecks({});
    setReviewedNpcProfiles([]);
    setNotes('');
    setShowStress(false);
    setSecondaryEvidenceIndex(-1);
  }, [revision?.revision]);

  const artifactUrl = (artifactIndex: number) => {
    if (!catalog || !item || !revision) return '';
    const params = new URLSearchParams({
      runId: catalog.runId,
      kind: item.kind,
      key: item.key,
      revision: String(revision.revision),
      artifact: String(artifactIndex),
    });
    return `/__model-review/artifact?${params}`;
  };

  const modelArtifactIndex = useMemo(() => {
    if (!revision) return -1;
    const candidates = revision.artifacts
      .map((artifact, index) => ({ artifact, index }))
      .filter(({ artifact }) => artifact.path.endsWith('.glb') && !artifact.path.includes('review_weapon_'));
    if (item?.kind === 'creature') return candidates[0]?.index ?? -1;
    const variantCandidates = candidates.filter(({ artifact }) => artifact.path.includes(`/${variant}/`));
    if (viewMode === 'bare') {
      return variantCandidates.find(({ artifact }) => /\/body_[^/]+\.glb$/u.test(artifact.path))?.index ?? -1;
    }
    return variantCandidates.find(({ artifact }) => artifact.path.includes('equipped_review.glb'))?.index
      ?? variantCandidates.find(({ artifact }) => !/\/body_[^/]+\.glb$/u.test(artifact.path))?.index
      ?? -1;
  }, [item?.kind, revision, variant, viewMode]);

  const weaponArtifactIndexes = useMemo(() => {
    const result = { main: -1, off: -1, twoHand: -1 };
    revision?.artifacts.forEach((artifact, index) => {
      if (artifact.path.endsWith('review_weapon_one_hand_main.glb')) result.main = index;
      if (artifact.path.endsWith('review_weapon_one_hand_off.glb')) result.off = index;
      if (artifact.path.endsWith('review_weapon_two_hand.glb')) result.twoHand = index;
    });
    return result;
  }, [revision]);

  const stressArtifactIndex = revision?.artifacts.findIndex((artifact) => (
    artifact.kind === 'review_image' && /stress/i.test(artifact.path)
  )) ?? -1;
  const displayedEvidenceIndex = secondaryEvidenceIndex >= 0 ? secondaryEvidenceIndex : stressArtifactIndex;

  const chooseVariant = (next: BodyVariant) => {
    setVariant(next);
    setVisitedVariants((current) => current.includes(next) ? current : [...current, next]);
  };

  const chooseWeaponMode = (next: WeaponMode) => {
    setWeaponMode(next);
    setVisitedWeaponModes((current) => current.includes(next) ? current : [...current, next]);
  };

  const submitDecision = async (decision: 'approved' | 'rejected') => {
    if (!catalog || !item || !revision) return;
    if (!reviewer.trim()) {
      setMessage('Enter a reviewer name before recording a decision.');
      return;
    }
    if (decision === 'rejected' && !notes.trim()) {
      setMessage('Disapproval requires notes.');
      return;
    }
    setBusy(true);
    try {
      const response = await fetch('/__model-review/review', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-war-review-token': catalog.reviewToken },
        body: JSON.stringify({
          runId: catalog.runId,
          kind: item.kind,
          key: item.key,
          revision: revision.revision,
          decision,
          reviewer: reviewer.trim(),
          notes,
          checks,
          visitedVariants,
          visitedWeaponModes,
          reviewedNpcProfiles,
        }),
      });
      const payload = await response.json() as { error?: { message?: string } };
      if (!response.ok) throw new Error(payload.error?.message ?? `Review failed (${response.status}).`);
      await loadCatalog(catalog.runId);
      setMessage(decision === 'approved'
        ? 'Model-stage bundle frozen. Runtime promotion remains blocked by LOD and animation stages.'
        : 'Revision disapproved and retained with reviewer notes.');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const regenerate = async () => {
    if (!catalog || !item) return;
    setBusy(true);
    try {
      const response = await fetch('/__model-review/regenerate', {
        method: 'POST',
        headers: { 'content-type': 'application/json', 'x-war-review-token': catalog.reviewToken },
        body: JSON.stringify({ runId: catalog.runId, kind: item.kind, key: item.key }),
      });
      const job = await response.json() as { jobId?: string; error?: { message?: string } };
      if (!response.ok || !job.jobId) throw new Error(job.error?.message ?? 'Regeneration could not start.');
      setMessage(`Regeneration job ${job.jobId} started.`);
      while (true) {
        await new Promise((resolve) => window.setTimeout(resolve, 900));
        const jobResponse = await fetch(`/__model-review/job?jobId=${encodeURIComponent(job.jobId)}`, { cache: 'no-store' });
        const progress = await jobResponse.json() as { status: string; progress: number; message: string; error?: { message: string } };
        setMessage(`${progress.status}: ${progress.progress}% - ${progress.message}`);
        if (TERMINAL_JOB_STATES.has(progress.status)) {
          await loadCatalog(catalog.runId);
          if (progress.status !== 'completed') setMessage(progress.error?.message ?? 'Regeneration was blocked.');
          break;
        }
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  const reviewChecks = item?.kind === 'creature' ? CREATURE_CHECKS : HUMANOID_CHECKS;
  const itemCount = items.length;
  const reviewReady = revision?.status === 'ready_for_review';
  const modelUrl = modelArtifactIndex >= 0 ? artifactUrl(modelArtifactIndex) : '';
  const weaponUrls = item?.kind === 'creature' ? [] : (
    weaponMode === 'two_handed'
      ? [weaponArtifactIndexes.twoHand]
      : weaponMode === 'dual_wield'
        ? [weaponArtifactIndexes.main, weaponArtifactIndexes.off]
        : [weaponArtifactIndexes.main]
  ).filter((index) => index >= 0).map(artifactUrl);

  return (
    <main className="model-review-screen">
      <ReviewCanvas modelUrl={modelUrl} weaponUrls={weaponUrls} weaponMode={weaponMode} autoRotate={autoRotate} />
      {(showStress || secondaryEvidenceIndex >= 0) && displayedEvidenceIndex >= 0 && (
        <div className="model-review-stress-overlay">
          <img src={artifactUrl(displayedEvidenceIndex)} alt={`${item?.displayName ?? 'Model'} review evidence`} />
          <button type="button" onClick={() => { setShowStress(false); setSecondaryEvidenceIndex(-1); }}>Close review evidence</button>
        </div>
      )}
      <header className="model-review-header">
        <div className="model-review-header-top">
          <div>
            <span className="model-review-badge">AUTHORING MODEL REVIEW · NOT RUNTIME</span>
            <h1>{item?.displayName ?? 'Full roster review'}</h1>
          </div>
          <a href="/">Exit review</a>
        </div>
        <p>{message}</p>
      </header>
      <aside className="model-review-queue" aria-label="Roster model review controls">
        <p className="model-review-mobile-status" aria-live="polite">{message}</p>
        <div className="model-review-tabs" role="tablist" aria-label="Review queues">
          {(['playable', 'npc', 'creature'] as const).map((tab) => (
            <button type="button" role="tab" aria-selected={kind === tab} className={kind === tab ? 'active' : ''} key={tab} onClick={() => setKind(tab)}>
              {tab === 'playable' ? 'Classes' : tab === 'npc' ? 'NPCs' : 'Creatures'}
            </button>
          ))}
        </div>
        <div className="model-review-nav">
          <button type="button" aria-label="Previous Item" disabled={!itemCount} onClick={() => setItemIndex((itemIndex - 1 + itemCount) % itemCount)}>
            <span className="model-review-wide-label">Previous Item</span><span className="model-review-short-label">Prev</span>
          </button>
          <span>{itemCount ? `${itemIndex + 1} / ${itemCount}` : '0 / 0'}</span>
          <button type="button" aria-label="Next Item" disabled={!itemCount} onClick={() => setItemIndex((itemIndex + 1) % itemCount)}>
            <span className="model-review-wide-label">Next Item</span><span className="model-review-short-label">Next</span>
          </button>
        </div>
        <div className="model-review-nav">
          <button type="button" aria-label="Previous Version" disabled={!item || versionIndex <= 0} onClick={() => setVersionIndex(versionIndex - 1)}>
            <span className="model-review-wide-label">Previous Version</span><span className="model-review-short-label">Prev ver.</span>
          </button>
          <span>{revision ? `Revision ${revision.revision}` : 'No revision'}</span>
          <button type="button" aria-label="Next Version" disabled={!item || versionIndex >= item.revisions.length - 1} onClick={() => setVersionIndex(versionIndex + 1)}>
            <span className="model-review-wide-label">Next Version</span><span className="model-review-short-label">Next ver.</span>
          </button>
        </div>

        {item?.kind === 'playable' && (
          <div className="model-review-segmented" aria-label="Body variant">
            <button type="button" className={variant === 'm' ? 'active' : ''} onClick={() => chooseVariant('m')}>Male</button>
            <button type="button" className={variant === 'f' ? 'active' : ''} onClick={() => chooseVariant('f')}>Female</button>
          </div>
        )}
        {item?.kind !== 'creature' && (
          <>
            <div className="model-review-segmented" aria-label="Equipment view">
              <button type="button" className={viewMode === 'bare' ? 'active' : ''} onClick={() => setViewMode('bare')}>Bare</button>
              <button type="button" className={viewMode === 'equipped' ? 'active' : ''} onClick={() => setViewMode('equipped')}>Equipped</button>
            </div>
            <div className="model-review-segmented model-review-weapons" aria-label="Weapon mode">
              <button type="button" className={weaponMode === 'one_handed' ? 'active' : ''} onClick={() => chooseWeaponMode('one_handed')}>One-handed</button>
              <button type="button" className={weaponMode === 'two_handed' ? 'active' : ''} onClick={() => chooseWeaponMode('two_handed')}>Two-handed</button>
              <button type="button" className={weaponMode === 'dual_wield' ? 'active' : ''} onClick={() => chooseWeaponMode('dual_wield')}>Dual wield</button>
            </div>
          </>
        )}
        <div className="model-review-segmented">
          <button type="button" className={autoRotate ? 'active' : ''} onClick={() => setAutoRotate(!autoRotate)}>Turntable: {autoRotate ? 'on' : 'off'}</button>
          <button type="button" disabled={stressArtifactIndex < 0} onClick={() => setShowStress(true)}>Stress pose</button>
        </div>

        <section className="model-review-qc">
          <h2>QC and stage status</h2>
          <p>Status: <strong>{revision?.status ?? 'not generated'}</strong></p>
          <p>Automated QC: <strong>{revision?.qc.passed ? 'pass' : 'pending / blocked'}</strong></p>
          <p>Evidence: {revision?.qc.modelCount ?? 0} models, {revision?.qc.reviewImageCount ?? 0} renders</p>
          <p>Animation stage: <strong>{revision?.animationStage ?? 'pending'}</strong> · Runtime: <strong>blocked</strong></p>
          {item?.kind === 'npc' && <p>{item.group.liveProfileKeys?.length ?? 0} live profiles · {(item.group.roleKits ?? []).join(', ') || 'ambient kit'}</p>}
          {item?.kind === 'npc' && <p>{revision?.qc.npcCombinationCount ?? 0} assembled profile combinations · {revision?.qc.secondaryReviewProfileKeys?.length ?? 0} secondary reviews</p>}
          {item?.kind === 'creature' && <p>Body plan: {item.group.bodyPlan}</p>}
          {revision?.qc.errors?.map((error) => <p className="model-review-error" key={error}>{error}</p>)}
        </section>

        <fieldset className="model-review-checklist" disabled={!revision || busy}>
          <legend>Approval checklist</legend>
          {reviewChecks.map(([key, label]) => (
            <label key={key}>
              <input type="checkbox" checked={checks[key] === true} onChange={(event) => setChecks((current) => ({ ...current, [key]: event.target.checked }))} />
              {label}
            </label>
          ))}
        </fieldset>
        {item?.kind === 'npc' && Boolean(revision?.qc.secondaryReviewProfileKeys?.length) && (
          <fieldset className="model-review-checklist" disabled={!reviewReady || busy}>
            <legend>Captain / failed-combination secondary review</legend>
            {revision?.qc.secondaryReviewProfileKeys?.map((profileKey) => {
              const evidenceIndex = revision.artifacts.findIndex((artifact) => artifact.path.endsWith(`/${profileKey}.png`));
              return (
                <div className="model-review-secondary-row" key={profileKey}>
                  <label>
                    <input
                      type="checkbox"
                      checked={reviewedNpcProfiles.includes(profileKey)}
                      onChange={(event) => setReviewedNpcProfiles((current) => (
                        event.target.checked
                          ? [...current, profileKey]
                          : current.filter((candidate) => candidate !== profileKey)
                      ))}
                    />
                    {profileKey}
                  </label>
                  <button type="button" disabled={evidenceIndex < 0} onClick={() => setSecondaryEvidenceIndex(evidenceIndex)}>View</button>
                </div>
              );
            })}
          </fieldset>
        )}
        <label className="model-review-field">
          Reviewer
          <input
            value={reviewer}
            placeholder="Your name"
            autoComplete="name"
            onChange={(event) => {
              const nextReviewer = event.target.value;
              setReviewer(nextReviewer);
              try {
                localStorage.setItem('war-js-model-reviewer', nextReviewer);
              } catch {
                // The current review still works without persistence.
              }
            }}
          />
        </label>
        <label className="model-review-field">
          Review notes (required for disapproval)
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} rows={3} />
        </label>
        <div className="model-review-actions">
          <button type="button" className="approve" disabled={!reviewReady || busy} onClick={() => void submitDecision('approved')}>Approve</button>
          <button type="button" className="disapprove" disabled={!reviewReady || busy} onClick={() => void submitDecision('rejected')}>Disapprove</button>
          <button type="button" disabled={!item || busy} onClick={() => void regenerate()}>Regenerate</button>
        </div>
      </aside>
    </main>
  );
}

function ReviewCanvas({
  modelUrl,
  weaponUrls,
  weaponMode,
  autoRotate,
}: {
  modelUrl: string;
  weaponUrls: string[];
  weaponMode: WeaponMode;
  autoRotate: boolean;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const autoRotateRef = useRef(autoRotate);
  useEffect(() => { autoRotateRef.current = autoRotate; }, [autoRotate]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let disposed = false;
    let frame = 0;
    let dragging = false;
    let previousX = 0;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x090b0f);
    const camera = new THREE.PerspectiveCamera(36, 1, 0.05, 100);
    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.45;
    container.appendChild(renderer.domElement);
    const pivot = new THREE.Group();
    scene.add(pivot);
    scene.add(new THREE.HemisphereLight(0xdbe7ff, 0x271710, 1.8));
    const key = new THREE.DirectionalLight(0xffd6a2, 3);
    key.position.set(-3, 5, 4);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x779cff, 1.8);
    rim.position.set(4, 3, -4);
    scene.add(rim);
    const floor = new THREE.Mesh(new THREE.CircleGeometry(3.2, 64), new THREE.MeshStandardMaterial({ color: 0x201f1b, roughness: 0.95 }));
    floor.rotation.x = -Math.PI / 2;
    scene.add(floor);
    const loader = new GLTFLoader();

    const resize = () => {
      const { width, height } = container.getBoundingClientRect();
      renderer.setSize(Math.max(1, width), Math.max(1, height), false);
      camera.aspect = Math.max(1, width) / Math.max(1, height);
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();

    void (async () => {
      if (!modelUrl) return;
      try {
        const model = await loader.loadAsync(modelUrl);
        if (disposed) return;
        prepareReviewMeshes(model.scene);
        pivot.add(model.scene);
        const rightSocket = model.scene.getObjectByName('socket_hand_R');
        const leftSocket = model.scene.getObjectByName('socket_hand_L');
        for (let index = 0; index < weaponUrls.length; index += 1) {
          const weapon = await loader.loadAsync(weaponUrls[index]);
          if (disposed) return;
          prepareReviewMeshes(weapon.scene);
          const socket = weaponMode === 'dual_wield' && index === 1 ? leftSocket : rightSocket;
          if (socket) socket.add(weapon.scene);
        }
        centerAndFrame(pivot, camera);
      } catch (error) {
        console.warn('[ModelReview] preview load failed:', error);
      }
    })();

    const down = (event: PointerEvent) => { dragging = true; previousX = event.clientX; container.setPointerCapture(event.pointerId); };
    const move = (event: PointerEvent) => { if (dragging) { pivot.rotation.y += (event.clientX - previousX) * 0.012; previousX = event.clientX; } };
    const up = (event: PointerEvent) => { dragging = false; if (container.hasPointerCapture(event.pointerId)) container.releasePointerCapture(event.pointerId); };
    container.addEventListener('pointerdown', down);
    container.addEventListener('pointermove', move);
    container.addEventListener('pointerup', up);
    container.addEventListener('pointercancel', up);
    const clock = new THREE.Clock();
    const animate = () => {
      if (disposed) return;
      if (!dragging && autoRotateRef.current) pivot.rotation.y += Math.min(clock.getDelta(), 0.05) * 0.18;
      else clock.getDelta();
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      container.removeEventListener('pointerdown', down);
      container.removeEventListener('pointermove', move);
      container.removeEventListener('pointerup', up);
      container.removeEventListener('pointercancel', up);
      disposeObjectTree(scene);
      renderer.dispose();
      renderer.forceContextLoss();
      renderer.domElement.remove();
    };
  }, [modelUrl, weaponMode, weaponUrls.join('|')]);

  return <div ref={containerRef} className="model-review-canvas" aria-label="Interactive model turntable" />;
}

function prepareReviewMeshes(root: THREE.Object3D): void {
  root.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh) return;
    mesh.castShadow = true;
    mesh.frustumCulled = false;
    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    materials.forEach((material) => { material.transparent = false; material.opacity = 1; material.needsUpdate = true; });
  });
}

function centerAndFrame(root: THREE.Object3D, camera: THREE.PerspectiveCamera): void {
  root.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(root);
  if (box.isEmpty()) return;
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const scale = 2.1 / Math.max(size.y, 0.1);
  root.scale.setScalar(scale);
  root.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale);
  const target = new THREE.Vector3(0, Math.max(0.7, size.y * scale * 0.48), 0);
  camera.position.set(0, target.y, Math.max(3.2, size.y * scale * 1.8));
  camera.lookAt(target);
}

function disposeObjectTree(root: THREE.Object3D): void {
  const geometries = new Set<THREE.BufferGeometry>();
  const materials = new Set<THREE.Material>();
  root.traverse((node) => {
    const mesh = node as THREE.Mesh;
    if (!mesh.isMesh) return;
    if (!geometries.has(mesh.geometry)) { geometries.add(mesh.geometry); mesh.geometry.dispose(); }
    const rows = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    rows.forEach((material) => {
      if (materials.has(material)) return;
      materials.add(material);
      for (const value of Object.values(material)) if (value instanceof THREE.Texture) value.dispose();
      material.dispose();
    });
  });
}
