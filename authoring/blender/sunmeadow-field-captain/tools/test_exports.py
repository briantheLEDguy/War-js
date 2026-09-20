"""Current-byte gates for three captain exports and nine fitted runtime clips."""
import collections,hashlib,json,struct,unittest
from pathlib import Path
WORK=Path(__file__).resolve().parents[1];KEY='frontier_sunmeadow_empire_field_captain'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()

class CaptainExports(unittest.TestCase):
    def test_lowest_lod_retains_reviewed_boot_surfaces_and_weights(self):
        build=json.loads((WORK/'review'/f'{KEY}_build.json').read_text())
        retention=build['lods'][2]['bootRetention']
        self.assertEqual(retention['referenceMasterSha256'],sha(WORK/retention['referenceMaster']))
        self.assertEqual(retention['toolSha256'],sha(WORK/retention['tool']))
        parts=json.loads((WORK/'review/semantic-parts.json').read_text())['parts']
        ids={row['id'] for name,row in parts.items() if name.startswith('fitted_boot_')}
        self.assertEqual(set(retention['parts']),ids)
        def actual_triangles(lod):
            raw=(WORK/'runtime'/f'{KEY}_lod{lod}.glb').read_bytes()
            length=int.from_bytes(raw[12:16],'little');doc=json.loads(raw[20:20+length]);binary=raw[28+length:]
            def values(index):
                accessor=doc['accessors'][index];view=doc['bufferViews'][accessor['bufferView']]
                kind={5121:'B',5123:'H',5125:'I',5126:'f'}[accessor['componentType']]
                count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[accessor['type']]
                fmt='<'+kind*count;size=struct.calcsize(fmt);start=view.get('byteOffset',0)+accessor.get('byteOffset',0)
                return [struct.unpack_from(fmt,binary,start+i*view.get('byteStride',size)) for i in range(accessor['count'])]
            names=[doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']];result=collections.Counter();surface_edges=collections.Counter()
            for mesh in doc['meshes']:
                for primitive in mesh['primitives']:
                    a=primitive['attributes'];part=values(a['_CAPTAIN_PART']);position=values(a['POSITION'])
                    joints=values(a['JOINTS_0']);weights=values(a['WEIGHTS_0']);indices=values(primitive['indices'])
                    def vertex(i):
                        field=tuple(sorted((names[j],round(w,6)) for j,w in zip(joints[i],weights[i]) if w>1e-7))
                        return tuple(round(v,7) for v in position[i]),field
                    for start in range(0,len(indices),3):
                        triangle=[row[0] for row in indices[start:start+3]];identity=round(part[triangle[0]][0])
                        if identity not in ids:continue
                        self.assertEqual({round(part[i][0]) for i in triangle},{identity})
                        surface=[position[i] for i in triangle]
                        for a,b in zip(surface,surface[1:]+surface[:1]):
                            if a!=b:surface_edges[(identity,tuple(sorted((a,b))))]+=1
                        points=tuple(vertex(i) for i in triangle)
                        result[(identity,min(points,points[1:]+points[:1],points[2:]+points[:2]))]+=1
            self.assertGreater(len(surface_edges),1000)
            self.assertEqual(set(surface_edges.values()),{2},f'LOD{lod} boot shaft/sole must remain a closed two-manifold surface')
            return result
        actual_triangles(0)
        reference=actual_triangles(1);self.assertGreater(sum(reference.values()),1000)
        self.assertEqual(reference,actual_triangles(2),'LOD2 must retain actual LOD1 boot topology, winding and skinning')

    def test_shoulder_strips_follow_continuous_surface_routes(self):
        report=json.loads((WORK/'review/shoulder-routing.json').read_text())
        self.assertEqual(report['masterSha256'],sha(WORK/report['master']))
        self.assertEqual(len(report['strips']),2)
        for strip in report['strips']:
            self.assertLessEqual(strip['maximumRowStep'],.020,strip['object'])
            self.assertGreaterEqual(strip['minimumWidth'],.020,strip['object'])
            self.assertLessEqual(strip['maximumWidth'],.065,strip['object'])
            self.assertGreaterEqual(strip['minimumWidthDirectionDot'],.5,strip['object'])
            self.assertLessEqual(strip['maximumTurnDegrees'],80,strip['object'])

    def test_actual_current_export_views(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_review_final.json').read_text())
            self.assertEqual(report['modelSha256'],sha(WORK/'runtime'/f'{KEY}_lod{lod}.glb'))
            views={row['view'] for row in report['images']}
            self.assertTrue({'front','head','side','rear','run_side','death:2','gameplay'}<=views)
            for image in report['images']:
                self.assertEqual(image['sha256'],sha(WORK/image['image']))

    def test_actual_semantic_equipment_attachments(self):
        anchors=WORK/'review/equipment-attachment-source.json';parts=WORK/'review/semantic-parts.json'
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_equipment_attachment.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertEqual(report['sourceAttachmentSha256'],sha(anchors))
            self.assertEqual(report['semanticPartsSha256'],sha(parts))
            for name,digest in report['checkerSources'].items():self.assertEqual(digest,sha(WORK/'tools'/name))
            self.assertEqual(report['coverage']['vertices'],report['coverage']['referencedVertices'])
            self.assertEqual(report['coverage']['fractionalIds'],0)
            self.assertEqual(report['coverage']['mixedPartTriangles'],0)
            self.assertEqual(len(report['links']),31)
            bridge_seams={f'{part}_{end}_seam_edge_{edge}'
                          for part in ('captain_structural_shoulder_bridge','captain_structural_shoulder_bridge.001')
                          for end in ('front','rear') for edge in range(2)}
            self.assertTrue(bridge_seams<={link['id'] for link in report['links']})
            for link in report['links']:
                if link['id'] in bridge_seams:
                    self.assertEqual(link['support']['part'],'captain_fitted_brigandine')
            self.assertEqual(len(report['clips']),9)
            limits={link['id']:link['maximumGap'] for link in report['links']}
            self.assertTrue(all(0<limit<=.006 for limit in limits.values()))
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                for sample in clip['samples']:
                    self.assertEqual(set(sample['links']),set(limits))
                    for name,contact in sample['links'].items():
                        self.assertLessEqual(contact['subjectToSupport'],limits[name],f'{lod}/{clip["clip"]}/{sample["seconds"]}/{name}')
                        self.assertLessEqual(contact['supportToSubject'],limits[name],f'{lod}/{clip["clip"]}/{sample["seconds"]}/{name}')

    def test_retained_male_anatomical_baseline(self):
        provenance=json.loads((WORK/'foundation-provenance.json').read_text())
        for row in provenance['inputs']:
            retained=WORK.parents[2]/row['retained']
            self.assertEqual(sha(retained),row['sha256'])
            self.assertEqual(retained.stat().st_size,row['bytes'])
        report=json.loads((WORK/'review/male-foundation.json').read_text())
        self.assertEqual(report['foundationFamily'],'civic_humanoid_v2_m')
        self.assertEqual(report['bodyVariant'],'m')
        self.assertEqual(report['sha256'],sha(WORK/report['source']))
        self.assertEqual(report['quadSurface']['sha256'],sha(WORK/report['quadSurface']['path']))
        self.assertEqual(report['morphScale'],[1,1,1])
        self.assertGreater(report['vertices'],10000)

    def test_master_continuity(self):
        report=json.loads((WORK/'review/master-continuity.json').read_text())
        self.assertEqual(report['masterSha256'],sha(WORK/'sources'/f'{KEY}.blend'))
        self.assertEqual(len(report['shirtConnectedComponents']),1)
        self.assertEqual(report['shirtBoundaryLoops'],4)
        self.assertTrue(report['shirtBoundaryValenceValid'])
        self.assertTrue(report['fittedBrigandine'])
        self.assertEqual(report['caseSuspensionLoops'],4)
        self.assertEqual(report['shoulderLames'],3)
        self.assertGreaterEqual(report['packedImages'],15)

    def test_brigandine_armor_layers_and_suspended_equipment_clear_body(self):
        for lod in range(3):
            for kind in ('garment_clearance','layer_clearance','tool_clearance'):
                report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_{kind}.json').read_text())
                self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
                for name,digest in report['checkerSources'].items():self.assertEqual(digest,sha(WORK/'tools'/name))
                self.assertEqual(len(report['clips']),9)
                self.assertGreater(report['probeVertices'],100)
                self.assertEqual(report['underlyingBody']['sha256'],sha(WORK/report['underlyingBody']['path']))
                for topology in report['closedTopology'].values():
                    self.assertEqual(topology['boundaryEdges'],0);self.assertEqual(topology['nonManifoldEdges'],0)
                self.assertTrue(report['realCrossingDiagnostic']['insideParity'])
                self.assertFalse(report['realCrossingDiagnostic']['outsideParity'])
                self.assertTrue(report['realCrossingDiagnostic']['exactInsideParity'])
                self.assertFalse(report['realCrossingDiagnostic']['exactOutsideParity'])
                for clip in report['clips']:
                    self.assertGreater(len(clip['samples']),30)
                    for sample in clip['samples']:
                        self.assertEqual(sample['edgeCrossings'],0,f'{lod}/{kind}/{clip["clip"]}/{sample["seconds"]}')
                        self.assertGreaterEqual(sample['minimumSignedGap'],-.002,f'{lod}/{kind}/{clip["clip"]}/{sample["seconds"]}')

    def test_three_valid_current_exports_and_sources(self):
        build=json.loads((WORK/'review'/f'{KEY}_build.json').read_text())
        validation=json.loads((WORK/'review/draft-validation.json').read_text())
        self.assertTrue(validation['passed']);self.assertEqual(len(build['lods']),3)
        for row in build['lods']:
            self.assertEqual(sha(WORK/'runtime'/row['model']),row['sha256'])
            self.assertEqual(sha(WORK/row['master']),row['masterSha256'])
            self.assertEqual(set(row['clips']),{'idle','walk','run','combat_idle','attack_melee','attack_ranged','cast','death','jump'})
            result=next(r for r in validation['records'] if r['model']==row['model'])
            self.assertEqual(result['errors'],0);self.assertEqual(result['warnings'],0)
        for source in build['sourceFiles']:
            self.assertEqual(sha(WORK.parents[2]/source['path']),source['sha256'],source['path'])
        for source in build['validationSourceFiles']:
            self.assertEqual(sha(WORK.parents[2]/source['path']),source['sha256'],source['path'])

    def test_forearms_are_closed_full_volume(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'arm-volume-lod{lod}.json').read_text())
            self.assertEqual(report['sourceSha256'],sha(WORK/'runtime'/f'{KEY}_lod{lod}.glb'))
            self.assertGreaterEqual(report['sampleCount'],200)
            self.assertGreaterEqual(report['minimumAreaRatio'],.8);self.assertLessEqual(report['maximumAreaRatio'],1.2)
            self.assertLessEqual(report['largestAngularGapDegrees'],75)
            self.assertGreaterEqual(report['maleFoundation']['minimumReferenceSpanRatio'],.9)
            self.assertLessEqual(report['maleFoundation']['maximumReferenceSpanRatio'],1.1)

    def test_nine_clips_ground_contact_and_material_deformation(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_motion.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']));self.assertEqual(len(report['clips']),9)
            for clip in report['clips']:
                self.assertGreater(len(clip['samples']),30)
                self.assertGreaterEqual(clip['minimumHeight'],-.004,clip['clip'])
                for sample in clip['samples']:
                    for material,row in sample['materials'].items():
                        self.assertLess(row['p99'],2.2,f'{lod}/{clip["clip"]}/{material}')
                        self.assertLess(row['maximumEdgeExtensionMetres'],.06,f'{lod}/{clip["clip"]}/{material}')
                    if clip['clip'] in ('idle','combat_idle','attack_melee','attack_ranged','cast'):
                        for side,height in sample['soleHeights'].items():self.assertLessEqual(height,.012,f'{clip["clip"]}/{side}')
                    if clip['clip']=='death' and sample['seconds']>clip['samples'][-1]['seconds']-.1:
                        for side,height in sample['handHeights'].items():self.assertLessEqual(height,.012,f'death/{side}')
                        for side,height in sample['soleHeights'].items():self.assertLessEqual(height,.012,f'death/{side} sole')
                        self.assertLessEqual(sample['torsoSupportHeight'],.012,'death torso support')

    def test_run_has_bent_alternating_arms(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_motion.json').read_text())
            run=next(clip for clip in report['clips'] if clip['clip']=='run')
            for side in ('L','R'):
                self.assertGreater(min(sample['arms'][side]['elbowFlexDegrees'] for sample in run['samples']),25)
                values=[sample['arms'][side]['wristFromShoulder'][1] for sample in run['samples']]
                self.assertGreater(max(values)-min(values),.30)
            opposite=[sample['arms']['L']['wristFromShoulder'][1]-sample['arms']['R']['wristFromShoulder'][1] for sample in run['samples']]
            self.assertGreater(max(opposite),.30);self.assertLess(min(opposite),-.30)

    def test_trousers_remain_tucked(self):
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_boot_clearance.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']));self.assertEqual(len(report['clips']),9)
            for clip in report['clips']:
                for sample in clip['samples']:
                    for side,row in sample['sides'].items():
                        self.assertGreater(row['rays'],report['probeVertices'][side]*.60)
                        self.assertEqual(row['penetrations'],0,f'{lod}/{clip["clip"]}/{side}')
                        self.assertEqual(row['intersections'],0,f'{lod}/{clip["clip"]}/{side} hem crossing')

    def test_closed_welts_and_identical_lod_motion(self):
        fingerprints=None
        for lod in range(3):
            report=json.loads((WORK/'review'/f'{KEY}_lod{lod}_welt.json').read_text())
            self.assertEqual(report['sha256'],sha(WORK/'runtime'/report['model']))
            self.assertEqual(report['components'],2);self.assertEqual(report['nonManifoldEdges'],0)
            self.assertLessEqual(report['maximumRestDistance'],.0035)
            if fingerprints is None:fingerprints=report['animationChannelSha256']
            self.assertEqual(report['animationChannelSha256'],fingerprints)
            for clip in report['clips']:
                for sample in clip['samples']:self.assertLessEqual(sample['maximumPoseDistance'],.0035)

if __name__=='__main__':unittest.main()
