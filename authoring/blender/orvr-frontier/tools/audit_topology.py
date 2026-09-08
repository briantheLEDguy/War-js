"""Measure exported seam topology without treating assembled props as solids."""
from collections import Counter
import json
from repair_normal_projection import ROOT,digest,unpack
from repair_degenerate_tangents import accessor


def main():
    source=json.loads((ROOT/'source/frontier_collection.json').read_text()); assets=[]
    for asset_id in source['assets']:
        lods=[]
        for level in (0,1,2):
            payload=(ROOT/'runtime'/f'{asset_id}_lod{level}.glb').read_bytes(); document,binary=unpack(payload); meshes=[]
            instances=Counter(node['mesh'] for node in document['nodes'] if 'mesh' in node)
            for index,mesh in enumerate(document['meshes']):
                raw_edges=Counter(); welded_edges=Counter(); canonical={}; duplicates=0; triangle_keys=set()
                for primitive in mesh['primitives']:
                    positions,_=accessor(document,binary,primitive['attributes']['POSITION'])
                    indices,_=accessor(document,binary,primitive['indices'])
                    mapping=[]
                    for position in positions:
                        key=tuple(round(value,6) for value in position)
                        mapping.append(canonical.setdefault(key,len(canonical)))
                    for start in range(0,len(indices),3):
                        triangle=tuple(indices[start+offset][0] for offset in range(3)); welded=tuple(mapping[vertex] for vertex in triangle)
                        triangle_key=tuple(sorted(welded))
                        if triangle_key in triangle_keys: duplicates+=1
                        triangle_keys.add(triangle_key)
                        for face,edges in ((triangle,raw_edges),(welded,welded_edges)):
                            for a,b in zip(face,face[1:]+face[:1]):
                                if a!=b: edges[tuple(sorted((a,b)))]+=1
                meshes.append({'mesh':index,'instances':instances[index],'raw_boundary_edges':sum(count==1 for count in raw_edges.values()),
                               'position_welded_boundary_edges':sum(count==1 for count in welded_edges.values()),
                               'position_welded_multi_face_edges':sum(count>2 for count in welded_edges.values()),'coincident_triangles':duplicates})
            lods.append({'level':level,'glb_sha256':digest(payload),'meshes':meshes})
        assets.append({'asset_id':asset_id,'lods':lods})
    report={'method':'Edge incidence on actual GLB triangles; optional coincident-position welding at 1e-6 m; each unique mesh counted once.',
            'interpretation':'Raw boundary edges include split export UV/normal seams. Position welding removes those splits but can merge intentionally touching joinery shells. These props contain disconnected assembled surfaces and are not certified watertight solids. Repeated wheel instances deliberately share one mesh and atlas; this is not a test of arbitrary atlas-interior overlap.',
            'assets':assets,'visual_approval':False}
    (ROOT/'review/topology_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    for asset in assets:
        counts=[sum(mesh['position_welded_boundary_edges']+mesh['position_welded_multi_face_edges'] for mesh in lod['meshes']) for lod in asset['lods']]
        print(f"{asset['asset_id']}: position-welded boundary/multi-face edges LOD0/1/2 {counts}")


if __name__=='__main__': main()
