"""Root-run unsaved clone of the actual retained mountain; no actor edits or saves.

Creates only a fresh private, source-bound technical clone in memory. Complete
stored/face readbacks establish attribute preservation, not physical acceptance.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import uuid
import unreal

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from shared_city_sources import package_file
from aegis_citadel_terrain_readback import checked_committed_carve, native_terrain_policy

REVISION='b619391123d3'
RUN=ROOT/'artifacts/unreal/aegis-citadel'/REVISION
CLIP=RUN/'native-terrain-clip.json'
SOURCE='/Game/Capitals/crownward/Terrain_mountain.Terrain_mountain'
candidate=json.loads((RUN/'candidate.json').read_text())
blueprint=json.loads((RUN/'blueprint.json').read_text())
source_receipt=json.loads((RUN/'native-terrain-source-receipt.json').read_text())
wrapper=json.loads(CLIP.read_text())
source_file=RUN/'native-terrain-source.json'
source_payload=source_file.read_bytes().decode('utf-8')
nonce=uuid.uuid4().hex[:12]
COLLECTION='AegisCitadel_'+nonce
OUT=ROOT/'artifacts/unreal/citadel-reference/terrain-clone-preflight'/nonce
OUT.mkdir(parents=True,exist_ok=False)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def raw_sha(value):return hashlib.sha256(value.encode()).hexdigest()
def write(name,value,raw=False):
    path=OUT/name;path.write_text(value if raw else json.dumps(value,indent=2,allow_nan=False)+'\n')
    return dict(path=str(path.relative_to(ROOT)).replace('\\','/'),sha256=sha(path))
bound={}
for bindings in (blueprint['baseline']['packageHashes'],candidate['sourceHashes'],candidate['packageHashes'],candidate['city']['dependencyHashes']):
    for package,digest in bindings.items():
        if package in bound and bound[package]!=digest:
            raise RuntimeError('Original/candidate package hash binding is ambiguous: '+package)
        bound[package]=digest
def package_hashes():return {package:sha(package_file(ROOT,package)) for package in bound}
before=package_hashes()
if before!=bound or len(blueprint['baseline']['packageHashes'])!=1343:
    raise RuntimeError('The exact original1343/b619 native package bindings changed before clone preflight')
if (candidate.get('revision')!=REVISION or candidate.get('published') is not False
        or wrapper.get('sourceMesh')!=SOURCE or source_receipt.get('sourceMesh')!=SOURCE
        or source_receipt.get('sourceFile')!=source_file.relative_to(ROOT).as_posix()
        or sha(source_file)!=source_receipt['sourceSha256']
        or raw_sha(wrapper['sourceExportPayload'])!=wrapper['sourceExportSha256']
        or json.loads(wrapper['sourceExportPayload'])!=json.loads(source_payload)):
    raise RuntimeError('Actual b619 raw source/clip identity changed')
files=[CLIP,RUN/'candidate.json',RUN/'blueprint.json',RUN/'native-terrain-source-receipt.json',
       RUN/'native-terrain-source.json',Path(__file__),Path(__file__).with_name('aegis_citadel_terrain_readback.py'),
       Path(__file__).with_name('aegis_citadel_terrain_render_readback.py'),
       ROOT/'unreal/AegisWar/Source/AegisWarEditorTools/Private/WarImportLibrary.cpp',
       ROOT/'unreal/AegisWar/Source/AegisWarEditorTools/Public/WarImportLibrary.h',
       ROOT/'unreal/AegisWar/Binaries/Win64/UnrealEditor-AegisWarEditorTools.dll']
file_before={str(path.relative_to(ROOT)).replace('\\','/'):sha(path) for path in files}
report=dict(schemaVersion=1,preflightOnly=True,unsavedOnly=True,passed=False,published=False,
    nativeCollisionVerified=False,visualApproved=False,routeApproval=False,sourceMesh=SOURCE,
    collection=COLLECTION,clipSha256=sha(CLIP),sourceExportSha256=wrapper['sourceExportSha256'],
    packagesBefore=before,fileBindings=file_before,evidence={})
error=None
try:
    mesh=unreal.load_asset(SOURCE)
    if not mesh:raise RuntimeError('Exact actual retained native mountain is unavailable')
    tools=(unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
           or unreal.get_default_object(unreal.StaticMeshEditorSubsystem))
    original_raw=unreal.WarImportLibrary.describe_static_mesh_source_data(mesh,0)
    original_stored=unreal.WarImportLibrary.describe_static_mesh_stored_corners(mesh,0)
    original_render=unreal.WarImportLibrary.describe_static_mesh_render_data(mesh)
    original_faces=unreal.WarImportLibrary.describe_static_mesh_rendered_faces(mesh,0)
    original_policy=native_terrain_policy(mesh,tools)
    # The historical clip normalized Windows newlines. Bind both original file
    # bytes and clip payload bytes, then compare their complete parsed exports.
    if original_raw!=source_payload or json.loads(original_raw)!=json.loads(wrapper['sourceExportPayload']):
        raise RuntimeError('Actual committed original mountain differs from the measured raw native payload')
    dirty_before={package.get_path_name() for package in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    report['evidence']['originalSource']=write('original-source.json',original_raw,True)
    report['evidence']['originalStored']=write('original-stored.json',original_stored,True)
    report['evidence']['originalRender']=write('original-render.json',original_render,True)
    report['evidence']['originalRenderedFaces']=write('original-rendered-faces.json',original_faces,True)
    target=unreal.WarImportLibrary.create_carved_citadel_terrain(mesh,COLLECTION,CLIP.read_text())
    if not target:raise RuntimeError('Actual source-bound unsaved clone creation failed')
    target_path=target.get_path_name();report['targetMesh']=target_path
    raw=unreal.WarImportLibrary.describe_static_mesh_source_data(target,0)
    stored=unreal.WarImportLibrary.describe_static_mesh_stored_corners(target,0)
    render=unreal.WarImportLibrary.describe_static_mesh_render_data(target)
    faces=unreal.WarImportLibrary.describe_static_mesh_rendered_faces(target,0)
    report['evidence']['cloneSource']=write('clone-source.json',raw,True)
    report['evidence']['cloneStored']=write('clone-stored.json',stored,True)
    report['evidence']['cloneRender']=write('clone-render.json',render,True)
    report['evidence']['cloneRenderedFaces']=write('clone-rendered-faces.json',faces,True)
    report['comparison']=checked_committed_carve(wrapper,json.loads(raw),json.loads(stored),target_path,json.loads(original_stored))
    target_policy=native_terrain_policy(target,tools)
    report['policies']=dict(original=original_policy,clone=target_policy)
    if original_policy!=target_policy:
        raise RuntimeError('Actual source LOD/build/reduction/material or collision policy changed in the clone')
    actual_render=json.loads(render)
    if actual_render.get('available') is not True or len(actual_render.get('lods',[]))!=original_policy['sourceLods']:
        raise RuntimeError('All inherited LODs require actual built native render data')
    for index,lod in enumerate(actual_render['lods']):
        basis=lod.get('tangentBasis',{});vertices=lod.get('vertices',0)
        if (lod.get('cpuReadable') is not True or vertices<=0 or lod.get('indices',0)<=0
                or lod.get('invalidUVs')!=0 or basis.get('invalidVertices')!=0
                or basis.get('orthogonalVertices')!=vertices):
            raise RuntimeError('Actual native cloned render-buffer attributes failed at LOD'+str(index))
    # The retained mountain intentionally recomputes normals. Its genuine rendered
    # exterior, rather than its raw supplied normals, is the preservation baseline.
    from aegis_citadel_terrain_render_readback import checked_rendered_carve
    report['renderComparison']=checked_rendered_carve(wrapper,json.loads(original_faces),json.loads(faces),original_policy,target_path)
    if report['renderComparison'].get('nativeExteriorRenderPreserved') is not True:
        raise RuntimeError('Actual original rendered exterior shading/UVs are not preserved')
    if (unreal.WarImportLibrary.describe_static_mesh_source_data(mesh,0)!=original_raw
            or unreal.WarImportLibrary.describe_static_mesh_stored_corners(mesh,0)!=original_stored
            or unreal.WarImportLibrary.describe_static_mesh_render_data(mesh)!=original_render
            or unreal.WarImportLibrary.describe_static_mesh_rendered_faces(mesh,0)!=original_faces
            or native_terrain_policy(mesh,tools)!=original_policy):
        raise RuntimeError('Actual original committed/build/render data changed during cloning')
    dirty_after={package.get_path_name() for package in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if dirty_before.intersection(bound)!=dirty_after.intersection(bound):
        raise RuntimeError('Original/candidate native package dirty state changed')
    content=ROOT/'unreal/AegisWar/Content/WorldRebuild'/COLLECTION/'Meshes/SM_HallCarvedMountain.uasset'
    if content.exists():raise RuntimeError('Unsaved preflight unexpectedly wrote a Content package')
    report.update(passed=True,originalNativeCommittedUnchanged=True,originalNativeStoredUnchanged=True,
        originalNativeBuildPolicyUnchanged=True,originalNativeRenderUnchanged=True,
        originalNativePackageDirtyStateUnchanged=True,sourcePolicyRetained=True,noPackagesSaved=True)
except Exception as exc:
    error=exc;report['error']=str(exc)
finally:
    after=package_hashes();report['packagesAfter']=after
    unchanged=before==after and all(sha(ROOT/name)==digest for name,digest in file_before.items())
    report['sourceAndCandidateFilesUnchanged']=unchanged
    if not unchanged:
        report['passed']=False;error=RuntimeError('Original/candidate bound files changed during preflight');report['error']=str(error)
    write('report.json',report)
    unreal.log('WAR_CITADEL_TERRAIN_PREFLIGHT='+str(OUT/'report.json'))
if error:raise RuntimeError('Actual unsaved native terrain preflight failed: '+str(error))
