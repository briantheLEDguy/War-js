"""Supported central keep standard authored directly in final centimetres.

The caller removes the old central standard and its intersecting parapet blocks.
This upper-only addition joins the retained front wall without changing a portal.
"""
from aegis_citadel_mesh import Mesh, banner, UPPER_FACTOR

STANDARD = dict(x=25760, y=0, top=12400, width=1200, length=2300)
WALL_TOP_CM = 9000 + (14400-9000)*UPPER_FACTOR
ROLL_TOP_BOUND_CM = 9420.5


def build_central_standard():
    masonry = Mesh('central_standard_support', False)
    bottom, top = WALL_TOP_CM-80, 12500
    masonry.block([26000,0,(bottom+top)/2], [280,1700,top-bottom], 'stone', 8)
    masonry.block([26000,0,12535], [460,1900,70], 'flagstone', 8)
    for side in (-1,1):
        masonry.block([25880,side*850,(bottom+12600)/2],
                      [280,170,12600-bottom], 'limestone', 8)
        # Brackets sit outside the cloth and connect its bar to the front wall.
        masonry.rod([25890,side*720,12335], [25760,side*720,12420], 15, 'iron', 8)
        masonry.block([25895,side*720,12330], [70,90,150], 'iron', 6)
    for y in range(-840,841,210):
        masonry.block([25810,y,12705], [280,110,210], 'stone', 6)
    cloth = Mesh('central_standard_cloth', False)
    banner(cloth, STANDARD['x'], STANDARD['y'], STANDARD['top'],
           STANDARD['width'], STANDARD['length'], True)
    hem = min(p[2] for p in cloth.positions)
    wall_gap = 25860-max(p[0] for p in cloth.positions)
    if hem <= ROLL_TOP_BOUND_CM+250 or wall_gap < 30:
        raise ValueError('Central cloth must clear the measured rolls and front wall')
    contract = dict(version=1, finalCoordinates=True, standard=STANDARD.copy(),
        wallJoinBottomCm=bottom, retainedWallTopCm=WALL_TOP_CM,
        measuredRollTopBoundCm=ROLL_TOP_BOUND_CM, actualHemBottomCm=hem,
        minimumRollClearanceCm=hem-ROLL_TOP_BOUND_CM,
        minimumClothWallGapCm=wall_gap, upperOnly=True,
        replacedParapetHalfWidthCm=950, bracketCount=2, nativeApproved=False)
    return masonry, cloth, contract
