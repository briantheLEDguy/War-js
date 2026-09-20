"""Rebuild, inspect saved geometry, render actual exports, and validate exact bytes."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
BLENDER = 'C:/Program Files/Blender Foundation/Blender 5.0/blender.exe'


def run(command, log):
    with (ROOT / 'review' / log).open('w', encoding='utf8') as output:
        subprocess.run(command, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, check=True)
    print('PASS', log, flush=True)


def blender(script, *args):
    return [BLENDER, '--background', '--threads', '2', '--python-exit-code', '1',
            '--python', str(ROOT / 'tools' / script), '--', *args]


run([sys.executable, str(ROOT / 'tools/make_textures.py')], 'textures.log')
run(blender('build_rack.py'), 'build.log')
run(blender('audit_masters.py'), 'masters.log')
run(blender('inspect_construction.py'), 'contacts.log')
run(blender('review_rack.py', '--lods', '0', '--views', 'neutral,rear,detail,joinery,gameplay'), 'views.log')
run(blender('review_rack.py', '--lods', '1,2', '--views', 'neutral,gameplay'), 'lod-views.log')
run([sys.executable, str(ROOT / 'tools/consolidate_build.py')], 'consolidate.log')
run(['node', str(ROOT / 'tools/validate_rack.mjs')], 'validate.log')
