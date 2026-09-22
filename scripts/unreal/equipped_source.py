"""Verified native assembly sources; browser body-only registrations stay intact."""
import hashlib
import json

PROFILE = "civic_battle_prelate_m"
SLOTS = ("body", "head", "shoulders", "chest", "hands", "waist", "legs", "feet", "back", "tabard", "weapon")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module_name(slot):
    stem = "chr_civic_battle_prelate_t1_m" if slot == "body" else "wep_civic_battle_prelate_dawn_maul" if slot == "weapon" else f"arm_civic_battle_prelate_{slot}_t1_m"
    return stem + ".glb"


def module_sources(root, registry):
    records = list(registry["characterProfiles"].values())
    for equipment in registry["equipment"].values():
        records.extend(equipment.get("variants", {"default": equipment}).values())
    result = []
    for slot in SLOTS:
        name = module_name(slot)
        candidates = [record for record in records if record.get("model") == name
                      and record.get("bodyVariant") == "m"]
        if len(candidates) != 1:
            raise ValueError(f"Expected one registered male Prelate module: {name}")
        record = candidates[0]
        source = root / "public/assets/models" / name
        if record.get("approvalState") != "approved" or not record.get("runtimeReady") or digest(source) != record.get("modelSha256"):
            raise ValueError(f"Unverified Prelate module: {name}")
        result.append({"slot": slot, "model": name, "sha256": digest(source)})
    return result


def resolve_source(root, kind, profile, record, registry):
    if kind != "characterProfiles" or profile != PROFILE:
        models = (root / "public/assets/models").resolve()
        source, qc = (models / record["model"]).resolve(), (models / record["qc"]).resolve()
        source.relative_to(models)
        qc.relative_to(models)
        return source, qc, record["modelSha256"], record["qcSha256"]
    directory = root / "artifacts/unreal/equipped" / PROFILE
    source, qc = directory / "equipped.glb", directory / "assembly.json"
    receipt = json.loads(qc.read_text(encoding="utf-8"))
    if (receipt.get("schemaVersion") != 1 or receipt.get("profileKey") != PROFILE
            or receipt.get("modules") != module_sources(root, registry)
            or receipt.get("sourceSha256") != digest(source)):
        raise ValueError("Equipped Prelate assembly is stale or incomplete; rebuild it")
    return source, qc, digest(source), digest(qc)
