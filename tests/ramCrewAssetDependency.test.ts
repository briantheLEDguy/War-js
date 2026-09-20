import fs from 'node:fs';
import path from 'node:path';
import { webcrypto } from 'node:crypto';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { AssetLoader } from '../src/game/AssetLoader';

afterEach(() => { vi.unstubAllGlobals(); vi.restoreAllMocks(); });

function fetchPublished(tamper?: string) {
  const root = path.resolve('public');
  vi.stubGlobal('crypto', webcrypto);
  vi.stubGlobal('fetch', async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost'), filename = path.resolve(root, '.' + decodeURIComponent(url.pathname));
    if (!filename.startsWith(root + path.sep) || !fs.existsSync(filename)) return new Response(null, { status: 404 });
    const bytes = fs.readFileSync(filename);
    if (tamper && filename.endsWith(tamper)) bytes[bytes.length - 1] ^= 1;
    return new Response(bytes);
  });
}

describe('published ram crew dependencies', () => {
  it('resolves the signed packs from the same approved ram manifest and binds both literal exports', async () => {
    fetchPublished();
    const loader = new AssetLoader();
    const packs = await loader.resolveStaticOperatorAnimationPacks('frontier_battering_ram');
    const manifest = JSON.parse(fs.readFileSync('scripts/blender-character-pipeline/data/approved-assets/frontier_battering_ram.approved.json', 'utf8'));
    const qc = JSON.parse(fs.readFileSync('public/assets/models/frontier_battering_ram_lod0.qc.json', 'utf8'));
    expect(packs).toEqual(manifest.runtime.operatorAnimationPacks);
    expect(packs).toEqual(qc.operatorAnimationPacks);
    for (const pack of Object.values(packs!)) {
      const bytes = fs.readFileSync(`public/assets/models/${pack.model}`);
      const root = (await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '')).scene;
      const clips = await loader.loadCharacterAnimations({ model: 'approved-body.glb', skeletonId: 'humanoid_game_v2', bindPoseId: 'a_pose_v2', animationPack: pack }, root);
      expect(clips.map(clip => clip.name)).toEqual(['ram_crew_idle', 'ram_crew_drive', 'ram_crew_strike']);
    }
    loader.dispose();
  });

  it('refuses modified pack bytes and leaves the existing avatar available', async () => {
    fetchPublished('frontier_ram_crew_left_animations.glb');
    const warning = vi.spyOn(console, 'warn').mockImplementation(() => undefined), loader = new AssetLoader();
    const packs = await loader.resolveStaticOperatorAnimationPacks('frontier_battering_ram');
    const bytes = fs.readFileSync('public/assets/models/frontier_ram_crew_left_animations.glb');
    const root = (await new GLTFLoader().parseAsync(bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength), '')).scene;
    const children = [...root.children];
    const clips = await loader.loadCharacterAnimations({ model: 'approved-body.glb', skeletonId: 'humanoid_game_v2', bindPoseId: 'a_pose_v2', animationPack: packs!.left }, root);
    expect(clips).toEqual([]); expect(root.children).toEqual(children);
    expect(warning).toHaveBeenCalledWith('[AssetLoader] animation pack fallback:', expect.objectContaining({ message: 'Animation pack hash mismatch' }));
    loader.dispose();
  });
});
