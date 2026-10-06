"""Joined wing foundations, bounded to the measured existing precinct.

New solids fill the 222 cm foundation gap and rear/end-tower overhangs. Exact
route reservations are subtracted before emission; retained terrain is untouched.
"""
from aegis_citadel_mesh import Mesh
from aegis_citadel_supports import reservations,prism,emit_support


def build_wing_footings(blueprint):
    mesh=Mesh('wing_foundation_repairs')
    reserved=reservations(blueprint)
    rows=[]

    def add(key,x0,x1,y0,y1,bottom):
        solid=prism([x0,(y0+y1)/2,6010],[x1,(y0+y1)/2,6010],
                    y1-y0,bottom,cap_offset=0)
        receipt=emit_support(mesh,solid,reserved)
        rows.append(dict(id=key,boundsCm=[[x0,y0,bottom],[x1,y1,6010]],**receipt))

    for side in (-1,1):
        y0,y1=sorted((side*6900,side*9100))
        # The old block's 12 cm upper bevel ends at5776 on its outer face.
        # Start there to join that edge without another coincident exterior face.
        add('wing_connection_'+str(side),27000,33400,y0,y1,5776)
        add('wing_rear_'+str(side),33400,34400,y0,y1,2400)
        for x,width,centre_y in ((27450,850,9100),(33900,720,9100),(28600,1000,8900)):
            half=max(width/2,width*.45+55)
            outer=centre_y+half
            a,b=sorted((side*9100,side*outer))
            add('tower_outer_'+str(side)+'_'+str(x),x-half,x+half,a,b,2400)
    contract=dict(version=1,rows=rows,minimumZCm=2400,wingBaseZCm=6010,
        oldFoundationTopZCm=5788,oldFoundationOuterBevelTopZCm=5776,
        existingFoundationPreserved=True,retainedTerrainPreserved=True,
        exactRouteReservationsSubtracted=True,sourceGroundSamplingVersion=2,
        requiredNativeGroundSamples=144,structuralOnly=True,
        freshNativeEvidenceRequired=True,nativeApproved=False,visualApproved=False)
    return mesh,contract
