"""Upper keep crown, authored in final Unreal centimetres.

The architecture caller replaces the old owned crown and appends this module
after its upper-height transform. The source contract remains unapproved until
fresh native capture and collision evidence is recorded for its signed revision.
"""
import math
from dataclasses import asdict, dataclass

from aegis_citadel_mesh import Mesh, MATERIALS, arch, pointed_profile

PRESERVED_Z_CM = 9000
MAXIMUM_Z_CM = 17200
ENVELOPE_CM = ((27060, -3950, 9100), (33010, 3950, MAXIMUM_Z_CM))


@dataclass(frozen=True)
class Belfry:
    id: str
    x0: float
    x1: float
    y: float
    width: float
    bottom: float
    eaves: float
    ridge: float


# Broad paired wings advance toward the courtyard. The tallest central mass
# rises behind them; substantial masonry, rather than loose needles, joins them.
BELFRIES = (
    Belfry('west_belfry', 27350, 30650, -2610, 1700, 10100, 11850, 12550),
    Belfry('central_belfry', 28350, 32750, 0, 3440, 10200, 13150, 14000),
    Belfry('east_belfry', 27750, 31050, 2610, 1700, 10100, 11930, 12860),
)
TOWER_PEAKS_CM = {'west_belfry': (15780, 15150),
                  'central_belfry': (16680, 16150),
                  'east_belfry': (15480, 14880)}


def front_lancets(body):
    """A dominant central traceried bay flanked by smaller, higher-set lancets."""
    if body.id == 'central_belfry':
        return [(body.y-1120, body.bottom+280, 520, 2080),
                (body.y, body.bottom+110, 1240, 2670),
                (body.y+1120, body.bottom+280, 520, 2080)]
    height = body.eaves-body.bottom-380
    return [(body.y+offset, body.bottom+155, 485, height) for offset in (-410, 410)]


class _CrownMesh(Mesh):
    def face(self, vertices, material='stone'):
        # Chamfered helper quads can twist slightly. Author each actual triangle
        # after coordinate quantization so its supplied normal follows its plane.
        corners = [[round(v, 4) for v in point] for point in vertices]
        for index in range(1, len(corners)-1):
            super().face([corners[0], corners[index], corners[index+1]], material)


def _half_width(profile, height):
    """Interpolate the same signed Gothic outline used by the carved frame."""
    left = [(z, -u) for u, z in profile if u <= 1e-6]
    left = sorted(set((round(z, 4), max(0, round(w, 4))) for z, w in left))
    if height <= left[0][0]:
        return left[0][1]
    for (z0, w0), (z1, w1) in zip(left, left[1:]):
        if height <= z1:
            return w0 + (w1-w0)*(height-z0)/(z1-z0)
    return 0


def _annulus(mesh, x, y, z, radius, thickness=26, depth=65):
    """A real stone quatrefoil eye with an open centre and deep inner reveal."""
    segments = 24
    for i in range(segments):
        a, b = i*math.tau/segments, (i+1)*math.tau/segments
        rings = [[[xx, y+r*math.cos(t), z+r*math.sin(t)] for t in (a, b)]
                 for xx in (x-depth/2, x+depth/2) for r in (radius-thickness, radius)]
        inner_front, outer_front, inner_back, outer_back = rings
        mesh.face([inner_front[0], inner_front[1], outer_front[1], outer_front[0]], 'limestone')
        mesh.face([inner_back[0], outer_back[0], outer_back[1], inner_back[1]], 'limestone')
        mesh.face([inner_front[0], inner_back[0], inner_back[1], inner_front[1]], 'limestone')
        mesh.face([outer_front[0], outer_front[1], outer_back[1], outer_back[0]], 'limestone')


def _tracery(mesh, x, y, z, width, height):
    # Two smaller lancets carry the centre mullion. The upper round eye and
    # curved reveals read at distance without filling the parent opening.
    lower_height = height*.67
    sub_width = width*.43
    for side in (-1, 1):
        arch(mesh, x, y+side*width*.25, z+55, sub_width, lower_height, 100, 30, glass=False)
    mesh.block([x, y, z+lower_height*.47], [120, 48, lower_height*.94], 'limestone', 3)
    _annulus(mesh, x, y, z+height*.77, width*.17)


def _perforated_wall(mesh, x, y, bottom, top, width, depth, openings,
                     tracery=False, applied_frames=True):
    """Extrude a wall with true lancet holes; no backing block crosses a hole.

    Wall skins are swept between profile heights. Only the outer boundary and
    hole outlines get depth faces, avoiding buried caps at every sweep band.
    """
    y0, y1 = y-width/2, y+width/2
    profiles = [(centre, base, pointed_profile(w, h), w, h) for centre, base, w, h in openings]
    heights = {bottom, top}
    for _, base, profile, _, _ in profiles:
        heights.update(round(base+v, 4) for _, v in profile if bottom < base+v < top)
    heights = sorted(heights)
    for z0, z1 in zip(heights, heights[1:]):
        middle = (z0+z1)/2
        holes = sorted((c, b, p) for c, b, p, _, h in profiles if b < middle < b+h)
        cursor0 = cursor1 = y0
        for centre, base, profile in holes:
            half0, half1 = _half_width(profile, z0-base), _half_width(profile, z1-base)
            edge0, edge1 = centre-half0, centre-half1
            quad = [[x, cursor0, z0], [x, edge0, z0], [x, edge1, z1], [x, cursor1, z1]]
            mesh.face(list(reversed(quad)))
            mesh.face([[p[0]+depth, p[1], p[2]] for p in quad])
            cursor0, cursor1 = centre+half0, centre+half1
        quad = [[x, cursor0, z0], [x, y1, z0], [x, y1, z1], [x, cursor1, z1]]
        mesh.face(list(reversed(quad)))
        mesh.face([[p[0]+depth, p[1], p[2]] for p in quad])
    boundary = [(y0, bottom), (y0, top), (y1, top), (y1, bottom)]
    for a, b in zip(boundary, boundary[1:]+boundary[:1]):
        mesh.face([[x+depth, *a], [x+depth, *b], [x, *b], [x, *a]])
    for centre, base, profile, w, h in profiles:
        outline = [(centre+u, base+v) for u, v in profile]
        for a, b in zip(outline, outline[1:]+outline[:1]):
            mesh.face([[x, *a], [x, *b], [x+depth, *b], [x+depth, *a]], 'limestone')
        if applied_frames:
            arch(mesh, x-45, centre, base, w, h, 115, 55, glass=False)
            arch(mesh, x+depth+45, centre, base, w, h, 115, 40, glass=False)
            mesh.block([x-50, centre, base-32], [210, w+140, 64], 'limestone', 5)
        if tracery:
            _tracery(mesh, x-60, centre, base, w, h)


def _side_wall(mesh, x, y, bottom, top, width, depth, openings, applied_frames=True):
    local = _CrownMesh('temporary_crown_wall')
    _perforated_wall(local, 0, 0, bottom, top, width, depth, openings,
                     applied_frames=applied_frames)
    # A proper rotation retains the helper's outward winding and supplied normals.
    for offset, material in enumerate(local.triangle_materials):
        corners = [local.positions[i] for i in local.indices[offset*3:offset*3+3]]
        mesh.face([[x-p[1], y+p[0], p[2]] for p in corners], MATERIALS[material])


def _slate_roof(mesh, body):
    # Sloped slate ridges join the attached towers behind the carved front.
    # Hipped ends avoid presenting a single broad triangular house gable.
    x0, x1 = body.x0+350, body.x1-350
    y0, y1 = body.y-body.width/2+350, body.y+body.width/2-350
    z = body.eaves+40
    corners = [[x0, y0, z], [x1, y0, z], [x1, y1, z], [x0, y1, z]]
    ridge0 = [x0+(x1-x0)*.23, body.y, body.ridge]
    ridge1 = [x1-(x1-x0)*.23, body.y, body.ridge]
    mesh.face([corners[0], corners[1], ridge1, ridge0], 'slate')
    mesh.face([corners[1], corners[2], ridge1], 'slate')
    mesh.face([corners[2], corners[3], ridge0, ridge1], 'slate')
    mesh.face([corners[3], corners[0], ridge0], 'slate')
    mesh.rod(ridge0, ridge1, 12, 'iron', 8)
    for corner, ridge in zip(corners, (ridge0, ridge1, ridge1, ridge0)):
        mesh.rod(corner, ridge, 12, 'iron', 8)


def _tower_cap(mesh, x, y, bottom, peak, width):
    from aegis_citadel_spire_detail import articulated_spire
    return articulated_spire(mesh, x, y, bottom, peak, width)


def _corner_tower(mesh, body, side, peak):
    """An attached stone tower with a deep upper bay and a substantial spire."""
    central = body.id == 'central_belfry'
    width = 800 if central else 650
    x = body.x0+(90 if central else 120)
    if body.id=='east_belfry' and side<0:
        # The advanced inner turret clears the adjacent central lancet bay.
        x=body.x0-300
    y = body.y+side*(body.width/2+(120 if not central else 0))
    front = x-width/2
    stone_top = body.eaves+(1050 if central else 1550)
    bay_bottom = stone_top-800
    lower_height = bay_bottom-body.bottom
    # The broad core is solid. A recessed blind lancet carves its front skin;
    # its real backing is deliberately behind the reveal, not on the façade.
    mesh.block([x+65, y, body.bottom+lower_height/2],
               [width-130, width, lower_height], 'stone', 7)
    lower_opening = [(y, body.bottom+170, width*.46, lower_height-650)]
    _perforated_wall(mesh, front, y, body.bottom, bay_bottom,
                     width, 130, lower_opening, applied_frames=False)
    # The belfry above the continuous core is hollow and open on four sides.
    bay_width, bay_height = width*.46, 650
    opening = [(y, bay_bottom+55, bay_width, bay_height)]
    _perforated_wall(mesh, front, y, bay_bottom, stone_top, width, 115, opening,
                     applied_frames=False)
    _perforated_wall(mesh, x+width/2-115, y, bay_bottom, stone_top, width, 115, opening,
                     applied_frames=False)
    for edge in (-1, 1):
        wall_y = y+edge*width/2
        _side_wall(mesh, x, wall_y if edge < 0 else wall_y-115,
                   bay_bottom, stone_top, width, 115,
                   [(0, bay_bottom+55, bay_width, bay_height)], applied_frames=False)
    # Continuous corner piers and successive ledges articulate the masonry;
    # six individually scaled caps replace the old array of small pinnacles.
    for tier in range(3):
        z = body.bottom+(stone_top-body.bottom)*(tier+1)/3
        mesh.block([x, y, z], [width+50-tier*10, width+50-tier*10, 85], 'limestone', 6)
    for corner in (-1, 1):
        mesh.block([front-15, y+corner*(width/2-25), body.bottom+(stone_top-body.bottom)/2],
                   [95, 100, stone_top-body.bottom+40], 'limestone', 5)
    mesh.block([x, y, stone_top+30], [width+70, width+70, 120], 'limestone', 7)
    spire = _tower_cap(mesh, x, y, stone_top+90, peak, width+20)
    return dict(id=body.id+('_left_tower' if side < 0 else '_right_tower'),
                centreCm=[x, y], widthCm=width, stoneTopCm=stone_top,
                peakCm=peak, upperBayHeightCm=bay_height, upperRevealDepthCm=115,
                spireDetail=spire)


def _belfry(mesh, body):
    height = body.eaves-body.bottom
    central = body.id == 'central_belfry'
    thickness = 420 if central else 290
    opening_height = height-380
    front_openings = front_lancets(body)
    _perforated_wall(mesh, body.x0, body.y, body.bottom, body.eaves,
                     body.width, thickness, front_openings, tracery=True)
    _perforated_wall(mesh, body.x1-thickness, body.y, body.bottom, body.eaves,
                     body.width, thickness, front_openings)
    centre = (body.x0+body.x1)/2
    side_openings = [(u, body.bottom+155, 545, opening_height) for u in (-780, 0, 780)]
    for side in (-1, 1):
        edge = body.y+side*body.width/2
        _side_wall(mesh, centre, edge if side < 0 else edge-thickness,
                   body.bottom, body.eaves, body.x1-body.x0, thickness, side_openings)
        mesh.block([centre, edge, body.eaves+50],
                   [body.x1-body.x0+70, 260, 100], 'limestone', 7)
        for xx in (body.x0+620,centre,body.x1-620):
            mesh.block([xx,edge,body.eaves+155],[240,300,290],'stone',8)
    for edge in (body.x0, body.x1):
        mesh.block([edge, body.y, body.eaves+50], [260, body.width+70, 100], 'limestone', 7)
        for yy in (body.y-body.width*.28,body.y,body.y+body.width*.28):
            mesh.block([edge,yy,body.eaves+155],[300,240,290],'stone',8)
    for xx in (body.x0-45, body.x1+45):
        for yy in (body.y-body.width/2+30, body.y+body.width/2-30):
            # Stepped buttresses remain substantial at the proposal's final scale.
            for tier in range(3):
                bottom = body.bottom+tier*height/3
                mesh.block([xx, yy, bottom+height/6], [260-tier*35, 220-tier*25, height/3+20], 'stone', 7)
                mesh.block([xx, yy, bottom+height/3], [310-tier*35, 255-tier*25, 65], 'limestone', 5)
    _slate_roof(mesh, body)
    towers = [_corner_tower(mesh, body, side, peak)
              for side, peak in zip((-1, 1), TOWER_PEAKS_CM[body.id])]
    return dict(**asdict(body), frontLancets=len(front_openings), revealDepthCm=thickness,
                frontBays=[dict(centreYcm=y, baseCm=z, widthCm=w, heightCm=h) for y,z,w,h in front_openings],
                windowHeightCm=max(row[3] for row in front_openings), trueOpenings=True,
                copingTopCm=body.eaves+300, roofSetbackCm=350, towers=towers)


def _central_cluster(mesh):
    """An octagonal lantern and attached turrets grow from the nave's roof."""
    x,y,bottom,stone_top=31200,0,12600,14800
    radius=690;depth=145
    ring=[(x+radius*math.cos(math.pi/8+i*math.tau/8),
           y+radius*math.sin(math.pi/8+i*math.tau/8)) for i in range(8)]
    for a,b in zip(ring,ring[1:]+ring[:1]):
        length=math.dist(a,b);along=[(a[j]-b[j])/length for j in range(2)]
        inward=[along[1],-along[0]];mid=[(a[j]+b[j])/2 for j in range(2)]
        local=_CrownMesh('central_lantern_wall')
        _perforated_wall(local,0,0,bottom,stone_top,length,depth,
            [(0,14170,length*.53,490)],tracery=False,applied_frames=False)
        for offset,role in enumerate(local.triangle_materials):
            face=[local.positions[i] for i in local.indices[offset*3:offset*3+3]]
            mesh.face([[mid[0]+inward[0]*p[0]+along[0]*p[1],
                        mid[1]+inward[1]*p[0]+along[1]*p[1],p[2]] for p in face],MATERIALS[role])
        for side in (-1,1):
            px,py=mid[0]+along[0]*length*.32*side,mid[1]+along[1]*length*.32*side
            mesh.rod([px,py,14185],[px,py,14580],13,'limestone',6)
    for px,py in ring:
        mesh.block([px,py,13690],[150,150,2180],'limestone',7)
        mesh.block([px,py,14810],[220,220,110],'limestone',7)
    mesh.ring(x,y,14845,630,750,'limestone',32)
    spire = _tower_cap(mesh,x,y,14910,MAXIMUM_Z_CM,1160)
    satellites=[]
    for index,(dx,dy,peak) in enumerate(((-440,-490,16280),(410,-520,15940),
                                        (-440,490,16360),(410,520,16050))):
        cx,cy=x+dx,y+dy;trunk_bottom,trunk_top=13600,14900
        mesh.block([cx,cy,(trunk_bottom+trunk_top)/2],[300,300,trunk_top-trunk_bottom],'stone',35)
        arch(mesh,cx-165,cy,13800,150,840,90,20,glass=False)
        mesh.block([cx,cy,trunk_top],[370,370,100],'limestone',8)
        turret_spire = _tower_cap(mesh,cx,cy,trunk_top+70,peak,350)
        satellites.append(dict(id='central_cluster_turret_'+str(index),centreCm=[cx,cy],
            widthCm=300,stoneTopCm=trunk_top,peakCm=peak,spireDetail=turret_spire))
    return dict(id='central_octagonal_lantern',centreCm=[x,y],bottomCm=bottom,
        widthCm=radius*2,stoneTopCm=stone_top,peakCm=MAXIMUM_Z_CM,
        upperBayBaseCm=14170,upperBayHeightCm=490,revealDepthCm=depth,
        satelliteTurrets=satellites,spireDetail=spire,
        attachedTo='central_belfry_roof_and_masonry_podium')


def build_keep_crown():
    """Return the bounded replacement mesh and its unapproved source contract."""
    mesh = _CrownMesh('upper_keep_crown_proposal')
    # A continuous masonry podium joins all three chambers above the preserved
    # ceiling. It uses the existing keep footprint and leaves the lower hall alone.
    mesh.block([30050, 0, 9570], [5740, 7160, 940], 'stone', 10)
    for z, expansion in ((9140, 0), (10035, 100), (10135, 170)):
        mesh.block([30050, 0, z], [5740+expansion, 7160+expansion, 80], 'limestone', 6)
    bodies = [_belfry(mesh, body) for body in BELFRIES]
    cluster=_central_cluster(mesh)
    # The side chambers meet the central nave through broad covered shoulders.
    for side in (-1, 1):
        mesh.block([30150, side*1770, 10750], [3400, 420, 1120], 'stone', 10)
        mesh.block([30150, side*1770, 11350], [3550, 520, 90], 'limestone', 6)
    mesh.reproject_stone_uvs()
    contract = dict(schemaVersion=1, proposalOnly=True, coordinates='final_unreal_centimetres',
        integration='replace_owned_upper_crown_then_append_after_upper_transform',
        preservedThroughZCm=PRESERVED_Z_CM, highestZCm=MAXIMUM_Z_CM,
        envelopeCm=[list(v) for v in ENVELOPE_CM], belfries=bodies,centralCluster=cluster,
        coreCompressionHighestZCm=14200,
        roofPolicy='supported_hipped_ridges_flared_spire_skirts_metal_arrises_and_recessed_lancet_dormers',
        visualApproval=False, nativeCollisionApproval=False, routeApproval=False,
        sourceReviewRequired=True, freshNativeEvidenceRequired=True)
    return mesh, contract
