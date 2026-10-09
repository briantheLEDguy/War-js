"""Source-preserving near/middle/far detail and restrained regional foliage adaptation."""

def foliage_recipe(identity):
    if identity not in ('sunmeadow_march','cinderfen_outskirts'):
        raise ValueError('Only reviewed first-batch foliage is admitted')
    return dict(lods=[dict(triangles=1.,screen=1.),dict(triangles=.16,screen=.10),dict(triangles=.035,screen=.025)],
        tint=[.64,.94,.68] if identity=='sunmeadow_march' else [.86,.86,.72],
        instanceTintRange=[.82,1.08],transmission=.12,collision=False,navigation=False,
        worldDisplacement=False,sourceGeometryPreservedAtLodZero=True,visualApproved=False,performanceAccepted=False)
