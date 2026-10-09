"""Read the installed Real_Landscape mesh inventory in private staging; no Blueprint execution or approval."""
import datetime,hashlib,json
from pathlib import Path
import unreal
ROOT=Path(__file__).resolve().parents[2];project=Path(unreal.Paths.project_dir()).resolve()
if project.name!='CityKitStaging':raise RuntimeError('Nature inspection requires isolated CityKitStaging')
folder=project/'Content/Medieval_Environment';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protected={p:sha(p) for p in folder.rglob('*') if p.suffix in ('.uasset','.umap','.uexp','.ubulk')}
registry=unreal.AssetRegistryHelpers.get_asset_registry();registry.search_all_assets(True)
tools=unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem) or unreal.new_object(unreal.StaticMeshEditorSubsystem)
rows=[]
try:
 for asset in registry.get_assets_by_path('/Game/Medieval_Environment/Real_Landscape',recursive=True):
  if str(asset.asset_class_path.asset_name)!='StaticMesh':continue
  mesh=asset.get_asset();bounds=mesh.get_bounds();body=mesh.get_editor_property('body_setup');package=str(asset.package_name)
  source=project/'Content'/(package.removeprefix('/Game/')+'.uasset')
  rows.append(dict(path=mesh.get_path_name(),sourceSha256=sha(source),boundsOrigin=[bounds.origin.x,bounds.origin.y,bounds.origin.z],boundsExtent=[bounds.box_extent.x,bounds.box_extent.y,bounds.box_extent.z],
    lodCount=mesh.get_num_lods(),lodVertices=[tools.get_number_verts(mesh,i) for i in range(mesh.get_num_lods())],lodScreenSizes=list(tools.get_lod_screen_sizes(mesh)),simpleCollisionCount=tools.get_simple_collision_count(mesh),
    collisionTraceFlag=str(body.get_editor_property('collision_trace_flag')) if body else None,materials=[slot.material_interface.get_path_name() if slot.material_interface else None for slot in mesh.get_editor_property('static_materials')]))
finally:
 for p,h in protected.items():
  if sha(p)!=h:raise RuntimeError('Preserve changed installed package: '+str(p))
 if set(protected)!=set(p for p in folder.rglob('*') if p.suffix in ('.uasset','.umap','.uexp','.ubulk')):raise RuntimeError('Installed nature inventory changed during inspection')
if not rows:raise RuntimeError('Installed nature inventory is empty')
output=ROOT/'artifacts/unreal/licensed-kits/nature-kit-inventory.json'
output.write_text(json.dumps(dict(createdUtc=datetime.datetime.now(datetime.timezone.utc).isoformat(),kit='/Game/Medieval_Environment/Real_Landscape',meshes=sorted(rows,key=lambda x:x['path']),sourcePackagesPreserved=len(protected),runtimeApproved=False,licenseReviewed=False,distributionApproved=False),indent=2)+'\n')
unreal.log('WAR_NATURE_KIT_INSPECTED='+str(len(rows)))
