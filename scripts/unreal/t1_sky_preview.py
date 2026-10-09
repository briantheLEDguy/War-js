"""Explicit offline sky updates; restore transient regional rigs and leave authored profiles intact."""
from contextlib import contextmanager


@contextmanager
def captured_sky(world,api):
    previous=[]
    def update():
        skies=[a.get_component_by_class(api.SkyLightComponent) for a in api.GameplayStatics.get_all_actors_with_tag(world,'WarLocalZoneEnvironment') if isinstance(a,api.SkyLight)]
        if len(skies)!=1 or skies[0] is None:raise RuntimeError('Offline preview requires one local regional sky')
        sky=skies[0]
        if not any(component==sky for component,_ in previous):previous.append((sky,sky.get_editor_property('real_time_capture')))
        sky.set_real_time_capture(False)
        api.WarImportLibrary.prepare_world_preview_frame(world)
        # SceneCapture views skip the engine real-time sky path; this command updates capture contents now.
        api.SystemLibrary.execute_console_command(world,'r.SkylightRecapture',None)
        api.WarImportLibrary.prepare_world_preview_frame(world)
    try:yield update
    finally:
        for sky,enabled in reversed(previous):sky.set_real_time_capture(enabled)
