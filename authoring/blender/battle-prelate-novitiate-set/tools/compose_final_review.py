"""Contact sheet of actual reimport renders; no changes to asset appearance."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
NAMES = [
    'reimport_lod0_full_front_material.png',
    'reimport_lod0_full_three_quarter_material.png',
    'reimport_lod0_full_side_material.png',
    'reimport_lod0_full_back_material.png',
    'reimport_lod0_full_front_neutral.png',
    'reimport_lod1_full_front_material.png',
    'reimport_lod2_full_front_material.png',
    'exported_motion_supplemental_late_death_wide.png',
]

if __name__ == '__main__':
    sheet = Image.new('RGB', (1600, 1100), '#303438')
    records = []
    for index, name in enumerate(NAMES):
        path = ROOT / 'review' / name
        original = Image.open(path).convert('RGB')
        original.thumbnail((400, 518))
        x, y = index % 4 * 400, index // 4 * 550
        sheet.paste(original, (x + (400-original.width)//2, y))
        ImageDraw.Draw(sheet).text((x+8, y+522), name.replace('reimport_', '').replace('_material.png', '').replace('.png', ''), fill='white')
        records.append({'path': 'review/'+name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    output = ROOT/'review/final_contact.png'
    sheet.save(output)
    (ROOT/'review/final_contact.json').write_text(json.dumps({'inputs': records, 'image_sha256': hashlib.sha256(output.read_bytes()).hexdigest()}, indent=2)+'\n')
