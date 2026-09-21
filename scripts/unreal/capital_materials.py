"""Recompile legacy kit materials into private native copies, preserving sources."""
import hashlib
import json
from pathlib import Path

SOURCE = "/Game/Medieval_Mod_Town/Materials/M_Market_Stall_Cloth"
TARGET = "/Game/LicensedKits/Crownward/M_Market_Stall_Cloth"
MESH = "/Game/LicensedKits/Crownward/SM_Market_Stall_Cloth"


def package_file(root, package):
    return root / "unreal/AegisWar/Content" / (package.removeprefix("/Game/") + ".uasset")


def digest(file):
    return hashlib.sha256(file.read_bytes()).hexdigest()


def check_receipt(receipt, source_hash, target_hash):
    if (receipt.get("schemaVersion") != 1 or receipt.get("source") != SOURCE
            or receipt.get("target") != TARGET or receipt.get("sourceSha256") != source_hash
            or receipt.get("materialSha256") != target_hash):
        raise RuntimeError("Preserve changed material/source; reconcile the cloth adaptation receipt")


def cloth_material(root, unreal):
    if Path(unreal.Paths.project_dir()).resolve() != (root / "unreal/AegisWar").resolve():
        raise RuntimeError("Adapt materials only in the main AegisWar project")
    source_file, target_file = package_file(root, SOURCE), package_file(root, TARGET)
    source_hash = digest(source_file)
    receipt_path = root / "artifacts/unreal/licensed-kits/cloth-material-adaptation.json"
    if target_file.exists():
        if not receipt_path.exists():
            raise RuntimeError("Preserve existing cloth adaptation without a receipt")
        check_receipt(json.loads(receipt_path.read_text()), source_hash, digest(target_file))
        material = unreal.load_asset(TARGET)
    else:
        if receipt_path.exists():
            raise RuntimeError("Recorded cloth adaptation is missing; reconcile before recreating")
        material = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, TARGET)
        if not isinstance(material, unreal.Material):
            raise RuntimeError("Could not copy the authored cloth material")
        # Preserve the graph and subsurface shading; serialize fresh native shader state.
        unreal.MaterialEditingLibrary.recompile_material(material)
        if not unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False):
            raise RuntimeError("Could not save the recompiled cloth material")
        if digest(source_file) != source_hash:
            raise RuntimeError("Purchased material source changed during adaptation")
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt_path.write_text(json.dumps({"schemaVersion": 1, "source": SOURCE, "target": TARGET,
            "sourceSha256": source_hash, "materialSha256": digest(target_file),
            "unrealVersion": unreal.SystemLibrary.get_engine_version(), "visualApproved": False}, indent=2) + "\n")
    if not isinstance(material, unreal.Material):
        raise RuntimeError("Required cloth material is unavailable")
    return material


if __name__ == "__main__":
    import unreal
    root = Path(__file__).resolve().parents[2]
    mesh = unreal.load_asset(MESH)
    if not isinstance(mesh, unreal.StaticMesh):
        raise RuntimeError("The adapted city cloth mesh is missing")
    current = mesh.get_material(0)
    if not current or current.get_path_name().split(".")[0] not in {SOURCE, TARGET}:
        raise RuntimeError("Preserve the changed cloth mesh material")
    material = cloth_material(root, unreal)
    if current != material:
        mesh.set_material(0, material)
        if not unreal.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False):
            raise RuntimeError("Could not bind the adapted cloth material")
    (root / "artifacts/unreal/licensed-kits/cloth-material-binding.json").write_text(json.dumps({
        "mesh": mesh.get_path_name(), "material": mesh.get_material(0).get_path_name(),
        "meshSha256": digest(package_file(root, MESH)),
        "materialSha256": digest(package_file(root, TARGET)), "visualApproved": False}, indent=2) + "\n")
    unreal.log("WAR_CLOTH_ADAPTATION_READY=" + material.get_path_name())
