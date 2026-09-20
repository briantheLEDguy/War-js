import { readFileSync } from 'node:fs';
import { webcrypto } from 'node:crypto';
import { afterEach, describe, expect, test, vi } from 'vitest';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { AssetLoader } from '../src/game/AssetLoader';
import { assembleCampaignEquipment, campaignAnimationClips, campaignEquipmentKeys, campaignNpcProfile, resolveCampaignEquipment } from '../src/game/network/CampaignCharacterPresentation';
import { CampaignAssetQueue, releaseCampaignActor, SharedCampaignRenderer } from '../src/game/network/SharedCampaignRenderer';

const modelPath = (name: string) => `${process.cwd()}/public/assets/models/${name}`;
const registry = JSON.parse(readFileSync(modelPath('asset-index.json'), 'utf8'));
const profile = registry.characterProfiles.civic_battle_prelate_m;

function installManifestFetch(missing = new Set<string>()): AssetLoader {
  vi.stubGlobal('crypto', webcrypto);
  vi.stubGlobal('fetch', vi.fn(async (input: string | Request, init?: RequestInit) => {
    const filename = String(input).split('?')[0].split('/').pop()!;
    if (missing.has(filename)) return new Response(null, { status: 404 });
    const data = readFileSync(modelPath(filename));
    return new Response(init?.method === 'HEAD' ? null : data, { headers: { 'content-type': filename.endsWith('.json') ? 'application/json' : 'model/gltf-binary' } });
  }));
  return new AssetLoader();
}

/** Parse the actual authored geometry, skins and clips without browser-only texture decoding. */
async function readAuthoredModel(filename: string) {
  const source = readFileSync(modelPath(filename));
  const length = source.readUInt32LE(12);
  const json = JSON.parse(source.subarray(20, 20 + length).toString('utf8'));
  delete json.images; delete json.textures; delete json.samplers; delete json.materials;
  for (const mesh of json.meshes ?? []) for (const primitive of mesh.primitives) delete primitive.material;
  const content = Buffer.from(JSON.stringify(json));
  const paddedLength = Math.ceil(content.length / 4) * 4;
  const bin = source.subarray(20 + length);
  const output = Buffer.alloc(20 + paddedLength + bin.length, 32);
  output.writeUInt32LE(0x46546c67, 0); output.writeUInt32LE(2, 4); output.writeUInt32LE(output.length, 8);
  output.writeUInt32LE(paddedLength, 12); output.writeUInt32LE(0x4e4f534a, 16);
  content.copy(output, 20); bin.copy(output, 20 + paddedLength);
  const gltf = await new GLTFLoader().parseAsync(output.buffer.slice(output.byteOffset, output.byteOffset + output.byteLength), '');
  return { object: gltf.scene as THREE.Object3D, animations: gltf.animations };
}

afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals(); });

async function createSharedActor(loader: AssetLoader, profileKey = 'npc_frontier_sunmeadow_dwarf_artisan') {
  // Exercise production actor creation without allocating a browser WebGL context.
  const description = { id: 'regional-service', profile: profileKey, signature: profileKey, position: { x: -413, y: 0, z: -257 }, self: false };
  const stage = {
    loader, queue: new CampaignAssetQueue(), scene: new THREE.Scene(), actors: new Map(),
    pending: new Set(), unavailable: new Map(), desiredActors: new Map([[description.id, description]]),
  };
  const renderer = Object.assign(Object.create(SharedCampaignRenderer.prototype), { stage, disposed: false, snapshot: null });
  await renderer.createActor(stage, description);
  return { renderer, stage, description, actor: stage.actors.get(description.id) };
}

describe('reviewed shared character presentation', () => {
  test.each([1, 2])('a missing primary regional GLB still presents its own available LOD%s, fitted meshes and embedded idle', async level => {
    const key = 'npc_frontier_sunmeadow_dwarf_artisan';
    const missing = new Set(Array.from({ length: level }, (_, index) => `frontier_sunmeadow_dwarf_artisan_lod${index}.glb`));
    const loader = installManifestFetch(missing);
    expect(await loader.resolveCharacterAsset(key)).toBeNull();
    const models = await loader.resolveApprovedAssetModels(key, 'characterProfiles');
    expect(models).toHaveLength(3);
    const authored = await readAuthoredModel(models[level]);
    const meshes = new Set<THREE.Mesh>(), bones = new Set<THREE.Bone>();
    authored.object.traverse(node => {
      if ((node as THREE.Mesh).isMesh) meshes.add(node as THREE.Mesh);
      if ((node as THREE.Bone).isBone) bones.add(node as THREE.Bone);
    });
    const load = vi.spyOn(loader, 'loadModelFull').mockImplementation(async (filename, fallback) =>
      missing.has(filename) ? { object: fallback!(), animations: [] } : authored);
    const equipment = vi.spyOn(loader, 'resolveEquipmentModel');
    const animationPack = vi.spyOn(loader, 'loadCharacterAnimations');
    const { renderer, stage, actor, description } = await createSharedActor(loader, key);
    expect(actor).toBeDefined();
    expect(actor.selected).toBe(level);
    expect(actor.models).toEqual(models);
    expect(actor.signature).toBe(key);
    expect(actor.object.parent).toBe(stage.scene);
    expect(actor.object.position.toArray()).toEqual([-413, 0, -257]);
    expect(actor.object.userData.campaignEntityId).toBe(description.id);
    expect(stage.unavailable.size).toBe(0);
    expect(stage.pending.size).toBe(0);
    expect(load.mock.calls.map(([filename]) => filename)).toEqual(models.slice(0, level + 1));
    expect(equipment).not.toHaveBeenCalled();
    expect(animationPack).not.toHaveBeenCalled();
    expect(actor.equipment).toEqual([]);
    const visual = actor.levels.get(level);
    expect(visual.object).toBe(authored.object);
    expect(visual.object.visible).toBe(true);
    expect(visual.crew).toBeUndefined();
    const presentedMeshes = new Set<THREE.Mesh>();
    actor.object.traverse((node: THREE.Object3D) => {
      if ((node as THREE.Mesh).isMesh) presentedMeshes.add(node as THREE.Mesh);
      if ((node as THREE.SkinnedMesh).isSkinnedMesh) {
        expect((node as THREE.SkinnedMesh).skeleton.bones.every(bone => bones.has(bone))).toBe(true);
      }
      expect(node.userData.equipmentOverlay).toBeUndefined();
    });
    expect(meshes.size).toBeGreaterThan(0);
    expect(bones.size).toBeGreaterThan(0);
    expect(presentedMeshes).toEqual(meshes);
    const authoredIdle = authored.animations.find(clip => /^idle$/i.test(clip.name))!;
    expect(visual.idle.isRunning()).toBe(true);
    expect(visual.idle.getClip().duration).toBe(authoredIdle.duration);
    expect(visual.idle.getClip().tracks.length).toBeGreaterThan(0);
    expect(visual.idle.getClip().tracks.every((track: THREE.KeyframeTrack) => authoredIdle.tracks.includes(track))).toBe(true);
    const rotations = [...bones].map(bone => bone.quaternion.clone());
    visual.mixer.update(.4);
    expect([...bones].some((bone, index) => bone.quaternion.angleTo(rotations[index]) > .00001)).toBe(true);
    // Returning toward the viewer never removes the working level in favor of a failed LOD0.
    actor.desired = 0;
    await renderer.loadActorLevel(stage, actor, 0);
    expect(actor.selected).toBe(level);
    expect(visual.object.visible).toBe(true);
    renderer.releaseActor(actor); stage.queue.close(); loader.dispose();
  });

  test('an entirely unavailable regional set stays empty without substituting another character or primitive', async () => {
    const missing = new Set([0, 1, 2].map(level => `frontier_sunmeadow_dwarf_artisan_lod${level}.glb`));
    const loader = installManifestFetch(missing);
    const load = vi.spyOn(loader, 'loadModelFull').mockImplementation(async (_, fallback) => ({ object: fallback!(), animations: [] }));
    const { stage, actor, description } = await createSharedActor(loader);
    expect(actor).toBeUndefined();
    expect(load.mock.calls.map(([filename]) => filename)).toEqual([...missing]);
    expect(stage.scene.children).toHaveLength(0);
    expect(stage.pending.size).toBe(0);
    expect(stage.unavailable.get(description.id)).toBe(description.signature);
    stage.queue.close(); loader.dispose();
  });

  test.each(['npc_frontier_sunmeadow_dwarf_artisan', 'civic_battle_prelate_m'])('does not bypass missing approval or modular metadata for %s', async key => {
    const loader = installManifestFetch();
    vi.spyOn(loader, 'resolveCharacterAsset').mockResolvedValue(null);
    const approved = vi.spyOn(loader, 'resolveApprovedAssetModels').mockResolvedValue(key.startsWith('npc_frontier_') ? [] : [profile.model]);
    const load = vi.spyOn(loader, 'loadModelFull');
    const { stage, actor, description } = await createSharedActor(loader, key);
    expect(actor).toBeUndefined();
    expect(stage.scene.children).toHaveLength(0);
    expect(stage.unavailable.get(description.id)).toBe(key);
    expect(load).not.toHaveBeenCalled();
    if (key.startsWith('npc_frontier_')) expect(approved).toHaveBeenCalledWith(key, 'characterProfiles');
    stage.queue.close(); loader.dispose();
  });

  test.each([
    ['npc_frontier_sunmeadow_dwarf_artisan', 'dwarf', 'aegis'],
    ['npc_frontier_sunmeadow_empire_farmer', 'empire', 'aegis'],
    ['npc_frontier_sunmeadow_high_elf_scout', 'high_elf', 'aegis'],
    ['npc_frontier_cinderfen_greenskin_peat_worker', 'greenskin', 'riftbound'],
    ['npc_frontier_cinderfen_dark_elf_supply_officer', 'dark_elf', 'riftbound'],
  ] as const)('preserves an explicit regional character %s instead of substituting a city model', (profileKey, race, realm) => {
    expect(campaignNpcProfile({ id: 'regional-service', role: 'trainer', profileKey, race, realm })).toBe(profileKey);
    expect(campaignNpcProfile({ id: 'regional-service', role: 'trainer', profileKey, realm })).toBe(profileKey);
  });

  test('regional profile selection rejects unknown and contradictory racial assignments', () => {
    const npc = { id: 'regional-service', role: 'trainer', profileKey: 'npc_frontier_sunmeadow_dwarf_artisan' };
    expect(campaignNpcProfile({ ...npc, race: 'empire', realm: 'aegis' })).toBeUndefined();
    expect(campaignNpcProfile({ ...npc, race: 'dwarf', realm: 'riftbound' })).toBeUndefined();
    expect(campaignNpcProfile({ ...npc, profileKey: 'npc_frontier_unbuilt_invented' })).toBeUndefined();
  });

  test('every selected existing city population profile resolves reviewed runtime LODs', async () => {
    const loader = installManifestFetch();
    const profiles = Object.keys(registry.characterProfiles).filter(key => /^npc_aegis_(city_guard|people)_/.test(key) || /^npc_riftspire_(chaos|greenskin|dark_elf)$/.test(key));
    expect(profiles.length).toBeGreaterThanOrEqual(14);
    for (const key of profiles) expect(await loader.resolveApprovedAssetModels(key, 'characterProfiles'), key).not.toHaveLength(0);
    loader.dispose();
  });

  test.each([0, 1, 2])('assembles all real Battle Prelate modules onto LOD%s and its own animated skeleton', async level => {
    const loader = installManifestFetch();
    const modules = await resolveCampaignEquipment(loader, 'civic_battle_prelate_m', profile);
    expect(modules).toHaveLength(10);
    expect(modules.every(module => module.models.length === 3)).toBe(true);
    expect(campaignEquipmentKeys('civic_battle_prelate_m').map(module => module.slot)).toContain('tabard');
    const bodyModels = await loader.resolveApprovedAssetModels('civic_battle_prelate_m', 'characterProfiles');
    const { object: body } = await readAuthoredModel(bodyModels[level]);
    const originalBones = new Set<THREE.Bone>();
    body.traverse(node => { if ((node as THREE.Bone).isBone) originalBones.add(node as THREE.Bone); });
    const meshLoader = { loadModelFull: vi.fn(readAuthoredModel) };
    await assembleCampaignEquipment(body, modules, level, meshLoader);
    expect(meshLoader.loadModelFull.mock.calls.map(([filename]) => filename)).toEqual(modules.map(module => module.models[level]));
    const overlays: THREE.Object3D[] = [];
    body.traverse(node => { if (node.userData.equipmentOverlay) overlays.push(node); });
    expect(overlays).toHaveLength(10);
    const weapon = overlays.find(overlay => overlay.userData.equipmentSlot === 'mainHand')!;
    expect(weapon.parent?.name).toBe('socket_hand_R');
    expect(weapon.position.toArray()).toEqual([0, 0, 0]);
    const bodyBones = new Map([...originalBones].map(bone => [bone.name, bone]));
    for (const overlay of overlays.filter(overlay => overlay !== weapon)) overlay.traverse(node => {
      const mesh = node as THREE.SkinnedMesh;
      if (!mesh.isSkinnedMesh) return;
      expect(mesh.skeleton.bones.every(bone => originalBones.has(bone))).toBe(true);
      for (const bone of mesh.skeleton.bones) expect(bone).toBe(bodyBones.get(bone.name));
    });
    // The promoted body is one fitted underlayer: never hide its exposed face and joints.
    expect(body.getObjectByName(`battle_prelate_body_lod${level}`)?.visible).toBe(true);
    const geometryDisposers: ReturnType<typeof vi.spyOn>[] = [];
    body.traverse(node => { if ((node as THREE.Mesh).isMesh) geometryDisposers.push(vi.spyOn((node as THREE.Mesh).geometry, 'dispose')); });
    releaseCampaignActor(body);
    expect(geometryDisposers.every(spy => spy.mock.calls.length === 0)).toBe(true);
    loader.dispose();
  });

  test('a cancelled equipment load disposes the orphan skeleton and never publishes a partial actor', async () => {
    const loader = installManifestFetch();
    const modules = await resolveCampaignEquipment(loader, 'civic_battle_prelate_m', profile);
    const { object: body } = await readAuthoredModel(profile.model);
    const { object: armor } = await readAuthoredModel(modules[0].models[0]);
    const disposers: ReturnType<typeof vi.spyOn>[] = [];
    const skeletons = new Set<THREE.Skeleton>();
    armor.traverse(node => { if ((node as THREE.SkinnedMesh).isSkinnedMesh) skeletons.add((node as THREE.SkinnedMesh).skeleton); });
    for (const skeleton of skeletons) disposers.push(vi.spyOn(skeleton, 'dispose'));
    let active = true;
    await expect(assembleCampaignEquipment(body, modules, 0, { loadModelFull: async () => {
      active = false; return { object: armor, animations: [] };
    } }, load => load(), () => active)).rejects.toThrow('actor released');
    expect(armor.parent).toBeNull();
    expect(disposers.every(spy => spy.mock.calls.length === 1)).toBe(true);
    expect(body.userData.campaignEquipmentComplete).toBeUndefined();
    releaseCampaignActor(body); loader.dispose();
  });

  test('incompatible armor fails before partial skeleton binding and removes earlier equipment', async () => {
    const loader = installManifestFetch();
    const modules = await resolveCampaignEquipment(loader, 'civic_battle_prelate_m', profile);
    const { object: body } = await readAuthoredModel(profile.model);
    let loads = 0;
    const meshLoader = { loadModelFull: async (filename: string) => {
      const loaded = await readAuthoredModel(filename);
      if (++loads === 2) loaded.object.traverse(node => { if ((node as THREE.Bone).isBone) node.name = `wrong_${node.name}`; });
      return loaded;
    } };
    await expect(assembleCampaignEquipment(body, modules, 0, meshLoader)).rejects.toThrow('skeleton mismatch');
    const overlays: THREE.Object3D[] = [];
    body.traverse(node => { if (node.userData.equipmentOverlay) overlays.push(node); });
    expect(overlays).toHaveLength(0);
    expect(body.userData.campaignEquipmentComplete).toBeUndefined();
    releaseCampaignActor(body); loader.dispose();
  });

  test('merges locomotion and animation packs while stripping client root motion and scale', () => {
    const idle = new THREE.AnimationClip('idle', 1, [new THREE.VectorKeyframeTrack('root.position', [0, 1], [0, 0, 0, 10, 0, 0])]);
    const run = new THREE.AnimationClip('run', 1, [new THREE.VectorKeyframeTrack('pelvis.scale', [0, 1], [1, 1, 1, 2, 2, 2])]);
    const attack = new THREE.AnimationClip('attack', 1, [new THREE.QuaternionKeyframeTrack('hand_R.quaternion', [0], [0, 0, 0, 1])]);
    const clips = campaignAnimationClips([idle, run], [attack]);
    expect(clips.map(clip => clip.name)).toEqual(['idle', 'run', 'attack']);
    expect(clips.map(clip => clip.tracks.length)).toEqual([0, 0, 1]);
    expect(idle.tracks).toHaveLength(1);
  });

  test('maps reviewed faction roles without substituting a human for an unbuilt racial profile', () => {
    expect(campaignNpcProfile({ id: 'keep_commander', role: 'commander', race: 'empire', realm: 'aegis' })).toBe('npc_aegis_city_guard_captain');
    expect(campaignNpcProfile({ id: 'trainer', role: 'trainer', race: 'empire' })).toBe('npc_aegis_people_attendant');
    for (const race of ['chaos', 'greenskin', 'dark_elf']) expect(campaignNpcProfile({ id: 'rift_guard', role: 'guard', race, realm: 'riftbound' })).toBe(`npc_riftspire_${race}`);
    for (const race of ['dwarf', 'high_elf']) expect(campaignNpcProfile({ id: 'scout', role: 'guard', race, realm: 'aegis' })).toBeUndefined();
    expect(campaignNpcProfile({ id: 'captured_guard', role: 'guard', race: 'empire', realm: 'riftbound' })).toBe('npc_riftspire_chaos');
    expect(campaignNpcProfile({ id: 'citizen', role: 'ambient', profileKey: 'npc_aegis_people_child' })).toBe('npc_aegis_people_child');
  });
});
