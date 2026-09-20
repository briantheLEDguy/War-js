"""Local anatomical planes on the authored continuous skin; no added proxy parts."""
import math


def deer_face_position(position, eye):
    x, y, z = position
    if y > -.52 or z < .88:
        return (x, y, z)
    def field(cy, cz, ry, rz):
        return math.exp(-((y - cy) / ry) ** 2 - ((z - cz) / rz) ** 2)
    side = min(1, abs(x) / .04)
    # The orbit sits above a distinct cheek plane; the tear-duct depression
    # and nasal bridge break the featureless conical head without a skin seam.
    orbit = .0065 * field(eye[1] + .006, eye[2] + .015, .040, .023)
    cheek = .011 * field(eye[1] + .028, eye[2] - .061, .042, .038)
    duct = -.0045 * field(eye[1] - .026, eye[2] - .007, .019, .016)
    nasal = -.0025 * field(-.721, 1.048, .044, .028)
    return (x + (1 if x >= 0 else -1) * (orbit + cheek + duct + nasal) * side, y, z)
