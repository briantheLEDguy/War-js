"""Place authored siege props and owned lighting; preserve every source asset.

This is an initial authoring pass, not equipped-roster or traversal approval.
The script refuses to overwrite existing objective assemblies.
"""
import json
import math
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts/unreal/siege"
TARGET = "/Game/Capitals/Siege/AegisCapital_Siege"
BASE = "/Game/WorldRebuild/Campaign_20260921_222411_608123/Meshes/"
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level(TARGET) or not levels.set_current_level_by_name("AegisCapital_Siege"):
    raise RuntimeError("An isolated siege map is required")
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
existing = list(actors.get_all_level_actors())
if any("WarSiegeObjectiveProp" in [str(t) for t in a.tags] for a in existing):
    raise RuntimeError("Objective assemblies already exist; preserve and review them")
battlefield = next(a for a in existing if isinstance(a, unreal.WarSiegeBattlefield))

def mesh(path):
    value = unreal.load_asset(path)
    if not isinstance(value, unreal.StaticMesh):
        raise RuntimeError("Required authored mesh missing: " + path)
    return value

crate = mesh("/Game/LicensedKits/Crownward/SM_Crate")
parts = {key: [mesh(BASE + key + "_" + str(i)) for i in range(count)] for key, count in
         [("frontier_siege_repair_bench_lod0",3), ("frontier_siege_ammunition_cradle_lod0",3),
          ("prop_riftspire_chain_winch",2), ("prop_riftspire_war_brazier",3)]}
created = []

def assembly(label, meshes, positions, gate=False):
    transforms = [unreal.Transform(location=unreal.Vector(*p)) for p in positions]
    actor = unreal.WarSiegeAuthoringLibrary.create_assembly(world, label, meshes, transforms, gate)
    if not actor:
        raise RuntimeError("Could not author " + label)
    created.append(label)
    return actor

def prop(label, key, position):
    return assembly(label, parts[key], [position] * len(parts[key]))

# Original-size authored supply crates form destructible blockades across the
# 6m openings. Individual crates are not stretched into a substitute gate mesh.
inventory = json.loads((ROOT / "artifacts/unreal/licensed-kits/capital-props-inventory.json").read_text())
metadata = next(m for m in inventory["meshes"] if m["path"].endswith("/SM_Crate.SM_Crate"))
ox,oy,oz = metadata["boundsOrigin"]
ex,ey,ez = metadata["boundsExtent"]
gates = []
for index,x in enumerate([14200,17300]):
    count = math.ceil(620 / (ey * 2))
    positions = [[x-ox, (column-(count-1)/2)*ey*2-oy, 4210+row*ez*2-(oz-ez)]
                 for row in range(math.ceil(320/(ez*2))) for column in range(count)]
    gates.append(assembly("Siege blockade " + str(index+1), [crate]*len(positions), positions, True))
mechanisms = [prop("Courtyard chain control " + str(i+1), "prop_riftspire_chain_winch", p)
              for i,p in enumerate([[15600,-1400,4210],[16400,1400,4210]])]
optional = [prop("Lower city ammunition reserve", "frontier_siege_ammunition_cradle_lod0", [-7900,3600,0]),
            prop("Courtyard reinforcement workshop", "frontier_siege_repair_bench_lod0", [16300,-2400,4210]),
            prop("Inner citadel rally brazier", "prop_riftspire_war_brazier", [18000,750,4210])]
optional[2].set_actor_scale3d(unreal.Vector(.5,.5,.5))
battlefield.set_editor_property("stage_gates", gates)
battlefield.set_editor_property("gate_mechanisms", mechanisms)
battlefield.set_editor_property("war_effort_props", optional)
spawns = list(battlefield.get_editor_property("team_spawns"))
spawns[4] = unreal.Vector(19800,2200,4220)
battlefield.set_editor_property("team_spawns", spawns)
battlefield.set_editor_property("traversal_reviewed", False)

sun = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0,0,20000), unreal.Rotator(pitch=-50,yaw=45))
sun.set_actor_label("Siege daylight")
sun.tags = ["WarSiegeLighting"]
sun.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
sun.light_component.set_editor_property("intensity", 30000.0)
sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0,0,18000))
sky.set_actor_label("Siege ambient sky")
sky.tags = ["WarSiegeLighting"]
sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
sky.light_component.set_editor_property("intensity", 1.0)
sky.light_component.set_editor_property("real_time_capture", True)
if not levels.save_current_level():
    raise RuntimeError("Cannot save siege objective props")
result = {"map":TARGET,"assemblies":created,"innerDefenderSpawn":[19800,2200,4220],
          "traversalReviewed":False,"equippedRosterReviewed":False,"nativePlayable":False}
(OUTPUT / "objectives.json").write_text(json.dumps(result,indent=2)+"\n")
unreal.log("WAR_SIEGE_OBJECTIVES " + json.dumps(result))
