"""Read exact native cloud parameter values without editing any package."""
import datetime
import json
import os
import re
import sys
from pathlib import Path

import unreal

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from aegis_citadel_blueprint import OUT, sha
from aegis_citadel_lighting import REVIEWED_CLOUD_MATERIAL
from shared_city_sources import protected_source_file

revision = os.environ.get('WAR_CITADEL_INSPECT_REVISION', '')
if not re.fullmatch('[a-f0-9]{12}', revision):
    raise RuntimeError('Explicit private candidate revision required')
directory = OUT / revision
candidate = json.loads((directory / 'candidate.json').read_text())
if candidate['published'] or candidate['revision'] != revision:
    raise RuntimeError('Only an unpublished exact candidate may be inspected')
expected = {**candidate['sourceHashes'], **candidate['packageHashes']}
materials = [REVIEWED_CLOUD_MATERIAL]
for file in sorted(directory.glob('lighting-study-*/study.json')):
    study = json.loads(file.read_text())
    if study['historicalGeometryRevision'] != revision or not study['diagnosticOnly']:
        raise RuntimeError('Lighting study identity differs')
    for package, value in study['createdPackageHashes'].items():
        if package in expected and expected[package] != value:
            raise RuntimeError('Contradictory private package hash')
        expected[package] = value
        if package.endswith('/Materials/MI_Cloud'):
            materials.append(package)

def hashes():
    return {package: sha(protected_source_file(ROOT, package, value))
            for package, value in expected.items()}

if hashes() != expected:
    raise RuntimeError('Preserve independently changed native packages')
rows = []
library = unreal.MaterialEditingLibrary
for package in materials:
    material = unreal.load_asset(package)
    if not isinstance(material, unreal.MaterialInstanceConstant):
        raise RuntimeError('Expected exact native cloud material instance: ' + package)
    scalars = {str(name): library.get_material_instance_scalar_parameter_value(material, str(name))
               for name in library.get_scalar_parameter_names(material)}
    vectors = {}
    for name in library.get_vector_parameter_names(material):
        value = library.get_material_instance_vector_parameter_value(material, str(name))
        vectors[str(name)] = [value.r, value.g, value.b, value.a]
    rows.append(dict(package=package, object=material.get_path_name(), scalars=scalars, vectors=vectors))
if hashes() != expected:
    raise RuntimeError('Read-only cloud inspection changed package bytes')
report = dict(schemaVersion=1, diagnosticOnly=True, revision=revision,
              scriptSha256=sha(Path(__file__)), nativeMaterials=rows,
              protectedPackageHashes=expected, packagesUnchanged=True,
              visualApproved=False, runtimeVisibilityVerified=False)
file = directory / ('cloud-material-survey-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
file.write_text(json.dumps(report, indent=2) + '\n')
unreal.log('WAR_CITADEL_CLOUD_SURVEY=' + str(file))
