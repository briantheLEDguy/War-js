"""Authored outer muscle envelopes for folded proximal-limb correctives."""
import numpy as np


def smoothstep(low, high, value):
    t = np.clip((value - low) / (high - low), 0, 1)
    return t * t * (3 - 2 * t)


def haunch_envelope(rest, posed, definition, side, hip, knee):
    """Return local displacement; all positions use unscaled pelvis rest space.

    Only the lateral haunch is projected. Medial skin, hoof, head and the
    opposite leg retain their positions. The smooth body/muscle union replaces
    the inward fold with an authored external tissue surface.
    """
    body = np.array([row[:5] for row in definition['body'] if row[1] >= -.30])
    body = body[np.argsort(body[:, 1])]
    y, z = posed[:, 1], posed[:, 2]
    cz = np.interp(y, body[:, 1], body[:, 2]); rx = np.interp(y, body[:, 1], body[:, 3]); rz = np.interp(y, body[:, 1], body[:, 4])
    body_x = rx * np.sqrt(np.clip(1 - ((z - cz) / rz) ** 2, 0, 1))
    axis = np.asarray(knee) - hip
    parameter = np.clip(((posed[:, 1:] - hip[1:]) @ axis[1:]) / max(1e-8, axis[1:] @ axis[1:]), 0, 1)
    center = hip + parameter[:, None] * axis
    radius = .105 * (1 - parameter) + .060 * parameter
    distance = np.linalg.norm(posed[:, 1:] - center[:, 1:], axis=1)
    muscle_x = side * center[:, 0] + np.sqrt(np.maximum(0, radius ** 2 - distance ** 2))
    muscle_x = np.where(distance < radius, muscle_x, 0)
    bridge = np.clip(1 - np.abs(body_x - muscle_x) / .055, 0, 1)
    envelope = np.maximum(body_x, muscle_x) + bridge ** 2 * .055 / 4
    mask = smoothstep(.065, .155, side * rest[:, 0])
    mask *= smoothstep(.33, .46, rest[:, 2]) * (1 - smoothstep(.70, .79, rest[:, 2]))
    mask *= smoothstep(.015, .10, rest[:, 1]) * (1 - smoothstep(.38, .48, rest[:, 1]))
    displacement = np.zeros_like(posed)
    displacement[:, 0] = side * np.clip(envelope - side * posed[:, 0], 0, .070) * mask
    return displacement
