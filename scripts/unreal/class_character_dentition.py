"""Fixed enamel profiles and weight contracts for the Greenskin dentition pass."""
from __future__ import annotations

import math
import hashlib
import json


def enamel_point(side, root, height, front_y, t, angle):
    """A buried root curves out through the lip before tapering to its cusp."""
    if (side not in (-1, 1) or len(root) != 3
            or not all(math.isfinite(value) for value in (*root, height, front_y, t, angle))
            or height <= 0 or not 0 <= t <= 1 or front_y >= root[1]):
        raise ValueError("Invalid fitted canine profile")
    outward = height * .17
    controls = (root, (root[0], front_y + height * .14, root[2] + height * .32),
                (root[0] + side * outward, front_y - height * .14, root[2] + height * .72),
                (root[0] + side * outward, front_y, root[2] + height))
    a = 1 - t
    center = [a**3 * controls[0][axis] + 3*a*a*t*controls[1][axis]
              + 3*a*t*t*controls[2][axis] + t**3*controls[3][axis] for axis in range(3)]
    tangent = [3*a*a*(controls[1][axis]-controls[0][axis])
               + 6*a*t*(controls[2][axis]-controls[1][axis])
               + 3*t*t*(controls[3][axis]-controls[2][axis]) for axis in range(3)]
    length = math.hypot(tangent[1], tangent[2])
    normal_y, normal_z = tangent[2] / length, -tangent[1] / length
    # A convex crown and a narrow cervix avoid the old straight-sided wedge.
    radius = height * .145 * (1-t)**.72 * (1 + .22*math.sin(math.pi*t))
    radius *= 1 + .018*math.cos(angle*4)
    return (center[0] + radius*math.cos(angle),
            center[1] + radius*.78*math.sin(angle)*normal_y,
            center[2] + radius*.78*math.sin(angle)*normal_z)


def jaw_weights(original, amount):
    if not math.isfinite(amount) or not 0 <= amount <= 1:
        raise ValueError("Invalid lower-face weight")
    if not original or any(not math.isfinite(value) or value <= 0 for value in original.values()):
        raise ValueError("Expected finite positive original weights")
    total = sum(original.values())
    if abs(total-1) > 1e-5:
        raise ValueError("Expected normalized original weights")
    result = {name: value*(1-amount) for name, value in original.items() if name != "jaw"}
    result["jaw"] = amount + original.get("jaw", 0)*(1-amount)
    chosen = sorted(((name, value) for name, value in result.items() if value > 1e-8),
                    key=lambda item: (-item[1], item[0]))[:4]
    total = sum(value for _, value in chosen)
    return {name: value/total for name, value in chosen}


def split_crowns(bounds, contract):
    """Identify retained dental arches by UV islands, independent of anatomy."""
    def key(values):
        if len(values) != 4 or any(not math.isfinite(value) for value in values):
            raise ValueError("Invalid dental UV bounds")
        return tuple(round(value, 6) for value in values)
    reference = {key(row["bounds"]): row["lower"] for row in contract}
    actual = [key(values) for values in bounds]
    # Fitted molars can rise above upper incisors; height cannot identify jaws.
    if (len(reference) != 32 or len(actual) != 32 or len(set(actual)) != 32
            or set(actual) != set(reference)
            or any(type(value) is not bool for value in reference.values())
            or sum(reference.values()) != 16):
        raise ValueError("Changed retained dental UV/arch contract")
    return [reference[value] for value in actual]


def surface_signature(vertices, triangles):
    """Compare oriented surfaces across exporter reordering and UV duplication."""
    if any(not math.isfinite(value) for point in vertices for value in point):
        raise ValueError("Non-finite surface")
    faces = []
    for triangle in triangles:
        if len(triangle) != 3:
            raise ValueError("Expected a triangulated export")
        points = tuple(tuple(vertices[index]) for index in triangle)
        faces.append(min(points, points[1:]+points[:1], points[2:]+points[:2]))
    return hashlib.sha256(json.dumps(sorted(faces), separators=(",", ":")).encode()).hexdigest()
