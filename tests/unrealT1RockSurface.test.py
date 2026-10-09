import hashlib
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_rock_surface import rock_surface,rock_projection_weights,MODELS,geological_color


class RockSurfaceTest(unittest.TestCase):
    def test_surface_requires_exact_admitted_model_export_and_channels(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);base=root/'artifacts/unreal/t1-redesign';base.mkdir(parents=True)
            source=root/'public/assets/models'/MODELS['sunmeadow_march'];source.parent.mkdir(parents=True);source.write_bytes(b'admitted original')
            sha=lambda file:hashlib.sha256(file.read_bytes()).hexdigest()
            channels={}
            for key in ('color','normal'):
                texture=root/'public/assets/textures'/(key+'.png');texture.parent.mkdir(exist_ok=True);texture.write_bytes(key.encode())
                channels[key]=dict(path=texture.relative_to(root).as_posix(),sha256=sha(texture))
            geometry=base/(source.stem+'.json');geometry.write_text(json.dumps(dict(materials=[dict(textures=channels,color=[1,1,1,1],alphaMode='OPAQUE')])))
            (base/'models.json').write_text(json.dumps(dict(models={source.name:dict(file=geometry.name,sha256=sha(geometry),sourceSha256=sha(source))})))
            registry=source.parent/'asset-index.json';registry.write_text(json.dumps(dict(staticProps=dict(rock=dict(model=source.name,modelSha256=sha(source),approvalState='approved',runtimeReady=True)))))
            self.assertEqual(rock_surface(root,'sunmeadow_march')['color'],channels['color'])
            source.write_bytes(b'changed source')
            with self.assertRaises(ValueError):rock_surface(root,'sunmeadow_march')
            source.write_bytes(b'admitted original');geometry.write_text('{}')
            with self.assertRaises(ValueError):rock_surface(root,'sunmeadow_march')
        with self.assertRaises(ValueError):rock_surface(Path('.'),'other_region')

    def test_geological_color_softens_source_atlas_joints_and_stays_bounded(self):
        recipe=dict(geological=dict(baseColor=[.22,.235,.215],sourceMix=.14,macroMinimum=.72,macroMaximum=1.12,fineMinimum=.88))
        light=geological_color(recipe,[1,1,1],.5,.5);dark=geological_color(recipe,[0,0,0],.5,.5)
        self.assertLess(max(a-b for a,b in zip(light,dark)),.13)
        for i in range(101):
            c=geological_color(recipe,[.1,.2,.3],i/100,1-i/100)
            self.assertTrue(all(0<v<.4 for v in c))
        with self.assertRaises(ValueError):geological_color(recipe,[math.nan,0,0],0,0)
        with self.assertRaises(ValueError):geological_color(recipe,[0,0,0],2,0)

    def test_projection_has_continuous_normalized_weights_across_face_seams(self):
        self.assertEqual(rock_projection_weights([1,0,0]),[1,0,0])
        self.assertEqual(rock_projection_weights([0,0,1]),[0,0,1])
        self.assertEqual(rock_projection_weights([.5,-.5,0]),[.5,.5,0])
        a=rock_projection_weights([.5,.5,0]); b=rock_projection_weights([.500001,.499999,0])
        self.assertLess(math.dist(a,b),.00001)
        for bad in ([0,0,0],[math.nan,0,1],[2,0,1]):
            with self.assertRaises(ValueError):rock_projection_weights(bad)


if __name__=='__main__':unittest.main()
