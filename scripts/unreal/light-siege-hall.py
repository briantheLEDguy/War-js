"""Add owned inner-hall brazier lighting without touching campaign packages."""
import json
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
TARGET = "/Game/Capitals/Siege/AegisCapital_Siege"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level(TARGET) or not levels.set_current_level_by_name("AegisCapital_Siege"):
    raise RuntimeError("Missing isolated siege map")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
owned = [a for a in actors.get_all_level_actors() if "WarSiegeHallLight" in [str(t) for t in a.tags]]
if owned and len(owned) != 8:
    raise RuntimeError("Incomplete hall lighting; inspect before authoring")
base = "/Game/WorldRebuild/Campaign_20260921_222411_608123/Meshes/prop_riftspire_war_brazier_"
meshes = [unreal.load_asset(base+str(i)) for i in range(3)]
if not all(isinstance(m, unreal.StaticMesh) for m in meshes):
    raise RuntimeError("Authored brazier meshes missing")
positions = [[x,y,4210] for x in [17800,19100] for y in [-600,600]]
for index,position in enumerate(positions):
    label = "Hall brazier " + str(index+1)
    transforms = [unreal.Transform(location=unreal.Vector(*position))] * len(meshes)
    prop = next((a for a in owned if a.get_actor_label() == label), None) if owned else unreal.WarSiegeAuthoringLibrary.create_assembly(world, label, meshes, transforms, False)
    if not prop:
        raise RuntimeError("Cannot create hall brazier")
    prop.tags = ["WarSiegeObjectiveProp", "WarSiegeHallLight"]
    # The source brazier is 4.16m tall; half scale clears the 3.1m hall ceiling.
    prop.set_actor_scale3d(unreal.Vector(.5,.5,.5))
    light_label = "Hall brazier glow " + str(index+1)
    light = next((a for a in owned if a.get_actor_label() == light_label), None) if owned else actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector())
    if not light:
        raise RuntimeError("Missing owned hall light")
    actual = prop.get_actor_location()
    light.set_actor_location(unreal.Vector(actual.x,actual.y,actual.z+220), False, True)
    light.set_actor_label(light_label)
    light.tags = ["WarSiegeHallLight"]
    component = light.point_light_component
    component.set_mobility(unreal.ComponentMobility.MOVABLE)
    component.set_editor_property("intensity", 7000.0)
    component.set_editor_property("attenuation_radius", 1800.0)
    component.set_editor_property("use_temperature", True)
    component.set_editor_property("temperature", 3200.0)
    component.set_editor_property("source_radius", 30.0)
for actor in actors.get_all_level_actors():
    if actor.get_actor_label() == "Inner citadel rally brazier" and "WarSiegeObjectiveProp" in [str(t) for t in actor.tags]:
        actor.set_actor_scale3d(unreal.Vector(.5,.5,.5))
if not levels.save_current_level():
    raise RuntimeError("Cannot save hall lighting")
(ROOT / "artifacts/unreal/siege/hall-lighting.json").write_text(json.dumps({"map":TARGET,"braziers":positions},indent=2)+"\n")
unreal.log("WAR_SIEGE_HALL_LIGHTING")
