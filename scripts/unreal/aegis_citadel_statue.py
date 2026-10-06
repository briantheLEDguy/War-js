"""Original carved sentinel proposal; independent of the active citadel recipe.

Geometry uses centimetres and the existing Mesh serialization/material contract.
The 780 cm sculpture retains the original GLB's effective node scale, base origin
and placement orientation. Integration and native visual/collision approval are
separate: running this file only writes ignored CPU-review artifacts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from aegis_citadel_mesh import MATERIALS, Mesh, cross


LEGACY_NODE_SCALE = 0.6725854277610779
NOMINAL_ENVELOPE_CM = (400.0, 400.0, 780.0)
LEGACY_NOMINAL_FOOT_CM = 135.0
SCULPT_FOOT_CM = 63.0
SCULPT_PLINTH_TOP_CM = 62.0
STONE = 'carved_stone'


def _add(a, b): return [a[i] + b[i] for i in range(3)]
def _sub(a, b): return [a[i] - b[i] for i in range(3)]
def _mul(a, s): return [v * s for v in a]
def _unit(a):
    length = math.sqrt(sum(v * v for v in a))
    if length < 1e-10: raise ValueError('A sculpture surface has no normal.')
    return [v / length for v in a]


class Sculpture(Mesh):
    """Area-weighted patch normals preserve curved carving and hard plate seams."""
    def __init__(self):
        super().__init__('aegis_original_carved_sentinel', collision=True)
        self.parts = []

    def surface(self, name, rows, material=STONE, flip=False, uv_scale=(1.0, 1.0)):
        height, width = len(rows), len(rows[0])
        if height < 2 or width < 2 or any(len(row) != width for row in rows):
            raise ValueError('Surface grid must be rectangular.')
        positions = [p for row in rows for p in row]
        normals = [[0.0, 0.0, 0.0] for _ in positions]
        triangles = []
        for v in range(height - 1):
            for u in range(width - 1):
                a, b = v * width + u, v * width + u + 1
                c, d = (v + 1) * width + u + 1, (v + 1) * width + u
                for ids in ((a, b, c), (a, c, d)):
                    if flip: ids = tuple(reversed(ids))
                    n = cross(_sub(positions[ids[1]], positions[ids[0]]),
                              _sub(positions[ids[2]], positions[ids[0]]))
                    if sum(q * q for q in n) < 1e-12:
                        raise ValueError(f'Degenerate triangle in {name}.')
                    triangles.append(ids)
                    for index in ids: normals[index] = _add(normals[index], n)
        # A duplicated UV seam has one smooth normal, without merging UV islands.
        groups = {}
        for i, p in enumerate(positions):
            groups.setdefault(tuple(round(q, 7) for q in p), []).append(i)
        for group in groups.values():
            n = _unit([sum(normals[i][j] for i in group) for j in range(3)])
            for i in group: normals[i] = n[:]
        start = len(self.positions)
        self.positions.extend(positions)
        self.normals.extend(normals)
        self.uvs.extend([[u / (width - 1) * uv_scale[0], v / (height - 1) * uv_scale[1]]
                         for v in range(height) for u in range(width)])
        self.indices.extend(start + i for ids in triangles for i in ids)
        self.triangle_materials.extend([MATERIALS.index(material)] * len(triangles))
        self.parts.append(dict(name=name, triangles=len(triangles), material=material))

    def cap(self, name, ring, material=STONE, reverse=False):
        before = len(self.indices)
        ring = list(reversed(ring)) if reverse else ring
        for i in range(1, len(ring) - 1):
            points = [ring[0], ring[i], ring[i + 1]]
            n = _unit(cross(_sub(points[1], points[0]), _sub(points[2], points[0])))
            axis = max(range(3), key=lambda k: abs(n[k]))
            uv_axes = [k for k in range(3) if k != axis]
            start = len(self.positions)
            self.positions.extend([p[:] for p in points])
            self.normals.extend([n[:]] * 3)
            self.uvs.extend([[p[k] / 100 for k in uv_axes] for p in points])
            self.indices.extend([start, start + 1, start + 2])
            self.triangle_materials.append(MATERIALS.index(material))
        self.parts.append(dict(name=name, triangles=(len(self.indices) - before) // 3,
                               material=material))


def _interpolate(profiles, subdivisions=3):
    result = []
    for a, b in zip(profiles, profiles[1:]):
        for i in range(subdivisions):
            t = i / subdivisions
            eased = (1 - math.cos(math.pi * t)) / 2
            result.append([a[j] + (b[j] - a[j]) * (t if j == 2 else eased)
                           for j in range(len(a))])
    return result + [list(profiles[-1])]


def _loft(mesh, name, profiles, segments=40, subdivisions=3, material=STONE,
          exponent=1.0, front_ridge=0.0, caps=True):
    """Tailored sections, rather than spheres, shape anatomical armor volumes.

    Profiles are center X/Y/Z and lateral/depth radii; a superellipse makes plate
    sections gently planar, while the narrow front ridge carves a breast/greave.
    """
    segments = max(12, round(segments * 0.70))
    subdivisions = max(1, round(subdivisions * 0.75))
    rows = []
    for x, y, z, rx, ry in _interpolate(profiles, subdivisions):
        row = []
        for i in range(segments + 1):
            angle = math.tau * i / segments
            c, s = math.cos(angle), math.sin(angle)
            c = math.copysign(abs(c) ** exponent, c)
            s = math.copysign(abs(s) ** exponent, s)
            row.append([x + rx * c, y + ry * s - front_ridge * max(0, -s) ** 16, z])
        rows.append(row)
    mesh.surface(name, rows, material, uv_scale=(2.0, 2.0))
    if caps:
        mesh.cap(name + '_sole', rows[0][:-1], material, reverse=True)
        mesh.cap(name + '_crown', rows[-1][:-1], material)


def _catmull(points, steps):
    result = []
    for i in range(len(points) - 1):
        a, b = points[max(0, i - 1)], points[i]
        c, d = points[i + 1], points[min(len(points) - 1, i + 2)]
        for j in range(steps):
            t = j / steps
            result.append([0.5 * ((2 * b[k]) + (-a[k] + c[k]) * t +
                                  (2 * a[k] - 5 * b[k] + 4 * c[k] - d[k]) * t * t +
                                  (-a[k] + 3 * b[k] - 3 * c[k] + d[k]) * t ** 3)
                           for k in range(3)])
    return result + [list(points[-1])]


def _sweep(mesh, name, points, radii, material=STONE, segments=16, steps=3,
           exponent=0.8):
    segments = max(6, round(segments * 0.70))
    steps = max(1, round(steps * 0.75))
    centers = _catmull(points, steps)
    rows = []
    previous_u = None
    for i, p in enumerate(centers):
        tangent = _unit(_sub(centers[min(i + 1, len(centers) - 1)], centers[max(0, i - 1)]))
        reference = previous_u if previous_u is not None else (
            [1, 0, 0] if abs(tangent[0]) < 0.85 else [0, 0, 1])
        projected = _sub(reference, _mul(tangent, sum(reference[k] * tangent[k] for k in range(3))))
        if sum(q * q for q in projected) < 1e-8:
            reference = [0, 0, 1] if abs(tangent[2]) < 0.85 else [1, 0, 0]
            projected = _sub(reference, _mul(tangent, sum(reference[k] * tangent[k] for k in range(3))))
        u = _unit(projected)
        previous_u = u
        v = cross(tangent, u)
        f = i / (len(centers) - 1) * (len(radii) - 1)
        j, t = min(int(f), len(radii) - 2), f - min(int(f), len(radii) - 2)
        rx, ry = [radii[j][k] * (1 - t) + radii[j + 1][k] * t for k in range(2)]
        row = []
        for q in range(segments + 1):
            angle = math.tau * q / segments
            c, s = math.cos(angle), math.sin(angle)
            c, s = math.copysign(abs(c) ** exponent, c), math.copysign(abs(s) ** exponent, s)
            row.append(_add(p, _add(_mul(u, rx * c), _mul(v, ry * s))))
        rows.append(row)
    mesh.surface(name, rows, material, uv_scale=(1.0, max(1.0, len(centers) / 16)))
    mesh.cap(name + '_start', rows[0][:-1], material, reverse=True)
    mesh.cap(name + '_end', rows[-1][:-1], material)


def _plate(mesh, name, center, width, height, depth, segments=28, levels=14,
           point=0.0, material=STONE):
    """Convex front carving with a tapered, pointed lower armor edge."""
    segments, levels = max(2, round(segments * 0.70)), max(2, round(levels * 0.65))
    x, y, z = center
    rows = []
    for j in range(levels + 1):
        v = j / levels
        taper = 1 - point * (1 - v) ** 3
        row = []
        for i in range(segments + 1):
            u = i / segments * 2 - 1
            row.append([x + u * width / 2 * taper,
                        y - depth * (1 - u * u) * math.sin(math.pi * (0.13 + v * 0.75)),
                        z + (v - 0.5) * height + point * 12 * u * u * (1 - v)])
        rows.append(row)
    mesh.surface(name, rows, material)
    # The carved plate has thickness, rather than a visible paper-thin plane.
    mesh.surface(name + '_inner', [[[p[0], p[1] + 6, p[2]] for p in row] for row in rows],
                 material, flip=True)
    for label, edge in (('left', [row[0] for row in rows]), ('right', [row[-1] for row in rows]),
                        ('bottom', rows[0]), ('top', rows[-1])):
        mesh.surface(name + '_' + label,
                     [edge, [[p[0], p[1] + 6, p[2]] for p in edge]], material,
                     flip=label in ('right', 'bottom'))


def _sun(mesh, name, center, radius, material=STONE):
    """Raised carved orb and alternating pointed rays; no letter/icon placeholder."""
    x, y, z = center
    profiles = [(radius * 0.48, 2), (radius * 0.50, 5), (radius * 0.39, 9),
                (radius * 0.20, 12), (radius * 0.025, 13)]
    rows = [[[x + r * math.cos(a), y - depth, z + r * math.sin(a)]
             for a in [math.tau * i / 48 for i in range(49)]] for r, depth in profiles]
    # Radius descends while the relief moves forward: preserve the outward face.
    mesh.surface(name + '_orb', rows, material)
    mesh.cap(name + '_orb_center', rows[-1][:-1], material)
    for i in range(16):
        a = math.tau * i / 16
        inner, outer = radius * 0.64, radius * (1 if i % 2 == 0 else 0.82)
        points = [[x + inner * math.cos(a - 0.095), y - 2, z + inner * math.sin(a - 0.095)],
                  [x + outer * math.cos(a + 0.035), y - 4, z + outer * math.sin(a + 0.035)],
                  [x + inner * math.cos(a + 0.095), y - 2, z + inner * math.sin(a + 0.095)],
                  [x + radius * 0.73 * math.cos(a), y - 8, z + radius * 0.73 * math.sin(a)]]
        for j in range(3): mesh.cap(name + '_ray', [points[j], points[(j + 1) % 3], points[3]], material)
    for r in (radius * 0.55, radius * 0.58):
        path = [[x + r * math.cos(math.tau * i / 24), y - 2, z + r * math.sin(math.tau * i / 24)]
                for i in range(25)]
        _sweep(mesh, name + '_engraved_ring', path, [(1.5, 1.2)] * len(path),
               material, segments=6, steps=1, exponent=1)


def _armor(mesh):
    # Weight rests on the left leg; the slightly advanced right boot and lowered
    # sword hand give a quiet ceremonial stance without a symmetrical mannequin.
    for side in (-1, 1):
        x, y = side * 77, -15 if side == 1 else 4
        _loft(mesh, f'{side}_articulated_sabatons',
              [(x, y - 35, 63, 51, 88), (x, y - 38, 72, 53, 91),
               (x, y - 28, 94, 49, 79), (x, y - 7, 112, 38, 48),
               (x, y, 141, 30, 29)], segments=40, subdivisions=2, exponent=0.68)
        for j in range(4):
            rows = []
            for v in range(4):
                t = v / 3
                rows.append([[x + u * (43 - j * 4), y - 98 + j * 19 + t * 15,
                              88 + j * 8 + 10 * (1 - u * u) + t * 4]
                             for u in [i / 8 * 2 - 1 for i in range(9)]])
            mesh.surface(f'{side}_sabatons_overlap_{j}', rows)
            mesh.surface(f'{side}_sabatons_overlap_edge_{j}',
                         [rows[0], [[p[0], p[1], p[2] - 3] for p in rows[0]]])
        _loft(mesh, f'{side}_anatomical_greave',
              [(x, y, 132, 28, 29), (x, y, 158, 31, 35),
               (x - side * 3, y + 3, 207, 38, 44),
               (x - side * 8, y + 6, 261, 43, 42),
               (x - side * 10, y + 7, 283, 41, 38)], exponent=0.75,
              front_ridge=8, segments=40, subdivisions=3)
        _sweep(mesh, f'{side}_greave_carved_rib',
               [(x, y - 34, 143), (x - side * 2, y - 49, 204), (x - side * 8, y - 43, 265)],
               [(2.2, 2.8), (3.3, 3), (2.2, 2.5)], segments=8, steps=5)
        _loft(mesh, f'{side}_knee_joint',
              [(x - side * 10, y + 7, 269, 34, 34),
               (x - side * 11, y + 8, 292, 38, 37),
               (x - side * 11, y + 8, 311, 35, 35)], segments=28, subdivisions=2)
        _plate(mesh, f'{side}_pointed_poleyn', (x - side * 10, y - 33, 293),
               98, 95, 23, point=0.45, segments=30, levels=16)
        _plate(mesh, f'{side}_knee_wing', (x + side * 31, y - 20, 296),
               50, 68, 8, point=0.68, segments=18, levels=8)
        _loft(mesh, f'{side}_cuisses',
              [(x - side * 11, y + 7, 307, 39, 38),
               (x - side * 14, y + 12, 338, 47, 46),
               (x - side * 17, y + 15, 381, 50, 50),
               (x - side * 20, y + 17, 420, 46, 43)], segments=40, subdivisions=3,
              exponent=0.8, front_ridge=5)
    _loft(mesh, 'tailored_cuirass',
          [(0, 9, 421, 82, 55), (0, 6, 453, 88, 56), (0, 2, 491, 110, 65),
           (0, 0, 530, 125, 70), (0, 5, 571, 130, 70), (0, 8, 606, 116, 58),
           (0, 11, 626, 90, 44)], exponent=0.8, front_ridge=12,
          segments=48, subdivisions=3)
    for side in (-1, 1):
        _sweep(mesh, f'{side}_breastplate_fluted_crease',
               [(side * 37, -52, 450), (side * 58, -67, 481),
                (side * 79, -76, 534), (side * 71, -61, 577)],
               [(1.8, 1.2), (2.5, 1.5), (2.5, 1.5), (1.8, 1.2)], segments=8, steps=4)
        _sweep(mesh, f'{side}_cuirass_upper_engraved_arch',
               [(side * 7, -76, 591), (side * 32, -74, 592),
                (side * 66, -67, 583), (side * 89, -56, 565)],
               [(1.6, 1.3)] * 4, segments=8, steps=4)
    _sweep(mesh, 'cuirass_sculpted_sternum_ridge',
           [(0, -70, 467), (0, -85, 513), (0, -89, 567), (0, -74, 590)],
           [(1.9, 1.9), (3, 2.8), (3, 2.8), (1.8, 1.8)], segments=8, steps=4)
    for j in range(4):
        z = 404 + j * 16
        _loft(mesh, f'scalloped_fauld_lame_{j}',
              [(0, 11, z - 10, 105 - j * 5, 68 - j * 3),
               (0, 10, z, 107 - j * 5, 70 - j * 3),
               (0, 9, z + 8, 100 - j * 5, 64 - j * 3)],
              segments=48, subdivisions=1, exponent=0.75)
    for side in (-1, 1):
        for j in range(4):
            _plate(mesh, f'{side}_layered_tasset_{j}',
                   (side * 57, -57 - j * 4, 409 - j * 20),
                   90 - j * 3, 36, 8, point=0.18 + j * 0.1,
                   segments=24, levels=4)
    _sun(mesh, 'breastplate_sun_seal', (0, -87, 547), 22)


def _arms(mesh):
    for side in (-1, 1):
        shoulder = (side * 123, 14, 602)
        elbow = (side * (153 if side == 1 else 149), -1, 504)
        wrist = (side * (132 if side == 1 else 129), -51, 451 if side == 1 else 474)
        _sweep(mesh, f'{side}_upper_arm_anatomy',
               [shoulder, (side * 143, 12, 557), elbow],
               [(31, 35), (37, 33), (28, 27)], segments=28, steps=4)
        _sweep(mesh, f'{side}_vambrace',
               [elbow, (side * 145, -28, 477 if side == 1 else 490), wrist],
               [(29, 31), (32, 30), (21, 23)], segments=28, steps=4)
        _plate(mesh, f'{side}_elbow_couter', (elbow[0], elbow[1] - 28, elbow[2]),
               70, 71, 13, point=0.65, segments=24, levels=8)
        # Four overlapping shoulder plates are broad and swept down the arm;
        # their flattened arch never reads as the old spherical pauldrons.
        for j in range(4):
            rows = []
            for v in range(7):
                t = v / 6
                row = []
                for i in range(23):
                    angle = -math.pi * 0.93 + math.pi * 0.86 * i / 22
                    r = 53 - j * 4 + 4 * math.sin(math.pi * t)
                    row.append([side * (128 + j * 9 + r * math.cos(angle) * 0.5),
                                13 + r * math.sin(angle),
                                635 - j * 19 - t * 27 + 11 * math.cos(angle)])
                rows.append(row)
            mesh.surface(f'{side}_swept_pauldron_lame_{j}', rows, flip=side == 1)
            mesh.surface(f'{side}_pauldron_inner_{j}',
                         [[[p[0], p[1] + 4, p[2] - 4] for p in row] for row in rows],
                         flip=side == -1)
            for label, edge in (('upper', rows[0]), ('lower', rows[-1])):
                _sweep(mesh, f'{side}_pauldron_{label}_carved_rim_{j}', edge,
                       [(2.0, 1.7)] * len(edge), segments=6, steps=1)
        _loft(mesh, f'{side}_gauntlet_cuff',
              [(wrist[0], wrist[1], wrist[2] - 5, 24, 24),
               (wrist[0], wrist[1], wrist[2] + 18, 28, 27),
               (wrist[0], wrist[1], wrist[2] + 30, 30, 28)],
              segments=24, subdivisions=2, exponent=0.72)
        palm_z = wrist[2] - 9
        _loft(mesh, f'{side}_shaped_palm',
              [(wrist[0], -66, palm_z - 21, 20, 15),
               (wrist[0], -67, palm_z - 6, 26, 17),
               (wrist[0], -65, palm_z + 14, 25, 16)],
              segments=24, subdivisions=2, exponent=0.7)
        for finger in range(4):
            x = wrist[0] - 19 + finger * 12
            z = palm_z + 11 - abs(finger - 1.5) * 2
            _sweep(mesh, f'{side}_articulated_finger_{finger}',
                   [(x, -78, z), (x, -93, z - 5), (x, -94, z - 19), (x, -82, z - 25)],
                   [(5.8, 6.2), (6.2, 6.0), (5.2, 5.1), (3.9, 4.2)],
                   segments=12, steps=3)
            for joint, depth, level in ((0, -87, z - 2), (1, -97, z - 13)):
                _plate(mesh, f'{side}_finger_knuckle_{finger}_{joint}', (x, depth, level),
                       11, 10, 2, segments=8, levels=3)
        _sweep(mesh, f'{side}_opposed_thumb',
               [(wrist[0] - side * 22, -68, palm_z - 4),
                (wrist[0] - side * 30, -85, palm_z - 10),
                (wrist[0] - side * 15, -93, palm_z - 20)],
               [(8, 9), (7, 8), (5, 6)], segments=12, steps=4)


def _helmet(mesh):
    _loft(mesh, 'neck_mail_core', [(0, 12, 612, 39, 35), (0, 8, 641, 43, 38),
                                  (0, 7, 668, 42, 37)], segments=32, subdivisions=3)
    _loft(mesh, 'sculpted_gorget', [(0, 8, 625, 79, 51), (0, 8, 634, 84, 56),
                                 (0, 8, 644, 66, 44), (0, 7, 657, 50, 39)],
          segments=48, subdivisions=2, exponent=0.75, front_ridge=5)
    _loft(mesh, 'closed_helm_bevor',
          [(0, 9, 655, 28, 29), (0, 6, 671, 36, 35), (0, 2, 690, 43, 42),
           (0, 2, 705, 46, 44)], segments=40, subdivisions=3, exponent=0.70,
          front_ridge=19)
    _loft(mesh, 'sculpted_helmet_calotte',
          [(0, 2, 715, 49, 46), (0, 4, 729, 48, 44), (0, 6, 747, 40, 36),
           (0, 9, 763, 28, 26), (0, 11, 775, 12, 14), (0, 11, 780, 1.5, 2)],
          segments=40, subdivisions=3, exponent=0.78, front_ridge=10)
    closed_back = []
    for v in range(4):
        t = v / 3
        closed_back.append([[(46 + 3 * t) * math.copysign(abs(math.cos(a)) ** 0.75, math.cos(a)),
                             2 + (44 + 2 * t) * math.copysign(abs(math.sin(a)) ** 0.75, math.sin(a)),
                             704 + t * 13]
                            for a in [-math.pi * 0.13 + math.pi * 1.26 * i / 24 for i in range(25)]])
    mesh.surface('closed_helmet_back_and_hinges', closed_back)
    # The visor is an actual recessed slit between the two carved shell pieces.
    # Two angled brows and a tapered nose bridge give a sculpted enclosed face.
    _plate(mesh, 'recessed_visor_shadow', (0, -45, 710), 82, 9, 0.8,
           segments=24, levels=2, material='window_dark')
    for side in (-1, 1):
        _sweep(mesh, f'{side}_helmet_brow',
               [(side * 4, -58, 716), (side * 24, -56, 714.5), (side * 40, -47, 715)],
               [(3.8, 2.2), (3.8, 2.5), (3, 2.2)], segments=8, steps=4)
    _plate(mesh, 'pointed_nasal_bridge', (0, -63, 704), 12, 31, 5,
           point=0.6, segments=12, levels=8)
    _sweep(mesh, 'helmet_sagittal_carving',
           [(0, -53, 724), (0, -34, 749), (0, -12, 772), (0, 14, 778),
            (0, 34, 756), (0, 48, 727)],
           [(2.2, 2.4)] * 6, segments=8, steps=4)


def _cloak(mesh):
    rows = []
    for j in range(21):
        v = j / 20
        width = 168 * (1 - v) + 127 * v
        row = []
        for i in range(41):
            u = i / 40 * 2 - 1
            folds = 12 * math.sin(6 * math.pi * u + v * 0.65) + 5 * math.sin(11 * math.pi * u - v)
            y = 110 - v * 29 + folds * (0.6 + 0.4 * (1 - v)) + 15 * abs(u) ** 6
            hem = 89 + 25 * (1 - u * u) + 9 * math.sin(3 * math.pi * u)
            z = hem * (1 - v) + (635 - 45 * abs(u) ** 3) * v
            row.append([u * width, y, z])
        rows.append(row)
    mesh.surface('weighted_cloak_deep_folds', rows, flip=True, uv_scale=(3, 5))
    mesh.surface('cloak_inner_carved_surface',
                 [[[p[0], p[1] - 5, p[2]] for p in row] for row in rows], uv_scale=(3, 5))
    for label, edge in (('hem', rows[0]), ('left', [row[0] for row in rows]),
                        ('right', [row[-1] for row in rows])):
        mesh.surface('cloak_' + label + '_thickness',
                     [edge, [[p[0], p[1] - 5, p[2]] for p in edge]], flip=label != 'right')
        _sweep(mesh, 'cloak_' + label + '_worked_border', edge,
               [(2.1, 1.6)] * len(edge), segments=6, steps=1)
    for side in (-1, 1):
        drape = []
        for j in range(13):
            v = j / 12
            drape.append([[side * (121 - 45 * v + u * 16),
                           76 - 115 * v + 4 * math.sin(math.pi * 3 * u) * math.sin(math.pi * v),
                           604 + 42 * math.sin(math.pi * v) + 19 * v - 7 * u * u]
                          for u in [i / 10 * 2 - 1 for i in range(11)]])
        mesh.surface(f'{side}_mantle_return_folds', drape, flip=side == 1)
        mesh.surface(f'{side}_mantle_inner',
                     [[[p[0], p[1], p[2] - 4] for p in row] for row in drape], flip=side == -1)
        _sweep(mesh, f'{side}_mantle_worked_border', [row[0] for row in drape],
               [(1.6, 1.4)] * len(drape), segments=6, steps=1)
    _sun(mesh, 'mantle_sun_clasp', (0, -53, 625), 16)


def _shield_and_sword(mesh):
    x, y, z = -112, -104, 398
    outline = [(-76, 151), (-82, 108), (-78, 40), (-61, -38), (-28, -116),
               (0, -153), (28, -116), (61, -38), (78, 40), (82, 108), (76, 151)]
    # A convex kite face is built from nested contours, with independent rim and
    # a real thick reverse. The grip sits behind it; the fingers are not floating.
    center = [x, y - 15, z + 18]
    contours = []
    for level in range(1, 13):
        t = level / 12
        contours.append([[center[0] + u * t, y - 15 * (1 - t * t), center[2] + (v - 18) * t]
                         for u, v in outline + [outline[0]]])
    mesh.surface('convex_carved_kite_shield', contours, flip=True, uv_scale=(1.5, 2.5))
    mesh.cap('shield_center', contours[0][:-1], reverse=True)
    edge = contours[-1]
    back = [[p[0], y + 10, p[2]] for p in edge]
    mesh.surface('shield_beveled_edge', [edge, back])
    mesh.cap('shield_reverse', back[:-1])
    for inset in (1, 0.94):
        rim = [[x + u * inset, y - 3 if inset == 1 else y - 5, z + v * inset]
               for u, v in outline + [outline[0]]]
        _sweep(mesh, 'shield_engraved_border', rim, [(3, 2)] * len(rim),
               segments=8, steps=3)
    _sun(mesh, 'shield_carved_sun_heraldry', (x, y - 14, z + 40), 47)
    for side in (-1, 1):
        _sweep(mesh, 'shield_lower_tracery',
               [(x + side * 38, y - 9, z - 26), (x + side * 24, y - 9, z - 76),
                (x, y - 7, z - 120)], [(1.9, 1.3)] * 3, segments=8, steps=4)
    # A down-pointing ceremonial sword: faceted fuller, shaped quillons, leather
    # wraps carved in stone and a small sun pommel. Its tip is grounded at the base.
    sx, sy = 132, -87
    blade_levels = [(78, 1.5), (100, 6), (172, 12), (350, 16), (416, 18), (431, 17)]
    for side in (-1, 1):
        rows = []
        for height, width in blade_levels:
            rows.append([[sx - width, sy, height], [sx - width * 0.65, sy + side * 2.5, height],
                         [sx, sy + side * 5, height], [sx + width * 0.65, sy + side * 2.5, height],
                         [sx + width, sy, height]])
        for stripe in range(4):
            mesh.surface('sword_' + ('front' if side == -1 else 'back') + '_fuller',
                         [[row[stripe], row[stripe + 1]] for row in rows],
                         flip=side == 1, uv_scale=(0.25, 2))
    _sweep(mesh, 'sword_swept_crossguard',
           [(sx - 52, sy + 1, 413), (sx - 37, sy, 424), (sx, sy, 430),
            (sx + 37, sy, 424), (sx + 52, sy + 1, 413)],
           [(5.5, 6), (6, 7), (8, 8), (6, 7), (5.5, 6)], segments=12, steps=4)
    _loft(mesh, 'sword_grip', [(sx, sy, 430, 7, 8), (sx, sy, 494, 7, 8),
                            (sx, sy, 502, 9, 9)], segments=16, subdivisions=2)
    for i in range(7):
        points = [[sx + 8 * math.cos(a), sy + 9 * math.sin(a), 438 + i * 8 + a / math.tau * 5]
                  for a in [math.tau * q / 16 for q in range(17)]]
        _sweep(mesh, 'sword_grip_carved_wrap', points, [(1.2, 1.0)] * len(points),
               segments=6, steps=1)
    _loft(mesh, 'sword_sculpted_pommel', [(sx, sy, 501, 7, 8), (sx, sy, 513, 15, 12),
                                      (sx, sy, 526, 11, 9), (sx, sy, 531, 3, 4)],
          segments=24, subdivisions=2, exponent=0.78)


def build_sentinel(scale=1.0):
    """Return the nominal local sculpture; use LEGACY_NODE_SCALE when flattening.

    Internal sculpting axes are lateral X, rear Y, up Z. The final rotation makes
    its face point toward native -X, as the current citadel furnishing import does.
    Review GLB export retains the old node scale. Caller placement/scale, pedestal,
    routes and collision contracts are untouched by this independent proposal.
    """
    if not math.isfinite(scale) or scale <= 0: raise ValueError('Statue scale must be positive and finite.')
    mesh = Sculpture()
    _loft(mesh, 'octagonal_carved_foot_plinth',
          [(0, 0, 0, 195, 195), (0, 0, 9, 200, 200), (0, 0, 25, 200, 200),
           (0, 0, 32, 185, 185), (0, 0, 49, 185, 185), (0, 0, 62, 177, 177)],
          segments=64, subdivisions=1, exponent=0.72)
    _armor(mesh)
    _cloak(mesh)
    _arms(mesh)
    _helmet(mesh)
    _shield_and_sword(mesh)
    source_top = max(p[2] for p in mesh.positions)
    normalization = NOMINAL_ENVELOPE_CM[2] / source_top
    body_scale = (NOMINAL_ENVELOPE_CM[2] - LEGACY_NOMINAL_FOOT_CM) / (source_top - SCULPT_FOOT_CM)
    base_scale = LEGACY_NOMINAL_FOOT_CM / SCULPT_PLINTH_TOP_CM
    positions, normals = [], []
    for p, n in zip(mesh.positions, mesh.normals):
        if p[2] >= SCULPT_FOOT_CM:
            z = LEGACY_NOMINAL_FOOT_CM + (p[2] - SCULPT_FOOT_CM) * body_scale
            vertical_scale = body_scale
        elif p[2] <= SCULPT_PLINTH_TOP_CM:
            z = p[2] * base_scale
            vertical_scale = base_scale
        else:
            raise ValueError('A sculpture component crosses the separate foot/plinth remap seam.')
        # Inverse-transpose transforms the authored surface normals, preserving
        # both smooth carving and independent plate seams under the vertical fit.
        transformed = _unit([n[0] / normalization, n[1] / normalization, n[2] / vertical_scale])
        positions.append([p[1] * scale * normalization, -p[0] * scale * normalization, z * scale])
        normals.append([transformed[1], -transformed[0], transformed[2]])
    mesh.positions, mesh.normals = positions, normals
    mesh.foot_fit = dict(nominalStandingPlaneCm=LEGACY_NOMINAL_FOOT_CM,
                         sourceSculptStandingPlaneCm=SCULPT_FOOT_CM,
                         sourceSculptPlinthTopCm=SCULPT_PLINTH_TOP_CM,
                         nominalTopCm=NOMINAL_ENVELOPE_CM[2], bodyVerticalScale=body_scale,
                         plinthVerticalScale=base_scale, horizontalScale=normalization,
                         outputScale=scale, normals='inverse_transpose_then_unit',
                         xyPreservedFromPreviousProposal=True)
    return mesh


def _original_foot_witness():
    """Read original iron boot vertices, independently of declared accessor bounds."""
    source = Path(__file__).resolve().parents[2] / 'public/assets/models/prop_aegis_citadel_oath_statue.glb'
    raw = source.read_bytes()
    magic, version, length = struct.unpack_from('<III', raw, 0)
    json_length, json_kind = struct.unpack_from('<II', raw, 12)
    if magic != 0x46546C67 or version != 2 or length != len(raw) or json_kind != 0x4E4F534A:
        raise ValueError('Original statue GLB identity is malformed.')
    document = json.loads(raw[20:20 + json_length])
    offset = 20 + json_length
    binary_length, binary_kind = struct.unpack_from('<II', raw, offset)
    if binary_kind != 0x004E4942: raise ValueError('Original statue GLB binary chunk missing.')
    binary = raw[offset + 8:offset + 8 + binary_length]
    if len(document['nodes']) != 1 or document['nodes'][0].get('scale') != [LEGACY_NODE_SCALE] * 3:
        raise ValueError('Original statue node scale drifted.')
    witnesses = []
    for mesh in document['meshes']:
        for primitive_index, primitive in enumerate(mesh['primitives']):
            if document['materials'][primitive['material']]['name'] != 'aegis_citadel_iron': continue
            accessor = document['accessors'][primitive['attributes']['POSITION']]
            view = document['bufferViews'][accessor['bufferView']]
            if accessor['componentType'] != 5126 or accessor['type'] != 'VEC3' or view['buffer'] != 0:
                raise ValueError('Original iron foot POSITION format changed.')
            start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            stride = view.get('byteStride', 12)
            points = [struct.unpack_from('<fff', binary, start + i * stride) for i in range(accessor['count'])]
            minimum = min(p[1] for p in points)
            feet = [p for p in points if abs(p[1] - minimum) < 1e-6]
            if abs(minimum * 100 - LEGACY_NOMINAL_FOOT_CM) > 0.001:
                raise ValueError('Original nominal boot standing plane changed.')
            witnesses.append(dict(primitive=primitive_index, material='aegis_citadel_iron',
                                   actualMinimumYMetres=minimum, footVertexCount=len(feet),
                                   uniqueFootPositionsMetres=[list(p) for p in sorted(set(feet))]))
    if len(witnesses) != 1: raise ValueError('Original boot primitive cannot be identified uniquely.')
    return dict(source=source.relative_to(Path(__file__).resolve().parents[2]).as_posix(),
                sourceSha256=hashlib.sha256(raw).hexdigest(), convention='glTF_Y_up_metres',
                nodeScale=LEGACY_NODE_SCALE, nominalStandingPlaneCm=LEGACY_NOMINAL_FOOT_CM,
                primitiveWitnesses=witnesses)


def _proposed_foot_witness(mesh):
    points = []
    offset = 0
    for part in mesh.parts:
        count = part['triangles'] * 3
        if 'articulated_sabatons' in part['name']:
            points.extend(mesh.positions[i] for i in mesh.indices[offset:offset + count])
        offset += count
    minimum = min(p[2] for p in points)
    feet = [p for p in points if abs(p[2] - minimum) < 1e-6]
    return dict(convention='native_Z_up_centimetres', actualMinimumZCm=minimum,
                uniqueFootPositionsCm=[list(p) for p in sorted(set(tuple(p) for p in feet))])


def sculpture_report(mesh):
    bounds = [[min(p[i] for p in mesh.positions), max(p[i] for p in mesh.positions)] for i in range(3)]
    material_triangles = {name: mesh.triangle_materials.count(i) for i, name in enumerate(MATERIALS)
                          if i in mesh.triangle_materials}
    data = mesh.export()
    encoded = json.dumps(data, sort_keys=True, separators=(',', ':')).encode('utf-8')
    return dict(schemaVersion=1, proposalOnly=True, sourceSha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                geometrySha256=hashlib.sha256(encoded).hexdigest(), triangles=len(mesh.indices) // 3,
                vertices=len(mesh.positions), boundsCm=bounds,
                dimensionsCm=[b - a for a, b in bounds], materialTriangles=material_triangles,
                legacyNodeScale=LEGACY_NODE_SCALE, nominalEnvelopeCm=list(NOMINAL_ENVELOPE_CM),
                reviewEffectiveDimensionsCm=[(b - a) * LEGACY_NODE_SCALE for a, b in bounds],
                standingPlaneFit=mesh.foot_fit, originalFootWitness=_original_foot_witness(),
                proposedFootWitness=_proposed_foot_witness(mesh),
                faceDirectionNative=[-1, 0, 0], baseOriginNative=[0, 0, 0], parts=mesh.parts,
                integrated=False, nativeCollisionVerified=False, visualApproved=False)


def _render_review(mesh, output):
    """Small genuine geometry renders; CPU Cycles only, no native application."""
    import bpy
    from mathutils import Vector
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 2
    scene.cycles.glossy_bounces = 2
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 2
    scene.render.resolution_x, scene.render.resolution_y = 640, 800
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new('CPU sculpture review world')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.075, 0.09, 0.12, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = 0.35
    scene.view_settings.view_transform = 'AgX'
    positions = [(p[1] / 100, -p[0] / 100, p[2] / 100) for p in mesh.positions]
    normals = [(n[1], -n[0], n[2]) for n in mesh.normals]
    faces = [tuple(mesh.indices[i:i + 3]) for i in range(0, len(mesh.indices), 3)]
    data = bpy.data.meshes.new('Original sentinel carved surfaces')
    data.from_pydata(positions, [], faces)
    data.update()
    data.uv_layers.new(name='Authored sculpture UV')
    for poly, material in zip(data.polygons, mesh.triangle_materials):
        poly.material_index = material
        poly.use_smooth = True
        for loop in poly.loop_indices:
            data.uv_layers[0].data[loop].uv = mesh.uvs[data.loops[loop].vertex_index]
    # Set smoothing before encoding custom normals; changing it afterwards can
    # reinterpret Blender's encoded loop normals and erase the sculpted seams.
    data.normals_split_custom_set_from_vertices(normals)
    data.calc_tangents(uvmap='Authored sculpture UV')
    tangent_audit = dict(method='Blender Mesh.calc_tangents / MikkTSpace', corners=len(data.loops),
                         nonFinite=0, zeroTangents=0, nonUnitTangents=0,
                         maximumNormalTangentDot=0.0, minimumSourceNormalDot=1.0,
                         invalidHandedness=0)
    for i, loop in enumerate(data.loops):
        actual_n = data.corner_normals[i].vector
        tangent = loop.tangent
        intended_n = Vector(normals[loop.vertex_index])
        values = list(actual_n) + list(tangent) + [loop.bitangent_sign]
        tangent_audit['nonFinite'] += int(not all(math.isfinite(q) for q in values))
        tangent_audit['zeroTangents'] += int(tangent.length < 1e-6)
        tangent_audit['nonUnitTangents'] += int(abs(tangent.length - 1) > 0.002)
        tangent_audit['maximumNormalTangentDot'] = max(tangent_audit['maximumNormalTangentDot'],
                                                       abs(actual_n.dot(tangent)))
        tangent_audit['minimumSourceNormalDot'] = min(tangent_audit['minimumSourceNormalDot'],
                                                      actual_n.dot(intended_n))
        tangent_audit['invalidHandedness'] += int(abs(abs(loop.bitangent_sign) - 1) > 1e-6)
    if (any(tangent_audit[k] for k in ('nonFinite', 'zeroTangents', 'nonUnitTangents', 'invalidHandedness')) or
            tangent_audit['maximumNormalTangentDot'] > 1e-4 or tangent_audit['minimumSourceNormalDot'] < 0.995):
        raise ValueError('Actual Blender authored-normal/Mikk basis audit failed: ' + json.dumps(tangent_audit))
    obj = bpy.data.objects.new('Original Bastion ceremonial sentinel', data)
    scene.collection.objects.link(obj)
    obj.scale = (LEGACY_NODE_SCALE,) * 3
    for name in MATERIALS:
        mat = bpy.data.materials.new(name)
        mat.use_nodes = True
        nodes, links = mat.node_tree.nodes, mat.node_tree.links
        bsdf = nodes.get('Principled BSDF')
        bsdf.inputs['Roughness'].default_value = 0.84
        base = (0.13, 0.145, 0.155, 1) if name != 'window_dark' else (0.018, 0.021, 0.024, 1)
        bsdf.inputs['Base Color'].default_value = base
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 28
        noise.inputs['Detail'].default_value = 3
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = 0.12
        bump.inputs['Distance'].default_value = 0.004
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
        data.materials.append(mat)
    # A broad flat ground is review context only, not part of the exported model.
    ground = bpy.data.meshes.new('Review ground')
    ground.from_pydata([(-20, -20, -0.015), (20, -20, -0.015), (20, 20, -0.015), (-20, 20, -0.015)], [], [(0, 1, 2, 3)])
    floor = bpy.data.objects.new('Review ground', ground)
    scene.collection.objects.link(floor)
    matte = bpy.data.materials.new('Review ground matte')
    matte.diffuse_color = (0.10, 0.12, 0.15, 1)
    ground.materials.append(matte)
    for name, point, energy, size in [('Key', (-4, 6, 9), 1100, 5), ('Fill', (5, 2, 5), 450, 4),
                                      ('Rim', (1, -5, 8), 1000, 3)]:
        light = bpy.data.lights.new(name, 'AREA')
        light.energy, light.shape, light.size = energy, 'DISK', size
        actor = bpy.data.objects.new(name, light)
        scene.collection.objects.link(actor)
        actor.location = point
        actor.rotation_euler = (Vector((0, 0, 3)) - actor.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data = bpy.data.cameras.new('Sculpture review camera')
    camera = bpy.data.objects.new('Sculpture review camera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    camera_data.lens = 65
    camera_data.clip_end = 100
    views = [('front', (0, 12.5, 4.2), (0, 0, 2.65)),
             ('three_quarter', (-8.2, 10.4, 4.8), (0, 0, 2.65)),
             ('rear', (6.7, -11.2, 4.4), (0, 0, 2.65)),
             ('armor_detail', (-3.1, 5.5, 4.5), (0, 0, 3.9))]
    for name, eye, target in views:
        camera.location = eye
        camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(output / (name + '.png'))
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'sentinel-proposal.blend'))
    for actor in scene.objects: actor.select_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    # The existing furnishing importer applies a -90-degree Z rotation before
    # native conversion. Retain its original source-facing -X orientation in the
    # GLB node; the saved review scene remains in the camera-facing review axes.
    obj.rotation_euler[2] = math.pi / 2
    bpy.ops.export_scene.gltf(filepath=str(output / 'sentinel-proposal.glb'), export_format='GLB',
                              use_selection=True, export_texcoords=True, export_normals=True,
                              export_materials='EXPORT')
    return dict(engine=scene.render.engine, device=scene.cycles.device, samples=scene.cycles.samples,
                threads=scene.render.threads, resolution=[scene.render.resolution_x, scene.render.resolution_y],
                views=[name for name, _, _ in views], gltfNodeScale=list(obj.scale),
                gltfSourceFaceDirectionBlender=[-1, 0, 0], gltfSourceRotationZDegrees=90,
                tangentAudit=tangent_audit)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    allowed = (root / 'artifacts' / 'unreal' / 'citadel-reference' / 'statue-proposal').resolve()
    if output != allowed and allowed not in output.parents:
        raise ValueError('Proposal artifacts must stay in the ignored statue-proposal directory.')
    output.mkdir(parents=True, exist_ok=True)
    mesh = build_sentinel()
    report = sculpture_report(mesh)
    (output / 'mesh.json').write_text(json.dumps(mesh.export(), separators=(',', ':')), encoding='utf-8')
    if args.render: report['cpuReview'] = _render_review(mesh, output)
    if hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != report['sourceSha256']:
        raise ValueError('Statue helper changed during rendering; no bound review receipt can be written.')
    report['files'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted(output.iterdir()) if p.is_file() and p.name != 'receipt.json'}
    (output / 'receipt.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('triangles', 'vertices', 'dimensionsCm', 'geometrySha256')}))


if __name__ == '__main__':
    import sys
    main(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
