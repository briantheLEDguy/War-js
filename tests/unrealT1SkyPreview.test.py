import sys,types,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_sky_preview import captured_sky

class SkyPreviewTests(unittest.TestCase):
 def fixture(self,enabled=True):
  events=[]
  class Sky:
   def __init__(self):self.enabled=enabled
   def get_component_by_class(self,kind):return self
   def get_editor_property(self,name):self_name=name;assert self_name=='real_time_capture';return self.enabled
   def set_real_time_capture(self,value):self.enabled=value;events.append(('capture',value))
  sky=Sky();actors=[sky]
  api=types.SimpleNamespace(SkyLight=Sky,SkyLightComponent=object,GameplayStatics=types.SimpleNamespace(get_all_actors_with_tag=lambda w,t:actors),WarImportLibrary=types.SimpleNamespace(prepare_world_preview_frame=lambda w:events.append('frame')),SystemLibrary=types.SimpleNamespace(execute_console_command=lambda w,c,p:events.append(c)))
  return api,sky,actors,events
 def test_update_order_and_original_mode_are_restored(self):
  for enabled in (True,False):
   api,sky,actors,events=self.fixture(enabled)
   with captured_sky('world',api) as update:
    update();update();self.assertFalse(sky.enabled)
   self.assertEqual(events[:4],[('capture',False),'frame','r.SkylightRecapture','frame']);self.assertEqual(events[-1],('capture',enabled));self.assertEqual(sky.enabled,enabled)
 def test_exception_restores_all_replaced_transient_rigs(self):
  api,first,actors,events=self.fixture();second=type(first)()
  with self.assertRaisesRegex(RuntimeError,'render failed'):
   with captured_sky('world',api) as update:
    update();actors[:]=[second];update();raise RuntimeError('render failed')
  self.assertTrue(first.enabled);self.assertTrue(second.enabled)
 def test_missing_or_ambiguous_rig_fails_without_mutation(self):
  for count in (0,2):
   api,sky,actors,events=self.fixture();actors[:]=[sky]*count
   with self.assertRaisesRegex(RuntimeError,'one local regional sky'):
    with captured_sky('world',api) as update:update()
   self.assertEqual(events,[]);self.assertTrue(sky.enabled)

if __name__=='__main__':unittest.main()
