"""Author deterministic Greenskin targets from pinned CC0 MPFB source targets.

Run through Blender so the installed MPFB extension resolves both its bundled
target library and the user asset-pack directory. The emitted targets retain
the hm08 vertex order and are reviewed like any other source artifact.
"""

from __future__ import annotations

from collections import defaultdict
import gzip
import hashlib
import json
from pathlib import Path

from bl_ext.blender_org.mpfb.services import LocationService


PIPELINE_ROOT = Path(__file__).resolve().parent.parent
BODY_FAMILY_ROOT = PIPELINE_ROOT / "data" / "body-families"
OUTPUT_ROOT = BODY_FAMILY_ROOT / "targets" / "mire_brutish_v1"


RECIPES = {
    "mire_cranium_brow_v1": [
        ("system", "head/head-square.target.gz", 0.38),
        ("system", "head/head-scale-horiz-incr.target.gz", 0.22),
        ("system", "forehead/forehead-trans-forward.target.gz", 0.34),
        ("user", "nose/elvs_nose_widening_1.target", 0.14),
    ],
    "mire_ears_v1": [
        ("user", "ears/elvs_flap_ears_2.target", 0.72),
        ("user", "ears/mindfront_ear_details.target", 0.30),
        ("user", "ears/jujube_ear_canal.target", 0.18),
    ],
    "mire_jaw_v1": [
        ("system", "chin/chin-width-incr.target.gz", 0.70),
        ("system", "chin/chin-prognathism-incr.target.gz", 0.48),
        ("system", "chin/chin-bones-incr.target.gz", 0.26),
        ("system", "mouth/mouth-scale-horiz-incr.target.gz", 0.22),
    ],
    # This morph creates the lip/jaw clearance for the fitted tusk body part.
    # Tusks are separate original meshes bound to the head bone at export.
    "mire_tusks_v1": [
        ("system", "mouth/mouth-lowerlip-width-incr.target.gz", 0.28),
        ("system", "mouth/mouth-lowerlip-volume-incr.target.gz", 0.18),
        ("system", "mouth/mouth-trans-forward.target.gz", 0.12),
    ],
}


def read_target(path: Path) -> dict[int, tuple[float, float, float]]:
    opener = gzip.open if path.suffix == ".gz" else open
    values = {}
    with opener(path, "rt", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            values[int(parts[0])] = tuple(float(value) for value in parts[1:4])
    return values


def source_path(kind: str, relative_path: str) -> Path:
    if kind == "system":
        return Path(LocationService.get_mpfb_data("targets")) / relative_path
    return Path(LocationService.get_user_data("targets")) / relative_path


def write_target(target_id: str, recipe: list[tuple[str, str, float]]) -> dict:
    combined = defaultdict(lambda: [0.0, 0.0, 0.0])
    sources = []
    for kind, relative_path, weight in recipe:
        path = source_path(kind, relative_path)
        if not path.is_file():
            raise FileNotFoundError(f"Required CC0 target is missing: {path}")
        payload = path.read_bytes()
        sources.append({
            "kind": kind,
            "relativePath": relative_path,
            "weight": weight,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "license": "CC0-1.0",
        })
        for vertex_index, offsets in read_target(path).items():
            for axis in range(3):
                combined[vertex_index][axis] += offsets[axis] * weight

    lines = []
    for vertex_index in sorted(combined):
        x, y, z = combined[vertex_index]
        if max(abs(x), abs(y), abs(z)) < 1e-8:
            continue
        lines.append(f"{vertex_index} {x:.8f} {y:.8f} {z:.8f}")

    output = OUTPUT_ROOT / f"{target_id}.target"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    output_hash = hashlib.sha256(output.read_bytes()).hexdigest()
    return {
        "targetId": target_id,
        "output": output.relative_to(BODY_FAMILY_ROOT).as_posix(),
        "sha256": output_hash,
        "vertexOffsets": len(lines),
        "license": "LicenseRef-WarJS-Original",
        "derivedFrom": sources,
    }


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    records = [write_target(target_id, recipe) for target_id, recipe in RECIPES.items()]
    provenance = {
        "schemaVersion": 1,
        "bodyFamily": "mire_brutish_v1",
        "sourceTopology": "MPFB hm08",
        "generator": "blender/author_mire_targets.py",
        "targets": records,
    }
    provenance_path = OUTPUT_ROOT / "target-provenance.json"
    provenance_path.write_text(
        json.dumps(provenance, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    main()
