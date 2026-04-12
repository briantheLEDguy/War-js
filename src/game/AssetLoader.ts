import * as THREE from 'three';
import { GLTFLoader, type GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { RGBELoader } from 'three/examples/jsm/loaders/RGBELoader.js';
import { useGameStore } from '../state/gameStore';

export type PrimitiveFactory = () => THREE.Object3D;

const BASE = import.meta.env.BASE_URL; // '/' in dev, '/War-js/' on GH Pages

/**
 * Asset loader with primitive fallbacks. If a file is missing or fails to load,
 * the fallback is returned and a counter in the debug overlay increments.
 *
 * Phase 2 note: when the WAR asset pipeline lands, converted .glb files drop
 * into /public/assets/models/ using the same names referenced here, no code
 * change required.
 */
export class AssetLoader {
  private gltfLoader = new GLTFLoader();
  private texLoader = new THREE.TextureLoader();
  private rgbeLoader = new RGBELoader();
  private modelCache = new Map<string, Promise<THREE.Object3D>>();
  private texCache = new Map<string, Promise<THREE.Texture>>();

  async loadModel(path: string, fallback: PrimitiveFactory): Promise<THREE.Object3D> {
    const cached = this.modelCache.get(path);
    if (cached) {
      const obj = await cached;
      return obj.clone(true);
    }
    const promise = this.gltfLoader
      .loadAsync(`${BASE}assets/models/${path}`)
      .then((g: GLTF) => {
        const scene = g.scene;
        scene.traverse((n) => {
          if ((n as THREE.Mesh).isMesh) {
            n.castShadow = true;
            n.receiveShadow = true;
          }
        });
        return scene as THREE.Object3D;
      })
      .catch((err) => {
        console.warn(`[AssetLoader] model fallback for ${path}:`, err.message);
        useGameStore.getState().incAssetFallbacks();
        return fallback();
      });
    this.modelCache.set(path, promise);
    const base = await promise;
    return base.clone(true);
  }

  async loadTexture(path: string, fallbackColor = 0x555555): Promise<THREE.Texture | null> {
    const cached = this.texCache.get(path);
    if (cached) return cached;
    const promise = this.texLoader
      .loadAsync(`${BASE}assets/textures/${path}`)
      .then((t) => {
        t.wrapS = t.wrapT = THREE.RepeatWrapping;
        t.colorSpace = THREE.SRGBColorSpace;
        return t;
      })
      .catch((err) => {
        console.warn(`[AssetLoader] texture fallback for ${path}:`, err.message);
        useGameStore.getState().incAssetFallbacks();
        // Return a 1x1 fallback texture of the requested color
        const data = new Uint8Array([
          (fallbackColor >> 16) & 0xff,
          (fallbackColor >> 8) & 0xff,
          fallbackColor & 0xff,
          255,
        ]);
        const tex = new THREE.DataTexture(data, 1, 1, THREE.RGBAFormat);
        tex.needsUpdate = true;
        tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
        return tex;
      });
    this.texCache.set(path, promise);
    return promise;
  }

  async loadHDRI(path: string): Promise<THREE.Texture | null> {
    try {
      const tex = await this.rgbeLoader.loadAsync(`${BASE}assets/hdri/${path}`);
      tex.mapping = THREE.EquirectangularReflectionMapping;
      return tex;
    } catch (err) {
      console.warn(`[AssetLoader] HDRI fallback for ${path}:`, (err as Error).message);
      useGameStore.getState().incAssetFallbacks();
      return null;
    }
  }

  /** Common primitive fallbacks. */
  static primitives = {
    humanoid(color = 0x7a6425): THREE.Object3D {
      const group = new THREE.Group();
      const bodyMat = new THREE.MeshStandardMaterial({ color });
      const skinMat = new THREE.MeshStandardMaterial({ color: 0xe6c29a });
      const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.35, 0.9, 4, 8), bodyMat);
      body.position.y = 0.95;
      body.castShadow = true;
      group.add(body);
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.22, 12, 12), skinMat);
      head.position.y = 1.75;
      head.castShadow = true;
      group.add(head);
      // forward indicator (nose)
      const nose = new THREE.Mesh(new THREE.ConeGeometry(0.06, 0.12, 8), skinMat);
      nose.rotation.x = Math.PI / 2;
      nose.position.set(0, 1.75, 0.22);
      group.add(nose);
      return group;
    },
    dummy(): THREE.Object3D {
      const group = new THREE.Group();
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x6b4a25 });
      const strawMat = new THREE.MeshStandardMaterial({ color: 0xbda44a });
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.1, 1.6, 10), woodMat);
      pole.position.y = 0.8;
      pole.castShadow = true;
      group.add(pole);
      const body = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.4, 0.9, 12), strawMat);
      body.position.y = 1.25;
      body.castShadow = true;
      group.add(body);
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.25, 10, 10), strawMat);
      head.position.y = 1.85;
      head.castShadow = true;
      group.add(head);
      return group;
    },
    tree(): THREE.Object3D {
      const group = new THREE.Group();
      const trunkMat = new THREE.MeshStandardMaterial({ color: 0x4a2f15 });
      const leafMat = new THREE.MeshStandardMaterial({ color: 0x2f5a25 });
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.2, 0.3, 1.8, 8), trunkMat);
      trunk.position.y = 0.9;
      trunk.castShadow = true;
      group.add(trunk);
      const leaves = new THREE.Mesh(new THREE.ConeGeometry(1.2, 2.6, 10), leafMat);
      leaves.position.y = 2.5;
      leaves.castShadow = true;
      group.add(leaves);
      return group;
    },
    rock(): THREE.Object3D {
      const mat = new THREE.MeshStandardMaterial({ color: 0x6a6a66, flatShading: true });
      const geo = new THREE.DodecahedronGeometry(0.7, 0);
      const m = new THREE.Mesh(geo, mat);
      m.castShadow = true;
      m.position.y = 0.5;
      m.scale.set(1, 0.7 + Math.random() * 0.4, 1);
      m.rotation.y = Math.random() * Math.PI * 2;
      return m;
    },
    building(): THREE.Object3D {
      const group = new THREE.Group();
      const wallMat = new THREE.MeshStandardMaterial({ color: 0xa89270 });
      const roofMat = new THREE.MeshStandardMaterial({ color: 0x6a2815 });
      const base = new THREE.Mesh(new THREE.BoxGeometry(4, 2.5, 3), wallMat);
      base.position.y = 1.25;
      base.castShadow = true;
      base.receiveShadow = true;
      group.add(base);
      const roof = new THREE.Mesh(
        new THREE.ConeGeometry(3, 1.6, 4),
        roofMat,
      );
      roof.rotation.y = Math.PI / 4;
      roof.position.y = 3.3;
      roof.scale.set(1.1, 1, 0.85);
      roof.castShadow = true;
      group.add(roof);
      return group;
    },

    // --- WAR city prop primitives ---

    /** City perimeter wall segment — long stone block. */
    wall_segment(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x8a8a80, roughness: 0.9 });
      const capMat = new THREE.MeshStandardMaterial({ color: 0x707068, roughness: 0.9 });
      const wall = new THREE.Mesh(new THREE.BoxGeometry(10, 4, 1.5), stoneMat);
      wall.position.y = 2;
      wall.castShadow = true;
      wall.receiveShadow = true;
      group.add(wall);
      // Crenellations (merlons)
      for (let i = -4; i <= 4; i += 2) {
        const merlon = new THREE.Mesh(new THREE.BoxGeometry(0.8, 1, 1.5), capMat);
        merlon.position.set(i, 4.5, 0);
        merlon.castShadow = true;
        group.add(merlon);
      }
      return group;
    },

    /** City wall tower — tall cylindrical stone tower with crenellations. */
    tower(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x7a7870, roughness: 0.9 });
      const capMat = new THREE.MeshStandardMaterial({ color: 0x606058 });
      const body = new THREE.Mesh(new THREE.CylinderGeometry(1.8, 2.0, 12, 12), stoneMat);
      body.position.y = 6;
      body.castShadow = true;
      body.receiveShadow = true;
      group.add(body);
      const top = new THREE.Mesh(new THREE.CylinderGeometry(2.0, 2.0, 0.5, 12), capMat);
      top.position.y = 12.25;
      group.add(top);
      // Crenellations on top
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        const merlon = new THREE.Mesh(new THREE.BoxGeometry(0.6, 1.2, 0.6), capMat);
        merlon.position.set(Math.cos(a) * 1.8, 13.1, Math.sin(a) * 1.8);
        group.add(merlon);
      }
      return group;
    },

    /** City gate — two flanking towers with portcullis arch. */
    gate(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x7a7870, roughness: 0.9 });
      const archMat = new THREE.MeshStandardMaterial({ color: 0x5a5850 });
      // Left tower
      const tL = new THREE.Mesh(new THREE.CylinderGeometry(2, 2.2, 14, 12), stoneMat);
      tL.position.set(-5, 7, 0);
      tL.castShadow = true;
      group.add(tL);
      // Right tower
      const tR = tL.clone();
      tR.position.set(5, 7, 0);
      group.add(tR);
      // Connecting arch lintel
      const lintel = new THREE.Mesh(new THREE.BoxGeometry(10, 2, 3), stoneMat);
      lintel.position.set(0, 8, 0);
      lintel.castShadow = true;
      group.add(lintel);
      // Arch soffit (dark interior)
      const arch = new THREE.Mesh(new THREE.BoxGeometry(4, 6, 3.1), archMat);
      arch.position.set(0, 4, 0);
      group.add(arch);
      return group;
    },

    /** Temple of Sigmar — large gothic cathedral silhouette. */
    temple(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0xc8b890, roughness: 0.85 });
      const roofMat = new THREE.MeshStandardMaterial({ color: 0x485868 });
      const goldMat = new THREE.MeshStandardMaterial({ color: 0xd4aa20, metalness: 0.6, roughness: 0.4 });
      // Main nave
      const nave = new THREE.Mesh(new THREE.BoxGeometry(12, 8, 20), stoneMat);
      nave.position.y = 4;
      nave.castShadow = true;
      nave.receiveShadow = true;
      group.add(nave);
      // Nave roof
      const naveRoof = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 7, 4, 4), roofMat);
      naveRoof.position.set(0, 10, 0);
      naveRoof.rotation.y = Math.PI / 4;
      group.add(naveRoof);
      // Central spire
      const spireBase = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.8, 10, 8), stoneMat);
      spireBase.position.set(0, 13, 0);
      spireBase.castShadow = true;
      group.add(spireBase);
      const spire = new THREE.Mesh(new THREE.ConeGeometry(1.2, 8, 8), roofMat);
      spire.position.set(0, 21, 0);
      spire.castShadow = true;
      group.add(spire);
      // Spire tip (gold)
      const tip = new THREE.Mesh(new THREE.ConeGeometry(0.15, 1.2, 6), goldMat);
      tip.position.set(0, 25.5, 0);
      group.add(tip);
      // Side transepts
      for (const side of [-1, 1]) {
        const transept = new THREE.Mesh(new THREE.BoxGeometry(5, 6, 8), stoneMat);
        transept.position.set(side * 8.5, 3, 0);
        transept.castShadow = true;
        group.add(transept);
        const tRoof = new THREE.Mesh(new THREE.ConeGeometry(4, 3, 4), roofMat);
        tRoof.position.set(side * 8.5, 7.5, 0);
        tRoof.rotation.y = Math.PI / 4;
        group.add(tRoof);
      }
      // Buttresses
      for (const dz of [-6, 0, 6]) {
        for (const side of [-1, 1]) {
          const butt = new THREE.Mesh(new THREE.BoxGeometry(1.5, 6, 1.5), stoneMat);
          butt.position.set(side * 7, 3, dz);
          group.add(butt);
        }
      }
      return group;
    },

    /** Decorative statue on a pedestal (Karl Franz / Sigmar style). */
    statue(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0xb0a890, roughness: 0.8 });
      // Pedestal
      const ped = new THREE.Mesh(new THREE.BoxGeometry(1.6, 1.8, 1.6), stoneMat);
      ped.position.y = 0.9;
      ped.castShadow = true;
      group.add(ped);
      // Figure
      const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.3, 1.0, 4, 8), stoneMat);
      body.position.y = 2.6;
      body.castShadow = true;
      group.add(body);
      const head = new THREE.Mesh(new THREE.SphereGeometry(0.2, 8, 8), stoneMat);
      head.position.y = 3.6;
      group.add(head);
      // Raised arm + weapon
      const arm = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 1.0, 6), stoneMat);
      arm.rotation.z = -Math.PI / 3;
      arm.position.set(0.5, 3.0, 0);
      group.add(arm);
      const weapon = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.8, 6), stoneMat);
      weapon.position.set(0.9, 3.5, 0);
      group.add(weapon);
      return group;
    },

    /** Plaza fountain — basin, column, water sphere. */
    fountain(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0xa0a098, roughness: 0.7 });
      const waterMat = new THREE.MeshStandardMaterial({
        color: 0x3a80c0,
        transparent: true,
        opacity: 0.7,
        roughness: 0.1,
        metalness: 0.2,
      });
      // Outer basin
      const basin = new THREE.Mesh(new THREE.CylinderGeometry(2.8, 2.5, 0.6, 16), stoneMat);
      basin.position.y = 0.3;
      basin.castShadow = true;
      group.add(basin);
      // Water surface
      const water = new THREE.Mesh(new THREE.CylinderGeometry(2.4, 2.4, 0.1, 16), waterMat);
      water.position.y = 0.55;
      group.add(water);
      // Central column
      const col = new THREE.Mesh(new THREE.CylinderGeometry(0.25, 0.3, 2.5, 10), stoneMat);
      col.position.y = 1.55;
      col.castShadow = true;
      group.add(col);
      // Top bowl
      const topBowl = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 0.8, 0.4, 12), stoneMat);
      topBowl.position.y = 2.8;
      group.add(topBowl);
      // Water sphere (jets)
      const jet = new THREE.Mesh(new THREE.SphereGeometry(0.4, 8, 8), waterMat);
      jet.position.y = 3.5;
      group.add(jet);
      return group;
    },

    /** Empire banner post — red panel with gold trim. */
    banner_post(): THREE.Object3D {
      const group = new THREE.Group();
      const poleMat = new THREE.MeshStandardMaterial({ color: 0x806010, metalness: 0.3 });
      const bannerMat = new THREE.MeshStandardMaterial({
        color: 0xcc1010,
        side: THREE.DoubleSide,
      });
      const trimMat = new THREE.MeshStandardMaterial({ color: 0xd4aa20, metalness: 0.6 });
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.09, 6, 8), poleMat);
      pole.position.y = 3;
      pole.castShadow = true;
      group.add(pole);
      // Banner panel
      const banner = new THREE.Mesh(new THREE.PlaneGeometry(1.2, 2.0), bannerMat);
      banner.position.set(0.6, 5.2, 0);
      group.add(banner);
      // Gold crossbar
      const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 1.5, 6), trimMat);
      bar.rotation.z = Math.PI / 2;
      bar.position.set(0.6, 6.3, 0);
      group.add(bar);
      // Tip finial
      const finial = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.4, 6), trimMat);
      finial.position.y = 6.2;
      group.add(finial);
      return group;
    },

    /** Market vendor stall — canopy and counter. */
    vendor_stall(): THREE.Object3D {
      const group = new THREE.Group();
      const woodMat = new THREE.MeshStandardMaterial({ color: 0x7a5830 });
      const canopyMat = new THREE.MeshStandardMaterial({ color: 0xb04020, side: THREE.DoubleSide });
      // Counter
      const counter = new THREE.Mesh(new THREE.BoxGeometry(2.5, 0.8, 1.0), woodMat);
      counter.position.y = 0.8;
      counter.castShadow = true;
      group.add(counter);
      // Legs
      for (const [px, pz] of [[-1, -0.4], [1, -0.4], [-1, 0.4], [1, 0.4]]) {
        const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 1.6, 6), woodMat);
        leg.position.set(px, 0.8, pz);
        group.add(leg);
      }
      // Canopy
      const canopy = new THREE.Mesh(new THREE.BoxGeometry(3, 0.15, 1.8), canopyMat);
      canopy.position.y = 2.2;
      canopy.rotation.x = -0.15;
      canopy.castShadow = true;
      group.add(canopy);
      // Support poles
      for (const px of [-1.1, 1.1]) {
        const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 2.2, 6), woodMat);
        pole.position.set(px, 1.1, -0.6);
        group.add(pole);
      }
      return group;
    },

    /** Wide stone steps for temple approaches. */
    steps(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0xb8aa90, roughness: 0.8 });
      for (let i = 0; i < 5; i++) {
        const step = new THREE.Mesh(
          new THREE.BoxGeometry(8 - i * 0.5, 0.3, 1.0),
          stoneMat,
        );
        step.position.set(0, i * 0.3, -i * 1.0);
        step.castShadow = true;
        step.receiveShadow = true;
        group.add(step);
      }
      return group;
    },

    /** Stone arch bridge. */
    bridge(): THREE.Object3D {
      const group = new THREE.Group();
      const stoneMat = new THREE.MeshStandardMaterial({ color: 0x9a9280, roughness: 0.9 });
      // Deck
      const deck = new THREE.Mesh(new THREE.BoxGeometry(4, 0.4, 12), stoneMat);
      deck.position.y = 3.2;
      deck.castShadow = true;
      deck.receiveShadow = true;
      group.add(deck);
      // Arch piers
      for (const pz of [-3, 3]) {
        const pier = new THREE.Mesh(new THREE.BoxGeometry(4, 3, 1.5), stoneMat);
        pier.position.set(0, 1.5, pz);
        pier.castShadow = true;
        group.add(pier);
      }
      // Arch (approximated as a cylinder segment)
      const arch = new THREE.Mesh(new THREE.CylinderGeometry(3, 3, 4, 12, 1, true, 0, Math.PI), stoneMat);
      arch.rotation.z = Math.PI / 2;
      arch.position.set(0, 3, 0);
      group.add(arch);
      // Parapets
      for (const px of [-1.8, 1.8]) {
        const parapet = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1.0, 12), stoneMat);
        parapet.position.set(px, 3.9, 0);
        parapet.castShadow = true;
        group.add(parapet);
      }
      return group;
    },

    /** Wooden dock/pier with mooring posts. */
    dock(): THREE.Object3D {
      const group = new THREE.Group();
      const plankMat = new THREE.MeshStandardMaterial({ color: 0x6b4820, roughness: 0.95 });
      const postMat = new THREE.MeshStandardMaterial({ color: 0x4a3010 });
      // Deck planks
      const deck = new THREE.Mesh(new THREE.BoxGeometry(4, 0.2, 14), plankMat);
      deck.position.y = 0.3;
      deck.castShadow = true;
      deck.receiveShadow = true;
      group.add(deck);
      // Support piles
      for (const [px, pz] of [[-1.5, -5], [0, -5], [1.5, -5], [-1.5, 5], [0, 5], [1.5, 5]]) {
        const pile = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.15, 2.5, 8), postMat);
        pile.position.set(px, -0.9, pz);
        group.add(pile);
      }
      // Mooring posts
      for (const pz of [-4, 0, 4]) {
        const post = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 1.2, 8), postMat);
        post.position.set(2.2, 0.9, pz);
        group.add(post);
      }
      return group;
    },

    // --- NPC role-colored humanoids ---

    /** City guard — armored soldier (steel blue). */
    npc_guard(): THREE.Object3D {
      return AssetLoader.primitives.humanoid(0x4a6080);
    },
    /** Vendor NPC (brown/tan). */
    npc_vendor(): THREE.Object3D {
      return AssetLoader.primitives.humanoid(0x8a6040);
    },
    /** Career trainer NPC (gold). */
    npc_trainer(): THREE.Object3D {
      return AssetLoader.primitives.humanoid(0xa88020);
    },
    /** Banker NPC (silver). */
    npc_banker(): THREE.Object3D {
      return AssetLoader.primitives.humanoid(0x909090);
    },
    /** Quest giver NPC (yellow — WAR's exclamation mark equivalent). */
    npc_quest(): THREE.Object3D {
      return AssetLoader.primitives.humanoid(0xd0b020);
    },
  };
}
