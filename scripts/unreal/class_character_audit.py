"""Measure rest anatomy and static skin deformation; this is not motion approval."""
from __future__ import annotations

import math


def texture_srgb(hex_color: str) -> tuple[float, float, float]:
    """RGB samples for packed sRGB textures, without a second gamma conversion."""
    value = hex_color.removeprefix("#")
    if len(value) != 6:
        raise ValueError("Expected an RGB hex colour")
    return tuple(int(value[index:index + 2], 16) / 255 for index in (0, 2, 4))


def canine_surface(side: int, root: tuple[float, float, float], height: float):
    """Closed, curved lower canine with an oval root and a fine enamel tip."""
    if side not in (-1, 1) or not math.isfinite(height) or height <= 0:
        raise ValueError("Invalid canine dimensions")
    vertices, faces = [], []
    rings, segments = 12, 16
    for ring in range(rings):
        t = ring / rings
        radius = height * .16 * (1 - t) ** .85
        center = (root[0] + side * height * .10 * t * t,
                  root[1] - height * (.32 * t - .10 * t * t), root[2] + height * t)
        for segment in range(segments):
            angle = 2 * math.pi * segment / segments
            ridge = 1 + .025 * math.cos(angle * 4)
            vertices.append((center[0] + radius * math.cos(angle) * ridge,
                             center[1] + radius * math.sin(angle) * .8 * ridge, center[2]))
            if ring:
                a = (ring - 1) * segments + segment
                b = (ring - 1) * segments + (segment + 1) % segments
                faces.append((a, b, b + segments, a + segments))
    tip = len(vertices)
    vertices.append((root[0] + side * height * .10, root[1] - height * .22, root[2] + height))
    for segment in range(segments):
        faces.append(((rings - 1) * segments + segment,
                      (rings - 1) * segments + (segment + 1) % segments, tip))
    faces.append(tuple(reversed(range(segments))))
    return vertices, faces


def limb_checks(lengths: dict[str, float]) -> dict[str, bool]:
    checks = {"finitePositiveLengths": all(math.isfinite(value) and value > 0 for value in lengths.values())}
    if not checks["finitePositiveLengths"]:
        return checks
    for segment in ("upper_arm", "forearm", "thigh", "shin"):
        left, right = lengths[f"{segment}_L"], lengths[f"{segment}_R"]
        checks[f"{segment}Symmetry"] = abs(left - right) / max(left, right) <= 0.015
    for side in ("L", "R"):
        checks[f"armRatio{side}"] = 0.70 <= lengths[f"forearm_{side}"] / lengths[f"upper_arm_{side}"] <= 1.20
        checks[f"legRatio{side}"] = 0.70 <= lengths[f"shin_{side}"] / lengths[f"thigh_{side}"] <= 1.20
    return checks


def weight_checks(rows: list[list[float]]) -> dict[str, bool]:
    return {
        "allVerticesWeighted": bool(rows) and all(row for row in rows),
        "fourInfluenceLimit": bool(rows) and all(len(row) <= 4 for row in rows),
        "finitePositiveWeights": bool(rows) and all(math.isfinite(value) and value > 0 for row in rows for value in row),
        "normalizedWeights": bool(rows) and all(abs(sum(row) - 1.0) <= 1e-5 for row in rows),
    }


def deformation_checks(row: dict, height: float) -> bool:
    # A ratio alone over-penalizes dense topology: a sub-mm edge can stretch
    # several times without a visible spike. Bound extension in body units as
    # well as the distribution across the whole surface, retaining every maximum.
    return (row["finite"] and row["p01EdgeRatio"] > .15 and row["p99EdgeRatio"] < 1.8
            and row["maxEdgeExtensionM"] <= height * .018)


def build_audit(body, meshes, rig, request, capture=None):
    import bpy
    from mathutils import Matrix, Quaternion, Vector

    contract_path = __import__("pathlib").Path(__file__).resolve().parents[1] / "blender-character-pipeline/data/body-families/humanoid_game_v2.skeleton.json"
    contract = __import__("json").loads(contract_path.read_text())
    expected = {bone["name"]: bone["parent"] for bone in contract["bones"]}
    observed = {bone.name: bone.parent.name if bone.parent else None for bone in rig.data.bones}
    bones = set(observed)
    weights = [[assignment.weight for assignment in vertex.groups if mesh.vertex_groups[assignment.group].name in bones and assignment.weight > 1e-8]
               for mesh in meshes for vertex in mesh.data.vertices]
    lengths = {name: (rig.matrix_world.to_3x3() @ bone.vector).length for name, bone in rig.data.bones.items()
               if name.startswith(("upper_arm_", "forearm_", "thigh_", "shin_"))}
    world = rig.matrix_world
    shoulder_span = (world @ rig.data.bones["upper_arm_L"].head_local - world @ rig.data.bones["upper_arm_R"].head_local).length

    def coordinates():
        bpy.context.view_layer.update()
        evaluated = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        geometry = evaluated.to_mesh()
        try:
            return [body.matrix_world @ vertex.co for vertex in geometry.vertices]
        finally:
            evaluated.to_mesh_clear()

    def reset():
        for bone in rig.pose.bones:
            bone.matrix_basis = Matrix.Identity(4)
        bpy.context.view_layer.update()

    def rotate(name, world_axis, degrees):
        bone = rig.data.bones[name]
        axis = (world.to_3x3() @ bone.matrix_local.to_3x3()).inverted() @ world_axis
        rig.pose.bones[name].rotation_mode = "QUATERNION"
        rig.pose.bones[name].rotation_quaternion = Quaternion(axis.normalized(), math.radians(degrees))

    reset()
    rest = coordinates()
    height = max(vertex.z for vertex in rest) - min(vertex.z for vertex in rest)
    scale = list(rig.matrix_world.to_scale())
    low, high = request["foundation"]["shoulderHeightRatio"]
    checks = {
        **weight_checks(weights), **limb_checks(lengths),
        "canonicalHierarchy": observed == expected,
        "uniformPositiveRigScale": min(scale) > 0 and max(scale) - min(scale) < 1e-5,
        "requestedHeight": abs(height - request["expectedHeightM"]) <= 0.012,
        "groundedFeet": abs(min(vertex.z for vertex in rest)) <= 0.003,
        "raceShoulderProportion": low <= shoulder_span / height <= high,
        "finiteRestMesh": all(math.isfinite(component) for vertex in rest for component in vertex),
    }
    edges = [tuple(edge.vertices) for edge in body.data.edges]
    rest_lengths = [(rest[a] - rest[b]).length for a, b in edges]
    poses = {}
    for pose in ("elbows_100", "knees_110", "arms_overhead", "hip_flexion_65", "grip"):
        reset()
        for side in ("L", "R"):
            if pose == "elbows_100":
                name = "forearm_" + side
                direction = world.to_3x3() @ rig.data.bones[name].vector
                rotate(name, direction.cross(Vector((0, -1, 0))).normalized(), 100)
            elif pose == "knees_110":
                rotate("shin_" + side, Vector((1, 0, 0)), 110)
            elif pose == "arms_overhead":
                rotate("upper_arm_" + side, Vector((0, -1 if side == "L" else 1, 0)), 110)
            elif pose == "hip_flexion_65":
                rotate("thigh_" + side, Vector((-1, 0, 0)), 65)
                rotate("shin_" + side, Vector((1, 0, 0)), 80)
            else:
                # Curl about each finger's local X; this is a rig diagnostic only.
                for finger in ("index", "middle", "ring", "pinky"):
                    for segment in ("01", "02", "03"):
                        bone = rig.pose.bones[f"{finger}_{segment}_{side}"]
                        bone.rotation_mode = "XYZ"
                        bone.rotation_euler.x = math.radians(-55)
        posed = coordinates()
        ratios = sorted((posed[a] - posed[b]).length / length for (a, b), length in zip(edges, rest_lengths) if length > 1e-5)
        # Extreme joints can compress individual edges. Inspect the complete tail,
        # and fail long spikes rather than mistaking a single metric for art review.
        worst = sorted(((posed[a] - posed[b]).length - length, a, b, length) for (a, b), length in zip(edges, rest_lengths))[-5:]
        row = {"minEdgeRatio": ratios[0], "maxEdgeRatio": ratios[-1],
               "p01EdgeRatio": ratios[int(len(ratios) * .01)], "p99EdgeRatio": ratios[int(len(ratios) * .99)],
               "finite": all(math.isfinite(component) for vertex in posed for component in vertex),
               "maxEdgeExtensionM": worst[-1][0],
               "worstStretchedEdges": [{"extensionM": delta, "vertices": [a, b], "restM": length, "restPosition": list(rest[a])} for delta, a, b, length in worst]}
        row["passed"] = deformation_checks(row, height)
        poses[pose] = row
        if capture:
            capture(pose)
    reset()
    checks["staticDeformation"] = all(row["passed"] for row in poses.values())
    return {"checks": checks, "passed": all(checks.values()), "heightM": height,
            "shoulderSpanM": shoulder_span, "shoulderHeightRatio": shoulder_span / height,
            "rigScale": scale, "limbLengthsM": lengths, "staticPoses": poses,
            "limitations": ["Static bend diagnostics are not supplied animation or native equipped clearance approval.",
                            "Joint collapse, twist quality, silhouette and topology also require visual inspection."]}
