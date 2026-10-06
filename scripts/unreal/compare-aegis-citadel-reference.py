"""Dimensioned reference/model comparison from actual camera-projected geometry.

The original image is embedded unchanged behind SVG clip paths. Pixel landmarks
are a hand trace with stated uncertainty, not a surveyed dimensional drawing.
No generated raster is used as evidence for an architectural or gameplay claim.
"""
import argparse
import base64
import html
import json
import math
from pathlib import Path
from aegis_citadel_blueprint import OUT, REFERENCE, sha


REFERENCE_FRONT=dict(keepLeft=[191,953],keepRight=[411,953],crownLeft=[218,811],
    crownRight=[355,811],portalLeft=[270,947],portalRight=[309,947],portalApex=[289,879],
    outerLeft=[45,977],outerRight=[545,977],courtLeft=[159,1004],courtRight=[427,1004],
    lowerCurtainLeft=[30,1005],lowerCurtainRight=[555,1005],mainSpireTop=[307,733],
    monumentCenter=[289,993],monumentTop=[286,959])


def compare(run):
    plan=json.loads((run/'blueprint.json').read_text())
    mass=plan['upperMassing'];cut=mass['preservedThroughZCm']
    roof=cut+(14400-cut)*(mass['coreCompressionHighestZCm']-cut)/(mass['originalHighestZCm']-cut)
    source=json.loads((run/'assets-source.json').read_text())
    receipt=json.loads((run/'source-review/receipt.json').read_text())
    if receipt['sourceMaster']!=source['sourceMaster']:raise ValueError('Source render master drift')
    frames={row['id']:row for row in receipt['frames']}
    for key in ('hero','front'):
        if key not in frames or sha(run/frames[key]['path'])!=frames[key]['sha256']:
            raise ValueError('Missing actual signed source frame: '+key)
    if sha(REFERENCE)!=plan['reference']['sha256']:raise ValueError('Reference image drift')
    def data(file):return 'data:image/png;base64,'+base64.b64encode(file.read_bytes()).decode()
    ref=data(REFERENCE);hero=data(run/frames['hero']['path']);front=data(run/frames['front']['path'])
    model=frames['front']['projectedLandmarksPx']
    # Compare projected proportions, separately from exact centimetre dimensions.
    # Widths use matching named landmarks; image uncertainty stays visible.
    def width(points,left,right):return math.dist(points[left],points[right])
    def proportions(points):
        p=width(points,'portalLeft','portalRight')
        base=[(points['portalLeft'][i]+points['portalRight'][i])/2 for i in range(2)]
        crown=[(points['crownLeft'][i]+points['crownRight'][i])/2 for i in range(2)]
        portal_height=math.dist(base,points['portalApex'])
        return dict(keep_to_portal=width(points,'keepLeft','keepRight')/p,
                    outer_to_portal=width(points,'outerLeft','outerRight')/p,
                    court_to_portal=width(points,'courtLeft','courtRight')/p,
                    monument_to_portal=width(points,'monumentCenter','monumentTop')/p,
                    top_to_portal_height=math.dist(base,points['mainSpireTop'])/portal_height,
                    upper_mass_to_portal_height=math.dist(base,crown)/portal_height,
                    spire_above_crown_to_portal_height=math.dist(crown,points['mainSpireTop'])/portal_height)
    reference_ratios,model_ratios=proportions(REFERENCE_FRONT),proportions(model)
    bounds={}
    for row in source['assets']:
        if row['gateLeaf']:continue
        mesh=json.loads((run/row['meshFile']).read_text())
        bounds[row['id']]=[[min(v[i] for v in mesh['positions']) for i in range(3)],
                           [max(v[i] for v in mesh['positions']) for i in range(3)]]
    global_bounds=[[min(b[0][i] for b in bounds.values()) for i in range(3)],
                   [max(b[1][i] for b in bounds.values()) for i in range(3)]]
    report=dict(schemaVersion=1,revision=plan['revision'],blueprintSignature=plan['signature'],
        geometrySignature=source['geometrySignature'],referenceSha256=sha(REFERENCE),
        referenceLandmarks=dict(frontPixels=REFERENCE_FRONT,uncertaintyPx=5,
            interpretation='Hand-traced front inset; background and lower-city extents are not dimensional measurements.'),
        actualModel=dict(boundsCm=global_bounds,meshBoundsCm=bounds,projectedLandmarksPx=model,
                         reviewViews=plan['reviewViews'],frames=receipt['frames']),
        compositionMapping=plan['interpretation'].get('compositionMapping'),
        projectedRatios=dict(reference=reference_ratios,model=model_ratios),
        knownDifferences=['The source frames omit retained lower-city/mountain context; native combined views are required.',
            'The center monument remains on the radial landmark; the capture standing point is 10 m west.',
            'Reference arrows do not encode stair dimensions. Real risers, landings, clear widths and stage gates are authored.',
            'Projected ratios compare a hand-traced perspective image with modeled cameras; they are not a proof of exact architectural identity.'],
        nativeVisualApproval=False,nativeTraversalApproval=False)
    file=run/'source-review/reference-proportion-review.json';file.write_text(json.dumps(report,indent=2)+'\n')
    parts=['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="1900" height="1720" viewBox="0 0 1900 1720">',
        '<rect width="1900" height="1720" fill="#111c26"/>',
        '<style>text{font-family:Segoe UI,sans-serif;fill:#eadcc6}.small{font-size:15px}.metric{font-size:18px}.title{font-size:27px}.dim{stroke:#e8bc6c;stroke-width:2;fill:none}.trace{stroke:#65becf;stroke-width:2;fill:none}</style>',
        '<text x="40" y="44" class="title">Bastion of Aegis — dimensioned reference / actual model review</text>',
        f'<text x="40" y="75" class="small">Revision {plan["revision"]} · real geometry / CPU render · geometry {source["geometrySignature"][:16]} · native approval pending</text>',
        '<text x="40" y="110" class="metric">Original supplied main perspective</text>',
        '<text x="970" y="110" class="metric">Actual modeled hero — same signed camera as native proof</text>']
    # Images keep their original aspect. Clipping crops the original reference;
    # it never stretches or paints architectural details into either image.
    def picture(name,image,x,y,w,h,crop=None,image_size=None):
        parts.append(f'<defs><clipPath id="{name}"><rect x="{x}" y="{y}" width="{w}" height="{h}"/></clipPath></defs>')
        if crop:
            a,b,c,d=crop;s=min(w/c,h/d);ox=x+(w-c*s)/2-a*s;oy=y+(h-d*s)/2-b*s
            iw,ih=image_size;parts.append(f'<image x="{ox}" y="{oy}" width="{iw*s}" height="{ih*s}" xlink:href="{image}" clip-path="url(#{name})"/>')
            return lambda p:[ox+p[0]*s,oy+p[1]*s]
        iw,ih=image_size;s=min(w/iw,h/ih);ox=x+(w-iw*s)/2;oy=y+(h-ih*s)/2
        parts.append(f'<image x="{ox}" y="{oy}" width="{iw*s}" height="{ih*s}" xlink:href="{image}"/>')
        return lambda p:[ox+p[0]*s,oy+p[1]*s]
    picture('main_ref',ref,40,130,890,470,[255,15,1175,680],[1448,1086])
    picture('main_model',hero,970,130,890,470,image_size=frames['hero']['resolutionPx'])
    parts.extend(['<text x="40" y="635" class="metric">Original front inset — hand-traced landmarks (±5 px)</text>',
                  '<text x="970" y="635" class="metric">Actual front projection — dimensions in metres</text>'])
    refxy=picture('front_ref',ref,40,655,890,470,[12,715,563,311],[1448,1086])
    modxy=picture('front_model',front,970,655,890,470,image_size=frames['front']['resolutionPx'])
    def dimension(xy,points,left,right,label,offset):
        a,b=xy(points[left]),xy(points[right]);a[1]+=offset;b[1]+=offset
        parts.append(f'<path class="dim" d="M{a[0]} {a[1]-8}v16M{a[0]} {a[1]}L{b[0]} {b[1]}M{b[0]} {b[1]-8}v16"/>')
        parts.append(f'<text x="{(a[0]+b[0])/2}" y="{(a[1]+b[1])/2-9}" text-anchor="middle" class="small">{html.escape(label)}</text>')
    for xy,points,is_model in ((refxy,REFERENCE_FRONT,False),(modxy,model,True)):
        dimension(xy,points,'portalLeft','portalRight','18 m clear opening' if is_model else '39 ±10 px opening',20)
        dimension(xy,points,'keepLeft','keepRight','92 m central core (144 m incl. wings)' if is_model else '220 ±10 px central core interpretation',-170)
        dimension(xy,points,'outerLeft','outerRight','182 m upper wing envelope' if is_model else '500 ±10 px visible outer extent',65)
        for key in ('keepLeft','keepRight','portalLeft','portalRight','mainSpireTop','monumentCenter','monumentTop'):
            x,y=xy(points[key]);parts.append(f'<circle cx="{x}" cy="{y}" r="4" fill="#65becf"/>')
    parts.extend(['<text x="40" y="1180" class="metric">Projected width / height ratios (matching portal dimension = 1)</text>',
                  '<text x="1100" y="1180" class="metric">Actual authored dimensions and gameplay accommodations</text>'])
    labels=dict(keep_to_portal='Front keep envelope / portal',outer_to_portal='Visible outer envelope / portal',
                court_to_portal='Court width / portal width',monument_to_portal='Monument height / portal width',
                top_to_portal_height='Portal base to highest spire / portal height',
                upper_mass_to_portal_height='Portal base to core crown / portal height',
                spire_above_crown_to_portal_height='Core crown to highest spire / portal height')
    for i,(key,label) in enumerate(labels.items()):
        parts.append(f'<text x="40" y="{1215+i*31}" class="small">{label}: reference {reference_ratios[key]:.2f} · model {model_ratios[key]:.2f}</text>')
    dimensions=['Court 118 × 144 m · paving circle diameter 60 m',
        'Grand stair: 36 m architectural width · 18 m reserved main lane',
        'Floors: court 42.1 m · balconies 54.1 m · hall 60.1 m · galleries 72.1 m',
        'Monument stays [20800,0]; capture point [20800,-1000] cm',
        '43 routes · every crossing enumerated · 3 outer / 5 inner gate leaves',
        f'Portal base 60.1 m · core crown {roof/100:.1f} m · highest spire {mass["highestZCm"]/100:.1f} m']
    for i,line in enumerate(dimensions):parts.append(f'<text x="1100" y="{1215+i*31}" class="small">{html.escape(line)}</text>')
    for i,line in enumerate(report['knownDifferences']):
        parts.append(f'<text x="40" y="{1480+i*30}" class="small">{html.escape(line)}</text>')
    parts.append('</svg>');svg=run/'source-review/reference-proportion-review.svg';svg.write_text('\n'.join(parts)+'\n')
    print(svg)
    print(json.dumps(report['projectedRatios'],indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--revision');args=parser.parse_args()
    revision=args.revision or json.loads((OUT/'current.json').read_text())['revision']
    compare(OUT/revision)
