"""Blender: convert verified class-body GLBs without changing their fitting sources."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import bpy

sys.path.insert(0, str(Path(__file__).parent))
from class_character_native import ROOT, RUN, OUT, read, sha, selected_bodies

spec = importlib.util.spec_from_file_location('class_body_conversion', Path(__file__).with_name('convert-model.py'))
conversion = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conversion)


def main():
    checkpoint = read(RUN / 'checkpoint.json')
    requests = {row['identity']: read(RUN / row['identity'] / 'request.json') for row in checkpoint['characters']}
    playable = read(ROOT / 'unreal/AegisWar/Content/Migration/content.json')['careers']['playableProfiles']
    bodies = selected_bodies(checkpoint, requests, playable)
    OUT.mkdir(parents=True, exist_ok=True)
    inventory = ROOT / 'artifacts/unreal/animation-replacement/sources.json'
    shutil.copyfile(inventory, OUT / 'sources.json')
    manifest = dict(schemaVersion=1, runId='anatomy-v10', checkpointSha256=sha(RUN / 'checkpoint.json'),
                    artApproval=False, developmentOnly=True, profiles={})
    for profile, row in bodies.items():
        source = RUN / row['source']
        if sha(source) != row['sourceSha256']:
            raise RuntimeError('Changed verified body: ' + profile)
        receipt = read(source.parent / 'review.json')
        if not receipt['passed']:
            raise RuntimeError('Failed source review: ' + profile)
        for evidence in receipt['files']:
            if Path(evidence['path']).name != evidence['path'] or sha(source.parent / evidence['path']) != evidence['sha256']:
                raise RuntimeError('Changed source evidence: ' + profile)
        revision = 'classbody_' + row['identity'] + '_' + row['sourceSha256'][:12]
        folder = OUT / revision
        folder.mkdir(exist_ok=True)
        fbx = folder / (revision + '.fbx')
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.gltf(filepath=str(source), disable_bone_shape=True)
        before = conversion.scene_metrics()
        reference = conversion.evaluated_snapshot()
        if before['meshes'] != 3 or before['joints'] != 56 or before['actions']:
            raise RuntimeError('Unexpected native body source structure')
        bpy.ops.export_scene.fbx(filepath=str(fbx), object_types={'MESH', 'ARMATURE', 'EMPTY'},
            axis_forward='-Y', axis_up='Z', global_scale=1., apply_unit_scale=True,
            apply_scale_options='FBX_SCALE_NONE', add_leaf_bones=False,
            use_armature_deform_only=False, use_triangles=True, bake_anim=False, path_mode='AUTO')
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.import_scene.fbx(filepath=str(fbx), automatic_bone_orientation=False)
        after = conversion.scene_metrics()
        delta = conversion.compare_snapshots(reference, conversion.evaluated_snapshot())
        if (before['triangles'] != after['triangles'] or after['meshes'] != 3 or after['joints'] != 56
                or delta['jointPositionErrorMeters'] > .0001 or delta['meshBoundsErrorMeters'] > .0001):
            raise RuntimeError('Native FBX roundtrip changed body/rest rig: ' + profile)
        manifest['profiles'][revision] = dict(**{k:v for k,v in row.items() if k != 'source'},
            source=source.relative_to(ROOT).as_posix(), fbx=fbx.relative_to(ROOT).as_posix(),
            fbxSha256=sha(fbx), sourceReceiptSha256=sha(source.parent / 'review.json'),
            roundtrip=delta, animations=[])
        (OUT / 'model-sources.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
        print('WAR_CLASS_NATIVE_CONVERTED='+profile, flush=True)


if __name__ == '__main__':
    main()
