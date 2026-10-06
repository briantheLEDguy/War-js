"""Portable source-plan boundary tests; synthetic bytes never approve native content."""
import hashlib
import ast
import json
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
import shared_city_sources as sources


class EngineCitySourcesTests(unittest.TestCase):
    def dependency_collector(self, root, graph, files):
        tree=ast.parse((Path(__file__).resolve().parents[1]/'scripts/unreal/shared_city_authoring.py').read_text())
        function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='dependencies')
        calls=[]
        def resolve_game(base,package):
            if not package.startswith('/Game/'):raise ValueError('Engine package cannot be owned')
            return files[package]
        def resolve_protected(base,package,expected):
            self.assertEqual(package,sources.REVIEWED_ENGINE_SOURCE)
            calls.append((package,expected));return files[package]
        scope=dict(ROOT=root,unreal=SimpleNamespace(AssetRegistryDependencyOptions=lambda **kw:kw),
            registry=SimpleNamespace(get_dependencies=lambda package,options:graph.get(package,[]),
                scan_paths_synchronous=lambda paths,force:None),
            package_file=resolve_game,protected_source_file=resolve_protected,
            REVIEWED_ENGINE_SOURCE=sources.REVIEWED_ENGINE_SOURCE,digest=sources.digest)
        exec(compile(ast.Module(body=[function],type_ignores=[]),'city-dependency-collector','exec'),scope)
        return scope['dependencies'],calls

    def test_dependency_collection_keeps_the_signed_engine_parent_in_the_city_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);model=root/'Model.uasset';cloud=root/'Cloud.uasset'
            model.write_bytes(b'game model');cloud.write_bytes(b'read-only reviewed engine input')
            graph={'/Game/Scenery':['/Game/Model'],
                   '/Game/Model':[sources.REVIEWED_ENGINE_SOURCE,'/Engine/Unreviewed']}
            collect,calls=self.dependency_collector(root,graph,{'/Game/Scenery':model,'/Game/Model':model,sources.REVIEWED_ENGINE_SOURCE:cloud})
            expected=sources.digest(cloud)
            result=collect(['/Game/Scenery'],{sources.REVIEWED_ENGINE_SOURCE:expected})
            self.assertEqual(result,{'/Game/Model':sources.digest(model),sources.REVIEWED_ENGINE_SOURCE:expected})
            self.assertEqual(calls,[(sources.REVIEWED_ENGINE_SOURCE,expected)])
            self.assertNotIn('/Engine/Unreviewed',result)
            with self.assertRaisesRegex(RuntimeError,'signed protected source hash'):collect(['/Game/Scenery'])
            cloud.write_bytes(b'changed engine input')
            with self.assertRaisesRegex(RuntimeError,'changed during'):collect(['/Game/Scenery'],{sources.REVIEWED_ENGINE_SOURCE:expected})

    def test_newly_saved_dependency_rows_are_refreshed_before_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);model=root/'Model.uasset';cloud=root/'Cloud.uasset'
            model.write_bytes(b'game model');cloud.write_bytes(b'read-only engine input')
            graph={};calls=[]
            collect,_=self.dependency_collector(root,graph,{'/Game/Scene/World':model,
                '/Game/Materials/Cloud':model,sources.REVIEWED_ENGINE_SOURCE:cloud})
            def scan(paths,force):
                calls.append((paths,force))
                if paths==['/Game/Scene']:graph['/Game/Scene/World']=['/Game/Materials/Cloud']
                if paths==['/Game/Materials']:graph['/Game/Materials/Cloud']=[sources.REVIEWED_ENGINE_SOURCE]
            collect.__globals__['registry'].scan_paths_synchronous=scan
            expected=sources.digest(cloud)
            result=collect(['/Game/Scene/World'],{sources.REVIEWED_ENGINE_SOURCE:expected})
            self.assertEqual(result[sources.REVIEWED_ENGINE_SOURCE],expected)
            self.assertEqual(calls,[(['/Game/Scene'],True),(['/Game/Materials'],True)])

    def fixture(self,root):
        engine=root/'portable-engine'
        def package(name):
            content=engine/'Engine/Content' if name.startswith('/Engine/') else root/'unreal/AegisWar/Content'
            file=content/(name.split('/',2)[2]+'.uasset');file.parent.mkdir(parents=True,exist_ok=True)
            file.write_bytes(('PORTABLE PACKAGE ONLY '+name).encode())
            return hashlib.sha256(file.read_bytes()).hexdigest()
        cities=[];zones=[]
        for identity in sources.CITIES:
            definition='/Game/'+identity+'/City';scene='/Game/'+identity+'/Scenery';game='/Game/'+identity+'/Gameplay'
            dependencies={'/Game/'+identity+'/Model':package('/Game/'+identity+'/Model')}
            cities.append(dict(id=identity,definition=definition,revision='fixture',origin=[0,0,0],
                sceneryLevels=[scene],gameplayLevels=[game],packageHashes={p:package(p) for p in (definition,scene,game)},dependencyHashes=dependencies))
            zones.append(dict(id=identity,cityDefinition=definition,cityRevision='fixture',origin=[0,0,0],levels=dict(scene=scene,game=game)))
        cities[0]['dependencyHashes'][sources.REVIEWED_ENGINE_SOURCE]=package(sources.REVIEWED_ENGINE_SOURCE)
        build=dict(map='/Game/Campaign',layer='/Game/Routing')
        receipt=dict(schemaVersion=1,campaignMap=build['map'],cities=cities,campaignHashes={p:package(p) for p in build.values()})
        file=root/sources.RECEIPT;file.parent.mkdir(parents=True);file.write_text(json.dumps(receipt))
        return engine,receipt,file,build,dict(zones=zones)

    def test_source_plan_resolves_exact_engine_input_and_detects_byte_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);engine,receipt,file,build,manifest=self.fixture(root)
            with mock.patch.object(sources,'routing',return_value=(build,manifest,None)):
                self.assertEqual(len(sources.source_plan(root,engine)['cities']),2)
                parent=engine/'Engine/Content'/(sources.REVIEWED_ENGINE_SOURCE[8:]+'.uasset')
                parent.write_bytes(b'TAMPERED PORTABLE PARENT')
                with self.assertRaisesRegex(ValueError,'Changed native city source'):sources.source_plan(root,engine)

    def test_source_plan_never_treats_engine_as_owned_or_accepts_unknown_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);engine,receipt,file,build,manifest=self.fixture(root)
            with mock.patch.object(sources,'routing',return_value=(build,manifest,None)):
                hashes=receipt['cities'][0]['dependencyHashes'];sha=hashes.pop(sources.REVIEWED_ENGINE_SOURCE)
                hashes['/Engine/Other']=sha;file.write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError,'Unreviewed'):sources.source_plan(root,engine)
                del hashes['/Engine/Other'];hashes[sources.REVIEWED_ENGINE_SOURCE]=sha
                receipt['cities'][0]['packageHashes'][sources.REVIEWED_ENGINE_SOURCE]=sha;file.write_text(json.dumps(receipt))
                with self.assertRaisesRegex(ValueError,'Invalid city package'):sources.source_plan(root,engine)


if __name__=='__main__':unittest.main()
