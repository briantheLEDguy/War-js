"""Arrange actual export views at equal pixels-per-metre within each asset row."""
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = [
    ('oak_pasture', 'Pasture oak'), ('oak_hedgerow', 'Hedgerow oak'),
    ('ash', 'Ash'), ('hawthorn', 'Hawthorn hedgerow'),
    ('wheat', 'Wheat'), ('meadow', 'Meadow grasses / wildflowers'),
    ('limestone', 'Weathered limestone'),
]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def font(size, bold=False):
    candidates = [Path('C:/Windows/Fonts') / ('segoeuib.ttf' if bold else 'segoeui.ttf')]
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(str(candidate), size)
    return ImageFont.load_default(size=size)


def main():
    width, cell, row_height, header = 1800, 600, 674, 118
    canvas = Image.new('RGB', (width, header + row_height * len(ASSETS)), '#172124')
    draw = ImageDraw.Draw(canvas)
    draw.text((24, 15), 'SUNMEADOW / ACTUAL GLB EXPORT REVIEW', font=font(31, True), fill='#f3f1df')
    draw.text((24, 62), 'Each row uses equal pixels per metre. Scale differs between assets. No paintovers or substituted source views.', font=font(21), fill='#bbc9c7')
    evidence = []
    for row, (kind, title) in enumerate(ASSETS):
        key = 'frontier_sunmeadow_' + kind
        record = json.loads((ROOT / 'review' / f'{key}_renders.json').read_text())
        renders = sorted(record['renders'], key=lambda item: item['level'])
        if [item['level'] for item in renders] != [0, 1, 2]:
            raise ValueError(f'{key}: all three export views are required')
        maximum_span = max(max(item['bounds_blender']['span']) for item in renders)
        y = header + row * row_height
        draw.text((24, y + 3), title, font=font(26, True), fill='#f3f1df')
        for col, item in enumerate(renders):
            source = ROOT / item['image']
            model = ROOT / 'runtime' / item['model']
            if sha(source) != item['image_sha256'] or sha(model) != item['model_sha256']:
                raise ValueError(f'{key}: stale reimport evidence')
            # Existing orthographic views use max(span) * 1.3. Reframe all three
            # to the largest span without distorting their geometry or pixels.
            ratio = max(item['bounds_blender']['span']) / maximum_span
            target = round(580 * ratio)
            with Image.open(source) as image:
                resized = image.convert('RGB').resize((target, target), Image.Resampling.LANCZOS)
                panel = Image.new('RGB', (580, 580), image.getpixel((0, 0))[:3])
                panel.paste(resized, ((580 - target) // 2, (580 - target) // 2))
            x = col * cell + 10
            canvas.paste(panel, (x, y + 43))
            draw.text((x + 8, y + 630), f'LOD{col}  /  {key}', font=font(19), fill='#c5d1ce')
            evidence.append({'asset': key, 'level': col, 'model_sha256': item['model_sha256'],
                             'source_image': item['image'], 'source_image_sha256': item['image_sha256'],
                             'pixels_per_metre': 580 / (1.3 * maximum_span)})
    output = ROOT / 'review' / 'exports_contact_sheet.png'
    canvas.save(output)
    canvas.resize((1200, round(canvas.height * 1200 / canvas.width)), Image.Resampling.LANCZOS).save(
        ROOT / 'review' / 'exports_contact_sheet_preview.png')
    canvas.resize((1200, round(canvas.height * 1200 / canvas.width)), Image.Resampling.LANCZOS).save(
        ROOT / 'review' / 'exports_contact_sheet_preview.png')
    (output.with_suffix('.json')).write_text(json.dumps({'image': output.name,
        'image_sha256': sha(output), 'method': 'Unretouched actual reimport PNGs; equal per-row metric scale',
        'sources': evidence}, indent=2) + '\n')
    print(output)


if __name__ == '__main__':
    main()
