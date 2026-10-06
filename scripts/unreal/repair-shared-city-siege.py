"""Reconcile the siege overlay with the active Dutch city, without granting admission."""
import hashlib
import json
import shutil
from pathlib import Path
import unreal

ROOT = Path(__file__).resolve().parents[2]
TARGET = '/Game/Capitals/Siege/AegisCapital_Siege'
FILE = ROOT/'unreal/AegisWar/Content/Capitals/Siege/AegisCapital_Siege.umap'
OUT = ROOT/'artifacts/unreal/shared-cities'
before = hashlib.sha256(FILE.read_bytes()).hexdigest()
backup = OUT/('siege-before-route-repair-' + before + '.umap')
OUT.mkdir(parents=True, exist_ok=True)
if not backup.exists():
    shutil.copy2(FILE, backup)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if not levels.load_level(TARGET):
    raise RuntimeError('Missing siege overlay')
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
unreal.GameplayStatics.flush_level_streaming(world)
fields = [a for a in actors.get_all_level_actors() if isinstance(a, unreal.WarSiegeBattlefield)]
if len(fields) != 1:
    raise RuntimeError('Expected one battlefield')
field = fields[0]
city = field.get_editor_property('city_definition')
if not city or city.get_editor_property('revision') != '6ffd751f94efa5aa261779a6853262a6ca5128376c7a65a369e69943de9f6a2f':
    raise RuntimeError('This overlay repair requires the surveyed shared Dutch city revision')
old = list(field.get_editor_property('equipment_spawns'))
if len(old) != 2 or any(abs(v.x-x) > 1 or v.y not in (0, -500) for v,x in zip(old, (-12900,-13750))):
    raise RuntimeError('Preserve an independently edited convoy staging area')
field.set_editor_property('equipment_spawns', [unreal.Vector(-12900,-500,10), unreal.Vector(-13750,-500,10)])
objectives = list(field.get_editor_property('objectives'))
if len(objectives) != 8 or objectives[2].x != 11900 or objectives[2].y not in (0, -400):
    raise RuntimeError('Preserve an independently edited ramp checkpoint')
objectives[2] = unreal.Vector(11900,-400,4000)
field.set_editor_property('objectives', objectives)
standards = field.get_editor_property('attacker_standards')
if len(standards) != 11 or 'WarSiegeEquipmentV1' not in [str(t) for t in standards[2].tags]:
    raise RuntimeError('Missing owned ramp checkpoint standard')
standards[2].set_actor_location(objectives[2]+unreal.Vector(0,430,0), False, True)
field.set_editor_property('lower_city_reviewed', False)
field.set_editor_property('traversal_reviewed', False)
field.set_editor_property('reviewed_city_revision', '')
if not levels.set_current_level_by_name('AegisCapital_Siege'):
    raise RuntimeError('Cannot select siege overlay')
if not unreal.WarSiegeAuthoringLibrary.build_navigation(world, unreal.Vector(3000,0,3500), unreal.Vector(25000,18000,6000)):
    raise RuntimeError('Navigation build failed')
if unreal.WarSiegeAuthoringLibrary.navigation_busy(world):
    raise RuntimeError('Navigation is still building')
if not levels.save_current_level():
    raise RuntimeError('Cannot save siege overlay')
(OUT/'siege-route-repair.json').write_text(json.dumps(dict(
    cityRevision=city.get_editor_property('revision'), backup=str(backup),
    beforeSha256=before, afterSha256=hashlib.sha256(FILE.read_bytes()).hexdigest(),
    equipmentSpawns=[[-12900,-500,10],[-13750,-500,10]], rampCheckpoint=[11900,-400,4000],
    admissionGranted=False), indent=2)+'\n')
unreal.log('WAR_SIEGE_ROUTE_REPAIR_SAVED; admission remains blocked')
