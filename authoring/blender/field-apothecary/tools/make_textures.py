"""Deterministic source-backed PBR fields for the original apothecary surfaces."""
import hashlib, json
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SIZE = 1024
rng = np.random.default_rng(92026)
y, x = np.mgrid[0:SIZE, 0:SIZE] / SIZE

def noise(size):
    # Repeat before resampling so opposing texture edges meet without board seams.
    tile = np.uint8(rng.random((size, size)) * 255)
    image = Image.fromarray(np.tile(tile, (3, 3))).resize((SIZE * 3, SIZE * 3), Image.Resampling.BICUBIC)
    return np.asarray(image.crop((SIZE, SIZE, SIZE * 2, SIZE * 2)), dtype=float) / 255

def field(name):
    broad, medium, fine = noise(12), noise(68), noise(330)
    if name in ('timber', 'endgrain'):
        grain = np.sin(x * np.pi * 120 + np.sin(y * np.pi * 6 + broad * 1.8) * 3 + broad * 9)
        pores = np.maximum(0, grain - .60) ** 1.4
        if name == 'endgrain':
            radius = np.sqrt((x - .42) ** 2 + ((y - .55) * 1.25) ** 2)
            pores = np.maximum(0, np.sin(radius * 210 + broad * 4) - .25)
        wear = np.clip((broad - .55) * 1.6, 0, .45)
        color = np.array([.36, .245, .125])[None, None, :] * (.70 + broad[:, :, None] * .65)
        color -= pores[:, :, None] * np.array([.082, .063, .036])
        color += wear[:, :, None] * np.array([.16, .13, .08])
        height = broad * .16 - pores * .12 + fine * .035
        rough = .74 + medium * .13 - wear * .14
        metal = 0
    elif name == 'iron':
        color = np.array([.105, .118, .125])[None, None, :] * (.6 + broad[:, :, None] * .8)
        oxide = np.maximum(0, medium - .67)[:, :, None]
        color += oxide * np.array([.16, .058, .01])
        height, rough, metal = medium * .08 + fine * .025, .46 + broad * .20, .88
    elif name == 'leather':
        color = np.array([.20, .105, .046])[None, None, :] * (.75 + broad[:, :, None] * .60)
        height, rough, metal = medium * .08 + fine * .08, .67 + broad * .16, 0
    elif name == 'amber':
        color = np.array([.29, .12, .025])[None, None, :] * (.92 + broad[:, :, None] * .13)
        height, rough, metal = fine * .008, .21 + broad * .08, 0
    elif name in ('sage', 'dried'):
        vein = np.exp(-((x - .5) * 95) ** 2)
        secondary = np.maximum(0, np.sin((y + np.abs(x - .5) * .36) * 83) - .87)
        tone = [.185, .265, .09] if name == 'sage' else [.34, .235, .072]
        color = np.array(tone)[None, None, :] * (.68 + broad[:, :, None] * .6)
        color += (vein + secondary)[:, :, None] * np.array([.055, .04, .009])
        height, rough, metal = vein * .1 + secondary * .04 + fine * .025, .86 + medium * .1, 0
    elif name == 'linen':
        weave = (np.sin(x * SIZE * 1.6) + np.sin(y * SIZE * 1.6)) * .5
        color = np.array([.48, .39, .24])[None, None, :] * (.75 + broad[:, :, None] * .35)
        height, rough, metal = weave * .055 + fine * .035, .88 + medium * .09, 0
    else:
        color = np.array([.38, .37, .28])[None, None, :] * (.75 + broad[:, :, None] * .40)
        height, rough, metal = medium * .12 + fine * .045, .69 + medium * .14, 0
    dy, dx = np.gradient(height)
    normals = np.stack((-dx * 11, -dy * 11, np.ones_like(x)), axis=-1)
    normals /= np.linalg.norm(normals, axis=-1, keepdims=True)
    return {
        'basecolor': np.clip(color, 0, 1),
        'normal': normals * .5 + .5,
        'orm': np.stack((np.ones_like(x), np.broadcast_to(rough, x.shape), np.full_like(x, metal)), axis=-1),
    }

if __name__ == '__main__':
    folder = ROOT / 'textures'; folder.mkdir(parents=True, exist_ok=True)
    receipts = {}
    for name in ('timber', 'endgrain', 'iron', 'leather', 'amber', 'sage', 'dried', 'linen', 'stoneware'):
        for channel, pixels in field(name).items():
            original = Image.fromarray(np.uint8(np.clip(pixels, 0, 1) * 255))
            for lod, size in enumerate((1024, 512, 256)):
                target = folder / f'{name}_lod{lod}_{channel}.png'
                original.resize((size, size), Image.Resampling.LANCZOS).save(target)
                receipts[str(target.relative_to(ROOT)).replace('\\', '/')] = {'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'size': size}
    (folder / 'sources.json').write_text(json.dumps({'generatorSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'seed': 92026, 'textures': receipts}, indent=2) + '\n')
    print('TEXTURES_SAVED', len(receipts))
