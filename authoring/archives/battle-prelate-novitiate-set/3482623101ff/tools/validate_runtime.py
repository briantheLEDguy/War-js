"""Read-only GLB audit for the explicitly authored Battle Prelate runtime bundle.

Only the optional JSON report is written. This is a structural/budget gate, not a
visual likeness or animation-intersection approval. Compressed/sparse geometry is
rejected rather than silently omitted from the binary audit.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import struct
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SLOTS = ("body", "head", "shoulders", "chest", "hands", "waist", "legs", "feet", "back", "tabard", "weapon")
CLIPS = {"idle", "walk", "run", "combat_idle", "attack_melee", "attack_ranged", "cast", "death", "jump"}
LOD_LIMITS = {0: 120000, 1: 60000, 2: 30000}
EVALUATED_ARCHIVE_NAME = "evaluated_lods.json.gz"
FORMATS = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
COMPONENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}


class AuditError(ValueError):
    """A file cannot be audited safely or does not conform to the runtime gate."""


def require(condition, message):
    if not condition:
        raise AuditError(message)


def integer(value, label, minimum=0):
    require(type(value) is int and value >= minimum, f"{label} must be an integer >= {minimum}")
    return value


def item(items, index, label):
    integer(index, label)
    require(index < len(items), f"{label} index {index} is out of range")
    return items[index]


def finite(values, label):
    require(all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in values),
            f"{label} contains nonfinite or nonnumeric values")


def sha256(payload):
    return hashlib.sha256(payload).hexdigest()


class Glb:
    def __init__(self, payload, path=None, runtime_root=None):
        self.path = Path(path).resolve() if path else None
        self.runtime_root = Path(runtime_root).resolve() if runtime_root else (self.path.parent if self.path else None)
        self.payload = payload
        self.external_files = {}
        self._accessors = {}
        require(len(payload) >= 20, "Truncated GLB header")
        magic, version, length = struct.unpack_from("<4sII", payload)
        require(magic == b"glTF" and version == 2, "Expected GLB version 2")
        require(length == len(payload), "GLB declared length does not match file size")
        chunks = []
        offset = 12
        while offset < length:
            require(offset + 8 <= length, "Truncated GLB chunk header")
            size, kind = struct.unpack_from("<II", payload, offset)
            require(size % 4 == 0 and offset + 8 + size <= length, "Invalid GLB chunk length")
            chunks.append((kind, payload[offset + 8:offset + 8 + size]))
            offset += size + 8
        require(chunks and chunks[0][0] == 0x4E4F534A, "GLB first chunk must contain JSON")
        require(sum(kind == 0x4E4F534A for kind, _ in chunks) == 1, "GLB must contain exactly one JSON chunk")
        require(sum(kind == 0x004E4942 for kind, _ in chunks) == 1, "GLB must contain exactly one binary chunk")
        try:
            self.document = json.loads(chunks[0][1].decode("utf-8").rstrip("\x00 \t\r\n"))
        except (UnicodeError, ValueError) as exc:
            raise AuditError(f"Invalid GLB JSON: {exc}") from exc
        require(isinstance(self.document, dict), "GLB JSON must contain an object")
        require(self.document.get("asset", {}).get("version") == "2.0", "Expected glTF asset version 2.0")
        self.binary = next(data for kind, data in chunks if kind == 0x004E4942)
        buffers = self.document.get("buffers", [])
        require(len(buffers) == 1 and "uri" not in buffers[0], "Geometry must use the single embedded GLB buffer")
        self.buffer_size = integer(buffers[0].get("byteLength"), "buffer byteLength")
        require(self.buffer_size <= len(self.binary) <= self.buffer_size + 3, "Binary buffer length/padding mismatch")

    def view(self, index):
        view = item(self.document.get("bufferViews", []), index, "bufferView")
        require(view.get("buffer", 0) == 0, "bufferView does not use embedded buffer")
        require(not view.get("extensions"), "Compressed or extended bufferViews are not supported by this audit")
        start = integer(view.get("byteOffset", 0), "bufferView byteOffset")
        length = integer(view.get("byteLength"), "bufferView byteLength")
        require(start + length <= self.buffer_size, "bufferView extends beyond embedded buffer")
        return view, start, length

    def accessor(self, index):
        if index in self._accessors:
            return self._accessors[index]
        acc = item(self.document.get("accessors", []), index, "accessor")
        require("sparse" not in acc, "Sparse accessor requires a separate decoder; not accepted by this gate")
        require("bufferView" in acc, "Accessor has no embedded bufferView")
        require(acc.get("componentType") in FORMATS and acc.get("type") in COMPONENTS, "Unsupported accessor layout")
        fmt, width = FORMATS[acc["componentType"]]
        count = integer(acc.get("count"), "accessor count", 1)
        dimensions = COMPONENTS[acc["type"]]
        require(not acc["type"].startswith("MAT") or width == 4, "Non-float matrix padding is not supported by this gate")
        view, start, length = self.view(acc["bufferView"])
        offset = integer(acc.get("byteOffset", 0), "accessor byteOffset")
        element_size = width * dimensions
        stride = integer(view.get("byteStride", element_size), "accessor stride", 1)
        require(stride >= element_size and stride % width == 0, "Accessor stride is shorter than an element or misaligned")
        require((start + offset) % width == 0, "Accessor byte offset is misaligned")
        require(offset + (count - 1) * stride + element_size <= length, "Accessor exceeds bufferView bounds")
        normalized = acc.get("normalized", False)
        require(type(normalized) is bool, "Accessor normalized must be boolean")
        require(not normalized or acc["componentType"] in {5120, 5121, 5122, 5123}, "Invalid normalized accessor type")
        raw = [struct.unpack_from("<" + fmt * dimensions, self.binary, start + offset + n * stride) for n in range(count)]
        if normalized:
            divisor = {5120: 127, 5121: 255, 5122: 32767, 5123: 65535}[acc["componentType"]]
            signed = acc["componentType"] in {5120, 5122}
            rows = [tuple(max(-1, v / divisor) if signed else v / divisor for v in row) for row in raw]
        else:
            rows = raw
        logical = b"".join(self.binary[start + offset + n * stride:start + offset + n * stride + element_size] for n in range(count))
        result = {"meta": acc, "rows": rows, "raw": raw, "sha256": sha256(logical)}
        self._accessors[index] = result
        return result

    def typed(self, index, kind, component_types, label):
        acc = self.accessor(index)
        require(acc["meta"]["type"] == kind and acc["meta"]["componentType"] in component_types, f"{label} has invalid accessor type")
        finite((v for row in acc["rows"] for v in row), label)
        return acc

    def image(self, index):
        image = item(self.document.get("images", []), index, "image")
        if "bufferView" in image:
            _, start, length = self.view(image["bufferView"])
            return self.binary[start:start + length]
        uri = image.get("uri", "")
        require(isinstance(uri, str) and bool(uri), "Image lacks URI or bufferView")
        parsed = urlsplit(uri)
        require(not parsed.scheme and not parsed.netloc and not parsed.query and not parsed.fragment,
                "Texture must be embedded or use a runtime-relative file URI")
        require(self.path is not None and self.runtime_root is not None, "External image has no runtime directory")
        path = (self.path.parent / unquote(uri)).resolve()
        require(path.is_relative_to(self.runtime_root), "External texture escapes runtime directory")
        require(path.is_file(), f"External texture is missing: {uri}")
        payload = path.read_bytes()
        self.external_files[str(path)] = {"bytes": len(payload), "sha256": sha256(payload)}
        return payload


def skin_signatures(glb):
    nodes = glb.document.get("nodes", [])
    parents = {}
    for parent, node in enumerate(nodes):
        for child in node.get("children", []):
            item(nodes, child, "child node")
            require(child not in parents, "Node has multiple parents")
            parents[child] = parent
    signatures = []
    for index, skin in enumerate(glb.document.get("skins", [])):
        joints = skin.get("joints", [])
        require(joints and len(set(joints)) == len(joints), "Skin has missing or duplicate joints")
        require("inverseBindMatrices" in skin, "Skin lacks explicit inverseBindMatrices")
        matrices = glb.typed(skin["inverseBindMatrices"], "MAT4", {5126}, "inverseBindMatrices")
        require(len(matrices["rows"]) == len(joints), "inverseBindMatrices count differs from joint count")
        named = {}
        for joint, matrix in zip(joints, matrices["rows"]):
            node = item(nodes, joint, "skin joint")
            name = node.get("name")
            require(isinstance(name, str) and name and name not in named, "Joint names must be present and unique")
            parent = parents.get(joint)
            named[name] = {"inverse_bind": list(matrix), "parent": nodes[parent].get("name") if parent in joints else None}
        signatures.append({"skin": index, "joints": named, "inverse_bind_sha256": matrices["sha256"]})
    return signatures


def validate_weights(glb, attributes, vertex_count, skin):
    sets = sorted({key.split("_")[-1] for key in attributes if key.startswith(("JOINTS_", "WEIGHTS_"))})
    require("0" in sets, "Skinned primitive lacks JOINTS_0/WEIGHTS_0")
    decoded = []
    for number in sets:
        require(number.isdecimal(), "Invalid skin attribute suffix")
        require(f"JOINTS_{number}" in attributes and f"WEIGHTS_{number}" in attributes, "Unpaired JOINTS/WEIGHTS attributes")
        joints = glb.typed(attributes[f"JOINTS_{number}"], "VEC4", {5121, 5123}, "JOINTS")
        weights = glb.typed(attributes[f"WEIGHTS_{number}"], "VEC4", {5121, 5123, 5126}, "WEIGHTS")
        require(not joints["meta"].get("normalized", False), "JOINTS must contain integer indices")
        require(weights["meta"]["componentType"] == 5126 or weights["meta"].get("normalized", False), "Integer WEIGHTS must be normalized")
        require(len(joints["rows"]) == len(weights["rows"]) == vertex_count, "Skin accessor count differs from POSITION")
        require(all(0 <= j < len(skin["joints"]) for row in joints["rows"] for j in row), "JOINTS index exceeds skin joint count")
        decoded.append((joints["rows"], weights["rows"]))
    maximum = 0
    for vertex in range(vertex_count):
        values = [weight for _, weights in decoded for weight in weights[vertex]]
        require(all(0 <= weight <= 1 for weight in values), "WEIGHTS must lie in [0,1]")
        influences = sum(weight > 1e-6 for weight in values)
        require(0 < influences <= 4, "Vertex has zero or more than four skin influences")
        require(abs(sum(values) - 1) <= 1e-3, "Vertex skin weights do not sum to one")
        maximum = max(maximum, influences)
    return maximum


def validate_materials(glb, primitives):
    from PIL import Image
    results = []
    cache = {}
    for material_index in sorted({p.get("material", -1) for p in primitives}):
        material = item(glb.document.get("materials", []), material_index, "material")
        pbr = material.get("pbrMetallicRoughness", {})
        channels = {"baseColor": pbr.get("baseColorTexture"), "normal": material.get("normalTexture"),
                    "metallicRoughness": pbr.get("metallicRoughnessTexture"), "occlusion": material.get("occlusionTexture")}
        channel_info = {}
        for name, info in channels.items():
            require(isinstance(info, dict) and "index" in info, f"Material {material_index} is missing required {name} texture")
            texture = item(glb.document.get("textures", []), info["index"], "texture")
            require("source" in texture, "Texture uses unsupported compressed image extension")
            source = texture["source"]
            if source not in cache:
                payload = glb.image(source)
                try:
                    with Image.open(io.BytesIO(payload)) as image:
                        width, height = image.size
                        image.verify()
                except Exception as exc:
                    raise AuditError(f"Image {source} cannot be decoded: {exc}") from exc
                require(0 < width <= 2048 and 0 < height <= 2048, f"Texture {source} exceeds 2048 pixels")
                cache[source] = {"image": source, "width": width, "height": height, "sha256": sha256(payload)}
            texcoord = info.get("extensions", {}).get("KHR_texture_transform", {}).get("texCoord", info.get("texCoord", 0))
            integer(texcoord, "texture texCoord")
            for primitive in primitives:
                if primitive.get("material") == material_index:
                    require(f"TEXCOORD_{texcoord}" in primitive.get("attributes", {}), f"Material texture refers to missing TEXCOORD_{texcoord}")
            channel_info[name] = cache[source]
        results.append({"material": material_index, "name": material.get("name"), "channels": channel_info})
    return results


def validate_animations(glb, require_clips):
    animations = glb.document.get("animations", [])
    names = [a.get("name") for a in animations]
    require(len(names) == len(set(names)), "Animation names are duplicated")
    if require_clips:
        require(CLIPS.issubset(set(names)), f"Missing body animations: {sorted(CLIPS - set(names))}")
    joint_nodes = {j for skin in glb.document.get("skins", []) for j in skin.get("joints", [])}
    results = []
    for animation in animations:
        channels = animation.get("channels", [])
        require(bool(channels), f"Animation {animation.get('name')} contains no channels")
        moving = 0
        duration = 0
        for channel in channels:
            target = channel.get("target", {})
            item(glb.document.get("nodes", []), target.get("node"), "animation target node")
            path = target.get("path")
            require(path in {"translation", "rotation", "scale"}, "Only joint transform animation is supported by this contract")
            sampler = item(animation.get("samplers", []), channel.get("sampler"), "animation sampler")
            times = glb.typed(sampler.get("input"), "SCALAR", {5126}, "animation times")["rows"]
            require(all(t[0] >= 0 for t in times) and all(b[0] > a[0] for a, b in zip(times, times[1:])), "Animation times must be nonnegative and strictly increasing")
            outputs = glb.typed(sampler.get("output"), "VEC4" if path == "rotation" else "VEC3", {5126}, "animation output")["rows"]
            interpolation = sampler.get("interpolation", "LINEAR")
            require(interpolation in {"LINEAR", "STEP", "CUBICSPLINE"}, "Unsupported animation interpolation")
            require(len(outputs) == len(times) * (3 if interpolation == "CUBICSPLINE" else 1), "Animation input/output count mismatch")
            values = outputs[1::3] if interpolation == "CUBICSPLINE" else outputs
            if target["node"] in joint_nodes and any(any(abs(a - b) > 1e-6 for a, b in zip(values[0], row)) for row in values[1:]):
                moving += 1
            duration = max(duration, times[-1][0] - times[0][0])
        if require_clips and animation.get("name") in CLIPS:
            require(duration > 0 and moving > 0, f"Animation {animation['name']} contains no changing joint samples")
        results.append({"name": animation.get("name"), "channels": len(channels), "changing_joint_channels": moving, "duration_seconds": duration})
    return results


def validate_glb(glb, slot):
    require(slot in SLOTS, f"Unknown runtime slot {slot}")
    doc = glb.document
    skins = skin_signatures(glb)
    if slot != "weapon":
        require(bool(skins), "Body/armor module contains no skin")
        require(any(n.get("name") == "humanoid_game_v2" for n in doc.get("nodes", [])), "Missing canonical humanoid_game_v2 rig node")
    scenes = doc.get("scenes", [])
    scene = item(scenes, doc.get("scene", 0), "default scene")
    active = set()
    visiting = set()
    def visit(index):
        require(index not in visiting, "Node hierarchy contains a cycle")
        if index in active:
            return
        node = item(doc.get("nodes", []), index, "scene node")
        require("EXT_mesh_gpu_instancing" not in node.get("extensions", {}), "GPU-instanced nodes require a separate draw-count audit")
        visiting.add(index)
        for key, length in (("matrix", 16), ("translation", 3), ("rotation", 4), ("scale", 3)):
            if key in node:
                require(isinstance(node[key], list) and len(node[key]) == length, f"Node {key} has invalid length")
                finite(node[key], f"Node {key}")
        for child in node.get("children", []):
            visit(child)
        visiting.remove(index)
        active.add(index)
    for index in scene.get("nodes", []):
        visit(index)
    totals = {"triangles": 0, "vertices": 0, "draw_calls": 0, "max_influences": 0}
    used_meshes = set()
    primitives = []
    geometry = []
    source_records = []
    for node_index in sorted(active):
        node = doc["nodes"][node_index]
        if "mesh" not in node:
            continue
        mesh = item(doc.get("meshes", []), node["mesh"], "mesh")
        used_meshes.add(node["mesh"])
        records = node.get("extras", {}).get("source_records", [])
        if isinstance(records, str):
            try:
                records = json.loads(records)
            except ValueError as exc:
                raise AuditError("Mesh source_records extras are not valid JSON") from exc
        require(isinstance(records, list), "Mesh source_records extras must contain a list")
        source_records.extend(records)
        if slot != "weapon":
            skin = item(doc.get("skins", []), node.get("skin"), "mesh skin")
        else:
            require("skin" not in node, "Socketed weapon must not carry a body skin")
            skin = None
        require(bool(mesh.get("primitives")), "Mesh has no primitives")
        for pindex, primitive in enumerate(mesh["primitives"]):
            require(primitive.get("mode", 4) == 4, "Runtime geometry must use TRIANGLES")
            require(not primitive.get("extensions"), "Compressed/extended geometry is not supported by this binary audit")
            require(not primitive.get("targets"), "Morph geometry is outside the rigid/skin source contract")
            attributes = primitive.get("attributes", {})
            position = glb.typed(attributes.get("POSITION"), "VEC3", {5126}, "POSITION")
            positions = position["rows"]
            count = len(positions)
            normal = glb.typed(attributes.get("NORMAL"), "VEC3", {5126}, "NORMAL")
            require(len(normal["rows"]) == count, "NORMAL count differs from POSITION")
            require(all(sum(v * v for v in row) > 1e-10 for row in normal["rows"]), "NORMAL contains a zero vector")
            for name, accessor_index in attributes.items():
                acc = glb.accessor(accessor_index)
                require(len(acc["rows"]) == count, f"{name} count differs from POSITION")
                finite((v for row in acc["rows"] for v in row), name)
                if name.startswith("TEXCOORD_"):
                    require(acc["meta"]["type"] == "VEC2", "UV accessor must use VEC2")
            if "indices" in primitive:
                indices_acc = glb.typed(primitive["indices"], "SCALAR", {5121, 5123, 5125}, "indices")
                require(not indices_acc["meta"].get("normalized", False), "Indices cannot be normalized")
                indices = [row[0] for row in indices_acc["rows"]]
                indices_hash = indices_acc["sha256"]
            else:
                indices = list(range(count))
                indices_hash = None
            require(len(indices) % 3 == 0 and bool(indices), "Triangle index count is not a positive multiple of three")
            require(all(0 <= i < count for i in indices), "Triangle index exceeds POSITION count")
            for start in range(0, len(indices), 3):
                a, b, c = (positions[i] for i in indices[start:start + 3])
                u = [b[n] - a[n] for n in range(3)]
                v = [c[n] - a[n] for n in range(3)]
                cross = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
                require(sum(value * value for value in cross) > 1e-24, "Geometry contains a degenerate triangle")
            if skin is not None:
                totals["max_influences"] = max(totals["max_influences"], validate_weights(glb, attributes, count, skin))
            totals["triangles"] += len(indices) // 3
            totals["vertices"] += count
            totals["draw_calls"] += 1
            primitives.append(primitive)
            geometry.append({"node": node_index, "mesh": node["mesh"], "primitive": pindex, "triangles": len(indices)//3,
                             "position_sha256": position["sha256"], "indices_sha256": indices_hash})
    require(used_meshes, "No mesh is reachable from the default scene")
    require(used_meshes == set(range(len(doc.get("meshes", [])))), "GLB contains orphan meshes outside the active scene")
    if slot == "body":
        require(totals["triangles"] <= 45000, "Body exceeds 45,000 triangles")
        require(totals["draw_calls"] <= 4, "Body exceeds four draw calls")
    elif slot != "weapon":
        require(totals["triangles"] <= 14000, f"Armor module {slot} exceeds 14,000 triangles")
        require(totals["draw_calls"] <= 2, f"Armor module {slot} exceeds two draw calls")
    return dict(totals, skins=skins, geometry=geometry, source_records=source_records, materials=validate_materials(glb, primitives),
                animations=validate_animations(glb, slot == "body"), external_files=glb.external_files)


def compare_skins(body, module):
    require(len(body) == 1 and len(module) == 1, "Each module must contain exactly one comparable canonical skin")
    left, right = body[0]["joints"], module[0]["joints"]
    require(left.keys() == right.keys(), "Module joint names differ from body skin")
    for name in left:
        require(left[name]["parent"] == right[name]["parent"], f"Joint parent differs from body: {name}")
        require(all(math.isclose(a, b, rel_tol=1e-6, abs_tol=1e-6) for a, b in zip(left[name]["inverse_bind"], right[name]["inverse_bind"])),
                f"inverseBindMatrices differ from body for joint {name}")


def model_name(slot, lod):
    stem = "chr_civic_battle_prelate_t1_m" if slot == "body" else "wep_civic_battle_prelate_dawn_maul" if slot == "weapon" else f"arm_civic_battle_prelate_{slot}_novitiate_m"
    return stem + (f"_lod{lod}" if lod else "") + ".glb"


def validate_evaluated_archive(runtime, stage):
    """Bind inspection data to the build without counting it as a game asset."""
    expected = stage.get("evaluated_mesh_archive_sha256")
    require(isinstance(expected, str) and len(expected) == 64 and all(c in "0123456789abcdef" for c in expected),
            "Missing or invalid evaluated_mesh_archive_sha256")
    runtime = Path(runtime).resolve()
    archive = (runtime / EVALUATED_ARCHIVE_NAME).resolve()
    require(archive.is_relative_to(runtime), "Evaluated mesh archive escapes runtime directory")
    require(archive.is_file(), f"Evaluated mesh archive is missing: {EVALUATED_ARCHIVE_NAME}")
    payload = archive.read_bytes()
    require(sha256(payload) == expected, "Evaluated mesh archive hash changed since build")
    return {"file": EVALUATED_ARCHIVE_NAME, "sha256": expected, "bytes": len(payload)}


def validate_bundle(runtime, lods=(0, 1, 2)):
    runtime = Path(runtime).resolve()
    require(lods and len(set(lods)) == len(lods) and all(lod in LOD_LIMITS for lod in lods), "LODs must be a unique subset of 0,1,2")
    report = {"schema_version": 1, "status": "failed", "created_utc": datetime.now(timezone.utc).isoformat(),
              "runtime_directory": str(runtime), "scope": "Structural binary and budget validation; no visual likeness, clipping, or deformation approval",
              "requested_lods": list(lods), "full_bundle_requested": set(lods) == set(LOD_LIMITS),
              "limits": {"armor_triangles": 14000, "body_triangles": 45000, "lod_triangles": LOD_LIMITS, "draw_calls": 16,
                         "texture_dimension": 2048, "bundle_bytes": 80000000, "weight_sum_tolerance": .001, "inverse_bind_tolerance": 1e-6},
              "lods": {}, "errors": [], "warnings": [], "assets": {}}
    assets = {}
    for lod in lods:
        modules = {}
        for slot in SLOTS:
            filename = model_name(slot, lod)
            path = runtime / filename
            if not path.is_file():
                report["errors"].append(f"LOD{lod}/{slot}: missing {filename}")
                continue
            payload = path.read_bytes()
            assets[str(path)] = {"bytes": len(payload), "sha256": sha256(payload)}
            try:
                glb = Glb(payload, path, runtime)
                result = validate_glb(glb, slot)
                assets.update(glb.external_files)
                modules[slot] = dict(result, model=filename, bytes=len(payload), sha256=sha256(payload))
            except (AuditError, KeyError, TypeError, IndexError, AttributeError, OSError) as exc:
                report["errors"].append(f"LOD{lod}/{slot}: {exc}")
        for slot, module in modules.items():
            if slot in {"body", "weapon"} or "body" not in modules:
                continue
            try:
                compare_skins(modules["body"]["skins"], module["skins"])
            except AuditError as exc:
                report["errors"].append(f"LOD{lod}/{slot}: {exc}")
        total = sum(m["triangles"] for m in modules.values())
        calls = sum(m["draw_calls"] for m in modules.values())
        if total > LOD_LIMITS[lod]:
            report["errors"].append(f"LOD{lod}: equipped triangles {total} exceed {LOD_LIMITS[lod]}")
        if calls > 16:
            report["errors"].append(f"LOD{lod}: equipped draw calls {calls} exceed 16")
        report["lods"][str(lod)] = {"complete": len(modules) == len(SLOTS), "modules": modules,
                                   "total_triangles": total, "draw_calls": calls}
    report["assets"] = assets
    report["bundle_bytes"] = sum(a["bytes"] for a in assets.values())
    if report["bundle_bytes"] > 80000000:
        report["errors"].append(f"Bundle size {report['bundle_bytes']} exceeds 80,000,000 bytes across requested assets")
    stage_path = runtime / "runtime_report.json"
    if stage_path.is_file():
        stage_payload = stage_path.read_bytes()
        report["stage_report_sha256"] = sha256(stage_payload)
        try:
            stage = json.loads(stage_payload)
            if report["full_bundle_requested"] or "evaluated_mesh_archive_sha256" in stage:
                report["evaluated_mesh_archive"] = validate_evaluated_archive(runtime, stage)
            else:
                report["warnings"].append("Partial audit: no declared evaluated mesh archive; inspection provenance has not been cross-checked")
            for lod, data in report["lods"].items():
                for slot, module in data["modules"].items():
                    recorded = stage.get("lods", {}).get(lod, {}).get("modules", {}).get(slot, {})
                    for field in ("sha256", "bytes", "triangles"):
                        if recorded.get(field) != module[field]:
                            report["errors"].append(f"LOD{lod}/{slot}: {field} differs from runtime_report.json")
                    records = recorded.get("source_records")
                    if not records or records != module["source_records"]:
                        report["errors"].append(f"LOD{lod}/{slot}: merged source_records missing or differ from GLB extras")
                    for record in records or []:
                        source_root = runtime.parent.parent / "battle-prelate-reference-rebuild" if slot in {"body", "weapon"} and recorded.get("shared_asset") else runtime.parent
                        source = (source_root / record["file"]).resolve()
                        if not source.is_relative_to(source_root / "source") or not source.is_file():
                            report["errors"].append(f"LOD{lod}/{slot}: source record path is invalid or missing")
                        elif sha256(source.read_bytes()) != record["sha256"]:
                            report["errors"].append(f"LOD{lod}/{slot}: source hash changed since build: {record['file']}")
        except (ValueError, TypeError, AttributeError, KeyError, OSError) as exc:
            report["errors"].append(f"Invalid runtime_report.json: {exc}")
    else:
        if report["full_bundle_requested"]:
            report["errors"].append("Full-bundle validation requires runtime_report.json and its declared evaluated mesh archive")
        else:
            report["warnings"].append("Partial audit: no runtime_report.json; binary hashes are recorded, but build provenance has not been cross-checked")
    if not report["errors"]:
        report["status"] = "passed"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, default=ROOT / "runtime")
    parser.add_argument("--lods", default="0,1,2", help="Only use a subset for an explicitly partial audit")
    parser.add_argument("--report", type=Path, help="Write JSON report here; defaults to runtime/validation_report.json")
    args = parser.parse_args()
    try:
        report = validate_bundle(args.runtime, tuple(int(value) for value in args.lods.split(",")))
    except (AuditError, ValueError, OSError) as exc:
        print(f"RUNTIME_VALIDATION_FAILED: {exc}")
        return 1
    destination = args.report or args.runtime / "validation_report.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "files": len(report["assets"]), "bundle_bytes": report["bundle_bytes"], "errors": report["errors"], "report": str(destination)}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
