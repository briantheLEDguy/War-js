"""Install only the recovered character DataAsset; leave the owner's capital map untouched."""
import importlib.util
from pathlib import Path
import unreal

source = Path(__file__).with_name("prepare-proof.py")
spec = importlib.util.spec_from_file_location("proof", source)
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)
proof.require(Path(unreal.Paths.project_dir()).resolve() == proof.imports.PROJECT.resolve(), "Wrong project")
visual = proof.visual("civic_battle_prelate_m", "empire", "battle_prelate", unreal.WarRealm.AEGIS)
proof.require(unreal.EditorAssetLibrary.save_loaded_asset(visual, only_if_is_dirty=False), "Recovered visual was not saved")
unreal.log("WAR_PRELATE_RECOVERED=" + visual.get_path_name())
