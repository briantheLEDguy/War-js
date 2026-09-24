import unittest
from strip_character_tracks import decode, encode, preservation_signature, strip


class TrackRemoval(unittest.TestCase):
    def model(self):
        return dict(asset={'version':'2.0'}, buffers=[{'byteLength':48}],
            bufferViews=[dict(buffer=0,byteOffset=i*12,byteLength=12) for i in range(4)],
            accessors=[dict(bufferView=i,componentType=5126,count=1,type='VEC3') for i in range(4)],
            meshes=[dict(primitives=[dict(attributes={'POSITION':0,'WEIGHTS_0':1})])],
            skins=[dict(joints=[0],inverseBindMatrices=1)],nodes=[dict(name='hips',translation=[0,1,0])],
            materials=[dict(name='OriginalSteel',pbrMetallicRoughness={'metallicFactor':.8})],
            animations=[dict(name='retired',samplers=[dict(input=2,output=3)],channels=[])])

    def test_removes_binary_tracks_preserves_geometry_skin_and_rest(self):
        document=self.model(); binary=bytes(range(48)); source=encode(document,binary)
        output,receipt=strip(source); result,payload=decode(output)
        self.assertNotIn('animations',result)
        self.assertEqual(len(result['accessors']),2)
        self.assertEqual(payload,binary[:24])
        self.assertEqual(preservation_signature(document,binary),preservation_signature(result,payload))
        self.assertEqual(receipt['removedBufferViews'],2)
        self.assertEqual(strip(output),(output,None))

    def test_mechanical_animation_is_untouched(self):
        document=self.model(); document.pop('skins')
        source=encode(document,bytes(range(48)))
        self.assertEqual(strip(source),(source,None))

    def test_shared_accessor_keeps_mesh_payload(self):
        document=self.model(); document['animations'][0]['samplers'][0]['output']=0
        result,receipt=strip(encode(document,bytes(range(48))))
        output,_=decode(result)
        self.assertEqual(output['meshes'][0]['primitives'][0]['attributes']['POSITION'],0)
        self.assertEqual(receipt['removedAccessors'],1)

    def test_partial_interleaving_fails_without_losing_mesh_bytes(self):
        document=self.model(); document['accessors'][3]['bufferView']=0
        with self.assertRaisesRegex(ValueError,'shares a geometry buffer view'):
            strip(encode(document,bytes(range(48))))

    def test_unknown_geometry_extension_is_not_silently_rewritten(self):
        document=self.model(); document['meshes'][0]['primitives'][0]['extensions']={'UNKNOWN':{}}
        with self.assertRaisesRegex(ValueError,'explicit preservation support'):
            strip(encode(document,bytes(range(48))))


if __name__=='__main__': unittest.main()
