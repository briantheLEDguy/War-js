"""Inspect named load paths in saved editable geometry before batching hides part IDs."""
import json,sys
from pathlib import Path
import bpy
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build_rack import KEY,sha,save

records=[]
for lod in(0,1,2):
    build=json.loads((ROOT/'review'/f'{KEY}_lod{lod}_build.json').read_text())
    master=ROOT/build['sourceMaster'];bpy.ops.wm.open_mainfile(filepath=str(master))
    objects={o.name:o for o in bpy.context.scene.objects if o.type=='MESH' and not o.hide_render}
    trees={}
    for name,obj in objects.items():
        obj.data.calc_loop_triangles()
        trees[name]=BVHTree.FromPolygons([v.co for v in obj.data.vertices],[t.vertices for t in obj.data.loop_triangles],all_triangles=True)
    contacts=[]
    def probes(obj):
        return [v.co for v in obj.data.vertices]+[(obj.data.vertices[e.vertices[0]].co+obj.data.vertices[e.vertices[1]].co)/2 for e in obj.data.edges]
    def contact(part,support,tolerance=.003):
        a,b=objects[part],objects[support]
        minimum=min([trees[support].find_nearest(point)[3] for point in probes(a)]+
                    [trees[part].find_nearest(point)[3] for point in probes(b)])
        crossings=len(trees[part].overlap(trees[support]))
        passed=bool(crossings) or minimum<=tolerance
        contacts.append({'part':part,'support':support,'minimumSurfaceGapM':minimum,
          'surfaceTriangleContacts':crossings,'toleranceM':tolerance,'passed':passed})
    for joint in build['joints']:
        contact(joint['part'],joint['support'],.003)
    record={'level':lod,'sourceMasterSha256':sha(master),'modelSha256':sha(ROOT/'runtime'/build['model']),
            'contacts':contacts,'passed':all(c['passed'] for c in contacts)}
    records.append(record)
report={'passed':all(r['passed'] for r in records),'toolSha256':sha(Path(__file__)),'records':records}
save(ROOT/'review/construction-contacts.json',report)
if not report['passed']:
    raise RuntimeError('Disconnected fittings: '+json.dumps([c for r in records for c in r['contacts'] if not c['passed']]))
print('RACK_CONNECTIONS_VERIFIED',sum(len(r['contacts']) for r in records),flush=True)
