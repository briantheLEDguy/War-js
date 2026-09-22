"""Select and save only an owned zone package, preserving authored detail layers."""
import datetime
import hashlib
import json
import shutil
from pathlib import Path
import unreal


class WorldLevelAccess:
    def __init__(self, root, receipt):
        self.root, self.receipt = root, receipt
        self.directory = root/'artifacts/unreal/world-portals'
        self.level = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        self.manifest = json.loads((self.directory/receipt['partitionManifest']).read_text()) if receipt.get('partitionManifest') else None
        self.zones = {row['id']:row for row in self.manifest['zones']} if self.manifest else {}
        self.backed_up = set()

    def package(self, zone):
        return self.zones[zone]['levels']['generated'] if self.manifest else self.receipt['layer']

    def file(self, package):
        if not package.startswith('/Game/WorldRebuild/'): raise RuntimeError('Refusing to edit an unowned level')
        return self.root/'unreal/AegisWar/Content'/(package.removeprefix('/Game/')+'.umap')

    def select(self, zone):
        package = self.package(zone)
        if package not in self.backed_up:
            file = self.file(package)
            expected = self.manifest['packageHashes'].get(package) if self.manifest else None
            if expected and hashlib.sha256(file.read_bytes()).hexdigest() != expected:
                raise RuntimeError('Zone changed since its last managed build; preserve and reconcile owner edits: '+zone)
            stamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            shutil.copy2(file, self.directory/(zone+'-before-edit-'+stamp+'.umap'))
            self.backed_up.add(package)
        if not self.level.set_current_level_by_name(package.rsplit('/',1)[1]):
            raise RuntimeError('Zone level unavailable: '+zone)

    def save(self, zones):
        for zone in sorted(zones):
            self.select(zone)
            if not self.level.save_current_level(): raise RuntimeError('Zone save failed: '+zone)
            if self.manifest:
                package = self.package(zone)
                self.manifest['packageHashes'][package] = hashlib.sha256(self.file(package).read_bytes()).hexdigest()
                self.refresh_bindings(zone)
                self.zones[zone]['acceptance']['traversal'] = 'pending'
                self.zones[zone]['acceptance']['visual'] = 'pending'
        if self.manifest and zones:
            self.manifest.pop('traversalEvidence', None)
            (self.directory/self.receipt['partitionManifest']).write_text(json.dumps(self.manifest, indent=2)+'\n')

    def refresh_bindings(self, zone):
        """Observe saved-level components; this inventory never grants visual acceptance."""
        if not self.manifest: return
        packages = set(self.zones[zone]['levels'].values())
        bindings, count = {}, 0
        for actor in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
            if actor.get_outer().get_path_name().split('.')[0] not in packages: continue
            if isinstance(actor, (unreal.WorldSettings, unreal.LevelScriptActor, unreal.Brush)): continue
            count += 1
            for component in actor.get_components_by_class(unreal.MeshComponent):
                mesh = component.static_mesh if isinstance(component,unreal.StaticMeshComponent) else (
                    component.get_skeletal_mesh_asset() if isinstance(component,unreal.SkeletalMeshComponent) else None)
                if not mesh: continue
                row = {'mesh':mesh.get_path_name(),
                    'materials':[component.get_material(i).get_path_name() if component.get_material(i) else None
                                 for i in range(component.get_num_materials())],
                    'collision':str(component.get_collision_profile_name())}
                bindings[json.dumps(row,sort_keys=True)] = row
        self.zones[zone]['actorCount'] = count
        self.zones[zone]['nativeAssetBindings'] = list(bindings.values())
