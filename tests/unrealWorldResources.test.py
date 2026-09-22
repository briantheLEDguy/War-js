import copy
import importlib.util
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bindings',ROOT/'scripts/unreal/world_resources.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)

class ResourceBindingsTest(unittest.TestCase):
    def setUp(self):
        self.source=json.loads((ROOT/'public/assets/maps/riftspire_capital.json').read_text())
        self.registry=json.loads((ROOT/'public/assets/models/asset-index.json').read_text())['staticProps']
    def test_original_eight_sites_and_floors(self):
        ready,pending=module.resource_bindings(self.source,self.registry)
        self.assertEqual(len(ready),8);self.assertEqual(pending,[])
        self.assertEqual({r['node']['kind'] for r in ready},{'ore','scrap','relic','soil'})
        self.assertTrue(any(r['node']['y']<0 for r in ready))
    def test_coordinate_or_identity_drift_rejected(self):
        source=copy.deepcopy(self.source);source['resourceNodes'][0]['x']+=1
        with self.assertRaises(ValueError):module.resource_bindings(source,self.registry)
        source=copy.deepcopy(self.source);source['resourceNodes'].append(source['resourceNodes'][0])
        with self.assertRaises(ValueError):module.resource_bindings(source,self.registry)
    def test_unapproved_or_replaced_model_rejected(self):
        registry=copy.deepcopy(self.registry);registry['riftspire_crate']['runtimeReady']=False
        with self.assertRaises(ValueError):module.resource_bindings(self.source,registry)
        registry=copy.deepcopy(self.registry);registry['riftspire_crate']['model']='other.glb'
        with self.assertRaises(ValueError):module.resource_bindings(self.source,registry)
    def test_unavailable_visuals_remain_pending(self):
        source=json.loads((ROOT/'public/assets/maps/sunmeadow_march.json').read_text())
        ready,pending=module.resource_bindings(source,self.registry)
        self.assertEqual(len(ready),2);self.assertEqual(len(pending),len(source['resourceNodes'])-2)
        self.assertTrue(all(row['node']['kind']=='herb' for row in ready))

    def test_review_never_admits_another_node_or_material_source(self):
        catalog=json.loads(module.CATALOG.read_text())
        bad=copy.deepcopy(catalog);bad['bindings'].append(bad['bindings'][0])
        with self.assertRaisesRegex(ValueError,'duplicate'):module.resource_bindings(self.source,self.registry,bad)
        source=copy.deepcopy(self.source);source['props'][next(i for i,p in enumerate(source['props']) if p['id']==source['resourceNodes'][0]['visualPropId'])]['heightMode']='terrain'
        with self.assertRaises(ValueError):module.resource_bindings(source,self.registry,catalog)
        bad=copy.deepcopy(catalog);bad['bindings'][0]['sourceSha256']='0'*64
        with self.assertRaises(ValueError):module.resource_bindings(self.source,self.registry,bad)

    def test_first_pair_uses_complete_reviewed_biome_plants(self):
        source=json.loads((ROOT/'public/assets/maps/cinderfen_outskirts.json').read_text())
        ready,pending=module.resource_bindings(source,self.registry)
        self.assertEqual(len(ready),4);self.assertEqual(len(pending),8)
        self.assertEqual({row['assetKey'] for row in ready},{'frontier_cinderfen_sedge_horsetail'})

    def test_catalog_append_preserves_previous_models_and_package_bytes(self):
        reviewed=json.loads(module.CATALOG.read_text())
        def binding(row):
            return {'purpose':'resource','zone':row['zone'],'entity':row['entity'],'visualProp':row['visualProp'],
                    'sourceModel':row['model'],'sourceSha256':row['sourceSha256'],'mesh':'/Game/Reviewed.Mesh'}
        before={'schemaVersion':1,'productionAccepted':False,'sourceContentSha256':'1'*64,
                'bindings':[binding(reviewed['bindings'][0])],'packageHashes':{'/Game/Reviewed':'2'*64}}
        after=copy.deepcopy(before);after['bindings'].append(binding(reviewed['bindings'][-1]))
        module.validate_catalog_append(before,after,reviewed)
        for mutate in [lambda d:d['bindings'][0].update(mesh='/Game/Changed.Mesh'),
                       lambda d:d['packageHashes'].update({'/Game/Reviewed':'3'*64}),
                       lambda d:d['bindings'][-1].update(entity='unreviewed'),
                       lambda d:d['bindings'].pop(0),
                       lambda d:d.update(sourceContentSha256='4'*64)]:
            invalid=copy.deepcopy(after);mutate(invalid)
            with self.assertRaises(ValueError):module.validate_catalog_append(before,invalid,reviewed)

if __name__=='__main__':unittest.main()
