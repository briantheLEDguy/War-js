"""Supported Gothic spire surfaces in final centimetres; no route authoring.

The caller supplies an upper-only mesh. Continuous flared slate skirts, inset
lancet dormers and slender metal arrises replace unarticulated roof pyramids.
Integration requires a new signed geometry revision and fresh native review.
"""
import math

from aegis_citadel_mesh import MATERIALS


def articulated_spire(mesh, x, y, bottom, peak, width):
    if not all(math.isfinite(v) for v in (x, y, bottom, peak, width)):
        raise ValueError('Spire dimensions must be finite')
    if bottom <= 9007 or peak-bottom < 800 or width < 300:
        raise ValueError('Detailed spires require an upper-only supported envelope')
    half, bevel, rise = width/2, width*.16, peak-bottom-110
    plan = [(-half+bevel, -half), (half-bevel, -half), (half, -half+bevel),
            (half, half-bevel), (half-bevel, half), (-half+bevel, half),
            (-half, half-bevel), (-half, -half+bevel)]
    profile = [(0, 1.035), (.06, 1), (.26, .73), (.79, .20), (1, .018)]
    rings = [[[x+u*scale, y+v*scale, bottom+alpha*rise] for u, v in plan]
             for alpha, scale in profile]
    for lower, upper in zip(rings, rings[1:]):
        for index in range(8):
            next_index = (index+1)%8
            corners = [lower[index], lower[next_index], upper[next_index], upper[index]]
            for triangle in (corners[:3], [corners[0], corners[2], corners[3]]):
                mesh.face(triangle, 'slate')
    mesh.face(list(reversed(rings[0])), 'slate')
    mesh.face(rings[-1], 'iron')
    # Individual seams follow every change of pitch; they do not bridge the
    # skirt with floating rods or introduce horizontal gold bands on the roof.
    for index in range(8):
        for lower, upper in zip(rings, rings[1:]):
            mesh.rod(lower[index], upper[index], 5, 'iron', 6)
    for index in range(8):
        mesh.rod(rings[0][index], rings[0][(index+1)%8], 7, 'iron', 6)
    mesh.rod([x, y, peak-110], [x, y, peak], 9, 'gold', 8)

    dormers = []
    for side in range(4):
        dormers.append(_dormer(mesh, x, y, bottom, rise, width, side))
    return dict(profile=[dict(riseFraction=a, widthFraction=s) for a, s in profile],
                bottomCm=bottom, peakCm=peak, widthCm=width,
                dormers=dormers, minimumZCm=bottom-7,
                maximumZCm=peak, maximumEnvelopeHalfWidthCm=half*1.035+8,
                freshNativeEvidenceRequired=True, visualApproval=False)


def _dormer(mesh, x, y, bottom, rise, width, side):
    from aegis_citadel_crown import _CrownMesh, _perforated_wall
    face_width = width*.28
    floor = bottom+rise*.075
    wall_height = min(360, rise*.17)
    # Back corners embed in the same slate skirt, making the dormer a supported
    # roof projection rather than a detached miniature tower.
    front, back = width*.40, width*.33
    local = _CrownMesh('spire_dormer')
    _perforated_wall(local, front, 0, floor, floor+wall_height,
                     face_width, 35,
                     [(0, floor+38, face_width*.55, wall_height*.72)],
                     applied_frames=False)
    ridge = [front+35, 0, floor+wall_height+face_width*.39]
    rear_ridge = [back, 0, ridge[2]]
    left = [front+35, -face_width/2-12, floor+wall_height]
    right = [front+35, face_width/2+12, floor+wall_height]
    local.face([left, right, ridge], 'limestone')
    for edge in (left, right):
        rear = [back, edge[1], edge[2]]
        # Triangulate each roof face after quantization, just like crown walls.
        local.face([edge, ridge, rear_ridge], 'slate')
        local.face([edge, rear_ridge, rear], 'slate')
        local.face([[front, edge[1], floor], edge, rear,
                    [back, edge[1], floor]], 'stone')
        local.rod(edge, ridge, 5, 'iron', 6)
    local.rod(ridge, rear_ridge, 5, 'iron', 6)
    # A recessed dark pane sits behind the actual pointed opening; the wall's
    # cut reveals remain three-dimensional and its front is never a painted bay.
    from aegis_citadel_mesh import pointed_profile
    pane = pointed_profile(face_width*.55, wall_height*.72)
    local.face([[front-12, u, floor+38+v] for u, v in pane], 'window_dark')
    angle = side*math.pi/2
    cosine, sine = math.cos(angle), math.sin(angle)
    for offset, material in enumerate(local.triangle_materials):
        corners = [local.positions[i] for i in local.indices[offset*3:offset*3+3]]
        mesh.face([[x+p[0]*cosine-p[1]*sine,
                    y+p[0]*sine+p[1]*cosine, p[2]] for p in corners], MATERIALS[material])
    return dict(side=side, floorCm=floor, wallHeightCm=wall_height,
                widthCm=face_width, pointedWindowWidthCm=face_width*.55,
                revealDepthCm=35, embeddedRearDistanceCm=back,
                outerDistanceCm=front+35, topCm=ridge[2])


def source_spire(mesh, x, y, final_bottom, final_peak, width):
    """Append final-sized roofs before the caller's existing upper transform."""
    from aegis_citadel_crown import _CrownMesh
    from aegis_citadel_mesh import upper_source_z
    local = _CrownMesh('articulated_source_roof')
    receipt = articulated_spire(local, x, y, final_bottom, final_peak, width)
    for offset, material in enumerate(local.triangle_materials):
        corners = [local.positions[i] for i in local.indices[offset*3:offset*3+3]]
        mesh.face([[p[0], p[1], upper_source_z(p[2])] for p in corners], MATERIALS[material])
    return receipt
