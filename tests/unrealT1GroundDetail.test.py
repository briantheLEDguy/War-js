import copy,json,math,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_ground_detail import modulate_surface


def fixture():
    base=dict(bounds=dict(minX=-40,maxX=40,minZ=-30,maxZ=30),segmentsX=8,segmentsZ=6,samples=[10]*63,edgeFade=10)
    detail=dict(bounds=dict(minX=-1,maxX=1,minZ=-1,maxZ=1),segmentsX=2,segmentsZ=2,samples=[0,.5,1]*3)
    layer=dict(id='fold',wavelengthMetres=40,amplitudeMetres=2,angleRadians=0,offsetX=0,offsetZ=0)
    return base,detail,[layer]


class GroundDetailTest(unittest.TestCase):
    def test_known_ramp_orientation_and_immutable_rectangular_seams(self):
        base,detail,layers=fixture();original=copy.deepcopy((base,detail,layers));result,proof=modulate_surface(base,detail,layers)
        self.assertEqual(result['samples'][3*9+4],9)
        self.assertEqual(result['samples'][3*9+6],10)
        for z in range(7):
            for x in range(9):
                if x in (0,8) or z in (0,6):self.assertEqual(result['samples'][z*9+x],base['samples'][z*9+x])
        self.assertEqual((base,detail,layers),original);self.assertEqual(result['bounds'],base['bounds'])
        layers[0]['angleRadians']=math.pi/2;rotated,_=modulate_surface(base,detail,layers)
        self.assertAlmostEqual(rotated['samples'][5*9+4],10);self.assertAlmostEqual(rotated['samples'][3*9+6],9)
        self.assertLessEqual(proof['maximumDeltaMetres'],2);self.assertTrue(proof['requiresRouteGrading']);self.assertFalse(proof['nativeIntegrated'])


    def test_buffered_raster_preserves_unaligned_native_boundary_and_neighbor_rows(self):
        base,detail,layers=fixture();base.update(segmentsX=16,segmentsZ=12,samples=[10]*221)
        bounds=dict(minX=-28,maxX=29,minZ=-18,maxZ=19);result,proof=modulate_surface(base,detail,layers,bounds)
        def sample(x,z):
            fx,fz=(x+40)/5,(z+30)/5;ix,iz=min(15,int(fx)),min(11,int(fz));u,v=fx-ix,fz-iz
            at=lambda dx,dz:result['samples'][(iz+dz)*17+ix+dx]
            return (at(0,0)*(1-u)+at(1,0)*u)*(1-v)+(at(0,1)*(1-u)+at(1,1)*u)*v
        for i in range(21):
            x=bounds['minX']+(bounds['maxX']-bounds['minX'])*i/20;z=bounds['minZ']+(bounds['maxZ']-bounds['minZ'])*i/20
            for offset in (0,4):
                for px,pz in [(x,bounds['minZ']+offset),(x,bounds['maxZ']-offset),(bounds['minX']+offset,z),(bounds['maxX']-offset,z)]:self.assertAlmostEqual(sample(px,pz),10,places=12)
        self.assertLess(sample(0,0),10);self.assertEqual(proof['protectedSamplingBorderMetres'],10)
        with self.assertRaises(ValueError):modulate_surface(base,detail,layers,{**bounds,'maxX':41})

    def test_reflected_source_is_continuous_across_tile_boundaries(self):
        base,detail,layers=fixture();layers[0]['offsetX']=40
        middle,_=modulate_surface(base,detail,layers);layers[0]['offsetX']=40-1e-5
        left,_=modulate_surface(base,detail,layers);layers[0]['offsetX']=40+1e-5
        right,_=modulate_surface(base,detail,layers);i=3*9+4
        self.assertLess(abs(left['samples'][i]-right['samples'][i]),1e-12)
        self.assertLess(abs(middle['samples'][i]-left['samples'][i]),1e-6)

    def test_rejects_aliasing_excessive_amplitude_and_bad_sampling(self):
        for update in [dict(wavelengthMetres=39),dict(amplitudeMetres=5),dict(offsetX=math.nan),dict(angleRadians=True)]:
            base,detail,layers=fixture();layers[0].update(update)
            with self.assertRaises(ValueError):modulate_surface(base,detail,layers)
        base,detail,layers=fixture();layers.append({**layers[0],'id':'second','amplitudeMetres':3})
        with self.assertRaises(ValueError):modulate_surface(base,detail,layers)
        for update in [dict(samples=[0]),dict(segmentsX=True),dict(samples=[math.nan]*9),dict(samples=[1]*9)]:
            base,detail,layers=fixture();detail.update(update)
            with self.assertRaises(ValueError):modulate_surface(base,detail,layers)

    def test_rejects_out_of_range_heights_and_preserves_zero_strength_exactly(self):
        base,detail,layers=fixture();base['samples']=[-100]*63
        with self.assertRaises(ValueError):modulate_surface(base,detail,layers)
        base,detail,layers=fixture();layers[0]['amplitudeMetres']=0;result,proof=modulate_surface(base,detail,layers)
        self.assertEqual(result,base);self.assertEqual(json.dumps(result),json.dumps(base));self.assertEqual(proof['changedVertices'],0)


if __name__=='__main__':unittest.main()
