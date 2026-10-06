"""Compare a single GM diagnostic run; measurements supplement visual inspection."""
import argparse
import json
import re
from pathlib import Path

from PIL import Image, ImageChops, ImageStat


def compare(folder):
    baseline = json.loads((folder / '00-baseline.json').read_text(encoding='utf-8-sig'))
    original = Image.open(folder / '00-baseline-scene.png').convert('RGB')
    rows = []
    for state_path in sorted(path for path in folder.glob('*.json') if re.match(r'^\d+-', path.name)):
        state = json.loads(state_path.read_text(encoding='utf-8-sig'))
        row = {'step': state['step'], 'stateChanges': {}}
        for key in ('renderer', 'displayGamma', 'viewMode', 'showFlags', 'components', 'postProcessVolumes', 'cameraPostProcess', 'levels', 'zone', 'camera', 'cameraRotation'):
            if baseline.get(key) != state.get(key):
                row['stateChanges'][key] = {'before': baseline.get(key), 'after': state.get(key)}
        row['sameCamera'] = all(baseline.get(key) == state.get(key) for key in ('camera', 'cameraRotation', 'zone'))
        image_path = state_path.with_name(state_path.stem + '-scene.png')
        if image_path.exists():
            current = Image.open(image_path).convert('RGB')
            if current.size != original.size:
                row['imageError'] = 'Viewport dimensions changed'
            else:
                # Scene captures omit Slate/editor chrome; fixed regions avoid the player.
                width, height = original.size
                regions = [(0, height // 4, width // 4, height * 3 // 4),
                           (width * 3 // 4, height // 4, width, height * 3 // 4)]
                row['regions'] = []
                for region in regions:
                    a, b = original.crop(region), current.crop(region)
                    row['regions'].append({'bounds': region, 'beforeMeanRgb': ImageStat.Stat(a).mean,
                                           'afterMeanRgb': ImageStat.Stat(b).mean,
                                           'meanAbsoluteDifference': ImageStat.Stat(ImageChops.difference(a, b)).mean})
        else:
            row['imageError'] = 'Missing screenshot'
        rows.append(row)
    return {'visualAcceptance': False, 'requiresVisualInspection': True, 'imageKind': 'scene', 'steps': rows}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    args = parser.parse_args()
    report = compare(args.folder)
    output = args.folder / 'comparison.json'
    output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'report': str(output), 'steps': [
        {'step': row['step'], 'changedState': list(row['stateChanges']), 'regions': row.get('regions'),
         'imageError': row.get('imageError')} for row in report['steps']]}))
