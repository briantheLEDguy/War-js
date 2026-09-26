"""Verify completed authoring passes are inert against the final saved packages."""
import hashlib
import json
from pathlib import Path
import runpy
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/unreal/capital-expansion'
CONTENT = ROOT / 'unreal/AegisWar/Content'
PASSES = (
    ('applied.json', 'apply-capital-expansion.py'),
    ('interior-revision.json', 'revise-capital-interiors.py'),
    ('replacements.json', 'apply-capital-replacements.py'),
    ('room-refits.json', 'apply-capital-room-refits.py'),
)


def fingerprint(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def main():
    # Require completion markers before invoking any mutating entry point.
    for marker, _ in PASSES:
        if not (OUT / marker).is_file():
            raise RuntimeError('Complete and verify the authoring pass first: ' + marker)
    receipt = json.loads((OUT / 'applied.json').read_text())
    files = [OUT / marker for marker, _ in PASSES]
    files += [OUT / 'plan.json', OUT / 'assets.json',
              ROOT / 'artifacts/unreal/world-portals/zone-manifest.json']
    for package, expected in receipt['packageHashes'].items():
        if not package.startswith('/Game/') or '..' in package:
            raise RuntimeError('Invalid capital package')
        file = CONTENT / (package.removeprefix('/Game/') + '.umap')
        if fingerprint(file) != expected:
            raise RuntimeError('Saved capital changed: ' + package)
        files.append(file)
    draft = ROOT / 'unreal/AegisWar/Saved/WorldEdit/crownward-draft.json'
    if draft.exists():
        files.append(draft)
    before = {str(file): fingerprint(file) for file in files}
    for _, script in PASSES:
        runpy.run_path(str(Path(__file__).with_name(script)), run_name='__main__')
        if before != {str(file): fingerprint(file) for file in files}:
            raise RuntimeError('Completed authoring pass changed files: ' + script)
    (OUT / 'repeatability.json').write_text(json.dumps({
        'passed': True, 'passes': [script for _, script in PASSES],
        'unchangedFiles': before,
    }, indent=2) + '\n')
    unreal.log('WAR_CAPITAL_EXPANSION_RERUN_PASSED')


main()
