import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { AssetLoader } from '../../game/AssetLoader';
import { Player } from '../../game/Player';
import { getCareerAbilityKit } from '../../game/abilities/abilityData';
import { spawnAbilityVfx } from '../../game/abilities/AbilityVfx';
import { VfxLayer } from '../../game/animation/VfxLayer';
import type { AbilityDefinition } from '../../game/abilities/types';
import type { CharacterState } from '../../services/types';
import type { Terrain } from '../../world/Terrain';
import { novitiateArmorEquipment } from '../../data/novitiateArmor';
import { starterArmorEquipmentFor } from '../../data/playableAssets.generated';
import { genericActionClip } from '../../game/animation/CombatAnimationController';

const abilities = getCareerAbilityKit('Battle Prelate').abilities;
type ReviewApi = { play: (seek?: number) => void; side: () => void; game: () => void };

/** Development route: isolated actor and effects, no saved character or gameplay mutations. */
export function CombatAnimationReviewScreen() {
  const host = useRef<HTMLDivElement>(null);
  const api = useRef<ReviewApi | null>(null);
  const [variant, setVariant] = useState<'m' | 'f'>('m');
  const [novitiate, setNovitiate] = useState(false);
  const [baseline, setBaseline] = useState(false);
  const [slot, setSlot] = useState(0);
  const [combo, setCombo] = useState(0);
  const [rate, setRate] = useState(1);
  const [moving, setMoving] = useState(false);
  const [airborne, setAirborne] = useState(false);
  const [effects, setEffects] = useState(false);
  const [repeat, setRepeat] = useState(true);
  const [paused, setPaused] = useState(false);
  const [time, setTime] = useState(0);
  const [status, setStatus] = useState('Loading equipped character…');
  const options = useRef({ slot, combo, rate, moving, airborne, effects, repeat, paused });
  options.current = { slot, combo, rate, moving, airborne, effects, repeat, paused };

  useEffect(() => {
    if (!host.current) return;
    setStatus('Loading equipped character…');
    const container = host.current;
    let disposed = false;
    let frame = 0;
    let player: Player | null = null;
    let elapsed = 0;
    let selected: AbilityDefinition = abilities[0];
    const scene = new THREE.Scene();
    scene.background = new THREE.Color('#26313d');
    const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.3;
    container.appendChild(renderer.domElement);
    const camera = new THREE.PerspectiveCamera(38, 1, .01, 100);
    camera.position.set(3, 2.2, 4.2);
    const orbit = new OrbitControls(camera, renderer.domElement);
    orbit.target.set(0, 1, 0);
    orbit.update();
    scene.add(new THREE.HemisphereLight('#e7efff', '#6c6052', 2.5));
    const key = new THREE.DirectionalLight('#fff0d6', 3.5);
    key.position.set(3, 5, 4); scene.add(key);
    const fill = new THREE.DirectionalLight('#97baff', 1.5);
    fill.position.set(-3, 3, -2); scene.add(fill);
    const grid = new THREE.GridHelper(12, 24, '#70808d', '#3d4b56');
    scene.add(grid);
    const loader = new AssetLoader();
    if (baseline) loader.loadCharacterAnimations = async () => [];
    const vfx = new VfxLayer(scene);
    const character: CharacterState = {
      id: 'animation-review', name: 'Battle Prelate', race: 'empire', className: 'Battle Prelate', bodyVariant: variant,
      level: 40, zoneId: 'aegis_capital', xp: 0, health: 180, maxHealth: 180, mana: 100, maxMana: 100,
      strength: 20, gold: 0, position: { x: 0, y: 0, z: 0 }, rotationY: 0,
      equipment: { ...starterArmorEquipmentFor('empire', 'Battle Prelate', variant), mainHand: 'weapon_hammer_reliquary_2h', ...(variant === 'm' && novitiate ? novitiateArmorEquipment() : {}) },
    };
    const play = (seek = 0) => {
      if (!player) return;
      const opts = options.current;
      const base = abilities[opts.slot];
      const motion = base.animation.variants?.[opts.combo];
      selected = motion ? { ...base, animation: { ...base.animation, ...motion } } : base;
      player.resetPreviewAnimation();
      player.playAbilityAnimation(selected);
      player.playAbilityWeaponAction(selected);
      vfx.clear();
      if (opts.effects) spawnAbilityVfx(vfx, selected, { source: player.object, weaponAnchor: player.getWeaponStrikeAnchor(), targetPosition: { x: 0, y: 0, z: 1.25 } }, selected.animation.contactSec ?? 0, 0);
      elapsed = 0;
      while (elapsed < seek - 1e-7) {
        const dt = Math.min(1 / 60, seek - elapsed);
        player.previewAnimationFrame(dt, opts.moving ? 3 : 0, opts.airborne);
        vfx.update(dt);
        elapsed += dt;
      }
      setTime(elapsed);
      const authored = player.hasCombatAnimationPack();
      setStatus(`${authored ? 'Gameplay profile' : 'Embedded baseline'} · ${authored ? selected.animation.clip : genericActionClip(selected.animation.actionId)}`);
    };
    const resize = () => {
      renderer.setSize(container.clientWidth, container.clientHeight);
      camera.aspect = container.clientWidth / Math.max(1, container.clientHeight);
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize); observer.observe(container); resize();
    const clock = new THREE.Clock();
    let uiClock = 0;
    const render = () => {
      if (disposed) return;
      frame = requestAnimationFrame(render);
      const opts = options.current;
      const dt = Math.min(.05, clock.getDelta()) * opts.rate;
      if (player && !opts.paused) {
        player.previewAnimationFrame(dt, opts.moving ? 3 : 0, opts.airborne);
        vfx.update(dt); elapsed += dt; uiClock += dt;
        if (uiClock > .08) { setTime(elapsed); uiClock = 0; }
        if (opts.repeat && elapsed > selected.animation.durationSec + .7) play();
      }
      orbit.update(); renderer.render(scene, camera);
    };
    render();
    void (async () => {
      player = new Player(character, { heightAt: () => 0 } as unknown as Terrain);
      await player.build(loader, scene);
      if (disposed) { player.disposeAnimations(); loader.dispose(scene); return; }
      await player.applyEquipmentVisuals(character.equipment ?? {}, loader);
      if (disposed) { player.disposeAnimations(); loader.dispose(scene); return; }
      api.current = { play,
        side: () => { camera.position.set(4.8, 1.7, 0); orbit.target.set(0, 1, 0); orbit.update(); },
        game: () => { camera.position.set(2.3, 2.4, -3.7); orbit.target.set(0, 1, .2); orbit.update(); },
      };
      play();
    })().catch((error) => { if (!disposed) setStatus(String(error)); });
    return () => {
      disposed = true; api.current = null;
      cancelAnimationFrame(frame); observer.disconnect(); orbit.dispose(); vfx.dispose();
      player?.disposeAnimations(); loader.dispose(scene); renderer.dispose(); renderer.domElement.remove();
    };
  }, [variant, novitiate, baseline]);

  useEffect(() => { api.current?.play(); }, [slot, combo, effects]);
  const activeMotion = abilities[slot].animation.variants?.[combo] ?? abilities[slot].animation;
  const duration = activeMotion.durationSec;
  return <div className="combat-review">
    <aside className="combat-review-controls">
      <h1>Battle Prelate</h1><p>Combat animation review</p>
      <label>Body <select value={variant} onChange={(e) => setVariant(e.target.value as 'm' | 'f')}><option value="m">Male</option><option value="f">Female</option></select></label>
      <label><input type="checkbox" checked={novitiate} disabled={variant === 'f'} onChange={(e) => setNovitiate(e.target.checked)} />Novitiate armor</label>
      <label><input type="checkbox" checked={baseline} onChange={(e) => setBaseline(e.target.checked)} />Embedded baseline comparison</label>
      <label>Ability <select value={slot} onChange={(e) => { setSlot(Number(e.target.value)); setCombo(0); }}>{abilities.map((a) => <option key={a.id} value={a.slot}>{a.name}</option>)}</select></label>
      {slot === 0 && <label>Strike <select value={combo} onChange={(e) => setCombo(Number(e.target.value))}><option value="0">Expanded embedded windup</option><option value="1">Return sweep</option><option value="2">Descending</option></select></label>}
      <label>Playback <select value={rate} onChange={(e) => setRate(Number(e.target.value))}><option value="1">Normal speed</option><option value="0.5">Half speed</option><option value="0.25">Quarter speed</option></select></label>
      <label><input type="checkbox" checked={moving} onChange={(e) => setMoving(e.target.checked)} />Moving</label>
      <label><input type="checkbox" checked={airborne} onChange={(e) => setAirborne(e.target.checked)} />Airborne</label>
      <label><input type="checkbox" checked={effects} onChange={(e) => setEffects(e.target.checked)} />Effects</label>
      <label><input type="checkbox" checked={repeat} onChange={(e) => setRepeat(e.target.checked)} />Repeat</label>
      <button onClick={() => setPaused(!paused)}>{paused ? 'Play' : 'Pause'}</button>
      <button onClick={() => api.current?.play()}>Restart</button>
      <button onClick={() => api.current?.side()}>Side view</button><button onClick={() => api.current?.game()}>Gameplay view</button>
      <label>Timeline <input aria-label="Timeline" type="range" min="0" max={duration + .5} step="0.0166667" value={Math.min(time, duration + .5)} onChange={(e) => { setPaused(true); api.current?.play(Number(e.target.value)); }} /></label>
      <output>{time.toFixed(2)}s · contact {activeMotion.contactSec?.toFixed(2)}s</output>
      <p role="status">{status}</p>
      <p>The gameplay profile uses an expanded version of the embedded opening windup, followed by distinct sweep and descending attacks. The comparison checkbox forces generic clips for every ability.</p>
      <p>Drag to orbit. Scroll to inspect grips and armor. This stage does not change saved equipment.</p>
    </aside>
    <div ref={host} className="combat-review-stage" />
  </div>;
}
