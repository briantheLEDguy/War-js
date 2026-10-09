import copy,math,struct,sys,unittest,zlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_forest_floor import forest_floor_mask,mask_png

class ForestFloorTests(unittest.TestCase):
 def fixture(self):return dict(minX=-40,maxX=40,minZ=-20,maxZ=20),[dict(x=-10,z=5,radius=9)]
 def test_rectangular_projection_places_the_mask_at_its_world_canopy(self):
  b,t=self.fixture();m=forest_floor_mask(b,t,128)
  def at(x,z):return m[int((b['maxZ']-z)/40*128)*128+int((x+40)/80*128)]
  self.assertEqual(at(-10,5),255);self.assertEqual(at(10,-5),0);self.assertEqual(at(-35,15),0)
  self.assertTrue(any(0<v<255 for v in m))
 def test_union_is_deterministic_order_independent_and_preserves_inputs(self):
  b,t=self.fixture();t.append(dict(x=-3,z=5,radius=8));before=copy.deepcopy((b,t));m=forest_floor_mask(b,t,128)
  self.assertEqual(m,forest_floor_mask(b,list(reversed(t)),128));self.assertEqual((b,t),before)
  first=forest_floor_mask(b,t[:1],128);second=forest_floor_mask(b,t[1:],128)
  self.assertEqual(m,bytes(max(a,c) for a,c in zip(first,second)))
 def test_png_roundtrip_and_byte_extent(self):
  b,t=self.fixture();m=forest_floor_mask(b,t,32);png=mask_png(m,32);self.assertTrue(png.startswith(b'\x89PNG\r\n\x1a\n'))
  offset=8;data=b''
  while offset<len(png):
   length=struct.unpack('>I',png[offset:offset+4])[0];kind=png[offset+4:offset+8];payload=png[offset+8:offset+8+length]
   self.assertEqual(struct.unpack('>I',png[offset+8+length:offset+12+length])[0],zlib.crc32(kind+payload)&0xffffffff)
   if kind==b'IDAT':data+=payload
   offset+=length+12
  raw=zlib.decompress(data);self.assertEqual(b''.join(raw[i*33+1:(i+1)*33] for i in range(32)),m)
  with self.assertRaises(ValueError):mask_png(m,31)
 def test_nonfinite_unbounded_and_empty_inputs_fail(self):
  b,t=self.fixture()
  for bb,tt,size in [({**b,'maxX':-50},t,32),(b,[],32),(b,t,2048),(b,[dict(x=math.inf,z=0,radius=5)],32),(b,[dict(x=0,z=0,radius=101)],32)]:
   with self.assertRaises(ValueError):forest_floor_mask(bb,tt,size)

if __name__=='__main__':unittest.main()
