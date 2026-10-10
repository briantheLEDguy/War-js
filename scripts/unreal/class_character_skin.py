"""Refine transitions on welded authoring topology before UV seam duplication."""
from __future__ import annotations

import numpy as np
import math
import hashlib
import json
from mathutils.kdtree import KDTree


def refine_source(body, rig, iterations=96, shoulder_iterations=None, anchor_width=.45):
    shoulder_iterations = iterations if shoulder_iterations is None else shoulder_iterations
    if any(type(value) is not int or not 1 <= value <= 256 for value in (iterations, shoulder_iterations)):
        raise ValueError("Skin refinement iterations must be integers between 1 and 256")
    if type(anchor_width) not in (int, float) or not math.isfinite(anchor_width) or not .2 <= anchor_width <= .8:
        raise ValueError("Trunk anchor width must be finite and between .2 and .8")
    names = list(rig.data.bones.keys())
    columns = {name: index for index, name in enumerate(names)}
    groups = {group.index: columns[group.name] for group in body.vertex_groups if group.name in columns}
    weights = np.zeros((len(body.data.vertices), len(names)))
    for vertex in body.data.vertices:
        for group in vertex.groups:
            if group.group in groups:
                weights[vertex.index, groups[group.group]] = group.weight
    if not np.isfinite(weights).all() or np.max(np.abs(weights.sum(axis=1) - 1)) > 1e-5:
        raise RuntimeError("Source body needs normalized finite skin weights")
    original = weights.copy()
    positions = np.array([list(body.matrix_world @ vertex.co) for vertex in body.data.vertices])
    height = np.ptp(positions[:, 2])
    shoulder_field, hip_field = np.zeros(len(weights)), np.zeros(len(weights))
    for name in ("upper_arm_L", "upper_arm_R", "thigh_L", "thigh_R"):
        pivot = np.array(rig.matrix_world @ rig.data.bones[name].head_local)
        distance = np.linalg.norm(positions - pivot, axis=1) / (height * .16)
        falloff = np.clip(1 - distance ** 2, 0, 1) ** 2
        if name.startswith("upper_arm_"):
            shoulder_field = np.maximum(shoulder_field, falloff)
        else:
            hip_field = np.maximum(hip_field, falloff)
    # Protect torso interiors instead of leaking thigh/arm rotation into the
    # pelvis or neck. Smooth falloff avoids a hard boundary in the weight field.
    trunk = weights[:, [columns[name] for name in ("hips", "spine", "chest", "upper_chest", "neck", "head")]].sum(axis=1)
    anchor = np.clip((.95 - trunk) / anchor_width, 0, 1) ** 2
    edges = np.array([list(edge.vertices) for edge in body.data.edges])
    left, right = edges[:, 0], edges[:, 1]
    counts = np.bincount(edges.ravel(), minlength=len(weights))[:, None]
    for iteration in range(max(iterations, shoulder_iterations)):
        field = np.maximum(shoulder_field * (iteration < shoulder_iterations), hip_field * (iteration < iterations)) * anchor
        totals = np.zeros_like(weights)
        np.add.at(totals, left, weights[right])
        np.add.at(totals, right, weights[left])
        weights += (totals / np.maximum(counts, 1) - weights) * field[:, None] * .55
    return dict(names=names, weights=weights, positions=positions,
                evidence=dict(method="welded_source_adjacency_with_smooth_joint_falloff_and_trunk_anchors",
                              iterations=iterations, shoulderIterations=shoulder_iterations, trunkAnchorWidth=anchor_width,
                              radiusHeightRatio=.16, relaxation=.55,
                              changedSourceVertices=int((np.max(np.abs(weights - original), axis=1) > 1e-5).sum())))


def validate_correction(data, identity, source_sha, position_sha, count, names, baseline):
    """Bind fixed weight painting to one exact source and refinement recipe."""
    if (data.get("schemaVersion") != 1 or data.get("identity") != identity
            or data.get("sourceBodySha256") != source_sha
            or data.get("positionSha256") != position_sha
            or data.get("sourceVertexCount") != count or data.get("baseline") != baseline
            or data.get("nativeAccepted") is not False or data.get("runtimeEligible") is not False):
        raise ValueError("Skin correction source, recipe or draft state changed")
    seen = set()
    rows = data.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("Skin correction needs explicit vertex rows")
    for row in rows:
        vertex, weights = row.get("vertex"), row.get("weights")
        if type(vertex) is not int or not 0 <= vertex < count or vertex in seen:
            raise ValueError("Invalid or repeated correction vertex")
        seen.add(vertex)
        if (not isinstance(weights, dict) or not 1 <= len(weights) <= 4
                or not set(weights).issubset(names)
                or any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0 for value in weights.values())
                or abs(sum(weights.values()) - 1) > 1e-6):
            raise ValueError("Correction needs normalized finite canonical weights")
    return rows


def apply_correction(refinement, data, identity, source_sha):
    positions = refinement["positions"]
    position_sha = hashlib.sha256(json.dumps(positions.round(6).tolist(), separators=(",", ":")).encode()).hexdigest()
    evidence = refinement["evidence"]
    baseline = dict(hipIterations=evidence["iterations"], shoulderIterations=evidence["shoulderIterations"],
                    trunkAnchorWidth=evidence["trunkAnchorWidth"])
    rows = validate_correction(data, identity, source_sha, position_sha, len(positions), refinement["names"], baseline)
    columns = {name: index for index, name in enumerate(refinement["names"])}
    maximum = 0
    for item in rows:
        original = refinement["weights"][item["vertex"]]
        selected = np.argsort(original)[-4:]
        base = np.zeros_like(original)
        base[selected] = original[selected] / original[selected].sum()
        corrected = np.zeros_like(original)
        for name, weight in item["weights"].items():
            corrected[columns[name]] = weight
        if any(corrected[index] > 0 and base[index] < 1e-8 for index in range(len(base))):
            raise ValueError("Correction introduced a new bone influence")
        change = float(np.max(np.abs(corrected - base)))
        if change > .2 + 1e-6:
            raise ValueError("Correction exceeded its bounded weight change")
        maximum = max(maximum, change)
        refinement["weights"][item["vertex"]] = corrected
    evidence["localCorrection"] = dict(sourceVertices=len(rows), maximumWeightChange=maximum,
                                        method="fixed_bounded_skin_weights_no_pose_dependent_geometry")


def transfer(body, rig, refinement):
    if set(refinement["names"]) != set(rig.data.bones.keys()):
        raise RuntimeError("Cannot transfer skin weights between different skeleton contracts")
    tree = KDTree(len(refinement["positions"]))
    for index, position in enumerate(refinement["positions"]):
        tree.insert(position, index)
    tree.balance()
    bone_groups = [group for group in body.vertex_groups if group.name in rig.data.bones]
    maximum_distance = 0
    for vertex in body.data.vertices:
        _, index, distance = tree.find(body.matrix_world @ vertex.co)
        if distance > 1e-5:
            raise RuntimeError("Runtime body differs from its welded authoring surface")
        maximum_distance = max(maximum_distance, distance)
        row = refinement["weights"][index]
        chosen = [column for column in np.argsort(row)[-4:] if row[column] > 1e-8]
        total = sum(row[column] for column in chosen)
        if not chosen or total <= 0:
            raise RuntimeError("Refinement produced an unweighted vertex")
        for group in bone_groups:
            group.remove([vertex.index])
        for column in chosen:
            name = refinement["names"][column]
            group = body.vertex_groups.get(name) or body.vertex_groups.new(name=name)
            group.add([vertex.index], float(row[column] / total), "REPLACE")
    return {**refinement["evidence"], "maximumTransferDistanceM": maximum_distance,
            "seamPolicy": "all_uv_duplicates_use_the_same_welded_source_weight_row"}
