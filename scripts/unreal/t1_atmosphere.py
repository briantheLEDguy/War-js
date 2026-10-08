"""Bounded, source-derived first-batch atmosphere placement; no gameplay mutations."""
import math

ZONES = ('sunmeadow_march', 'cinderfen_outskirts')


def native(point):
    values = [point['z']*100, point['x']*100, point.get('y', 0)*100]
    if any(not math.isfinite(n) or abs(n) > 300000 for n in values):
        raise ValueError('Atmosphere coordinates must be finite and bounded')
    return values


def atmosphere_recipe(source, scenes):
    identity = source['id']
    if identity not in ZONES:
        raise ValueError('Later-batch native atmosphere remains gated')
    military = [native(k['deliveryPoint']) for k in source['orvrLayout']['keeps']]
    military += [native(o) for o in source['orvrLayout']['battlefieldObjectives']]
    if len(military) != 5:
        raise ValueError('Retain two keeps and three objective thresholds')
    steam = []
    if identity == ZONES[1]:
        for scene in scenes:
            if scene['id'].endswith(('_basalt_shelf', '_mineral_rise')):
                placements = scene['placements']
                steam.extend(native(placements[i]) for i in range(0, len(placements), max(1, len(placements)//3)))
        if not 1 <= len(steam) <= 16:
            raise ValueError('Geothermal effects require bounded authored vent sites')
    return dict(zone=identity, villageCentre=native(source['spawnPoint']), militaryCentres=military,
        steamSites=steam, audioGain=.6, maximumParticles=192, collision=False, replicated=False,
        audioProvenance='original-native-synthesis', activeCampaignChanged=False, visualApproved=False,
        audioApproved=False)


def validate_live_atmosphere(report, config):
    if not math.isfinite(report.get('environmentUnixSeconds', math.nan)) or report['environmentUnixSeconds'] <= 0:
        raise ValueError('Native atmosphere requires the authoritative world clock')
    if len(report.get('routes', [])) != len(config['routes']):
        raise ValueError('Native atmosphere requires all configured routes')
    for row, route in zip(report['routes'], config['routes']):
        expected = [i for i, p in enumerate(route['points']) if p.get('capture')]
        frames = row.get('atmosphereFrames', [])
        if [f.get('waypoint') for f in frames] != expected:
            raise ValueError('Native atmosphere frames must cover all reached camera waypoints')
        for frame in frames:
            if frame.get('zone') != config['zone'] or frame.get('active') is not True or frame.get('replicated') is not False or frame.get('collisionEnabled') is not False:
                raise ValueError('Native local weather was inactive or violated cosmetic boundaries')
            if not 0 <= frame.get('particles', -1) <= 192 or not 0 <= frame.get('queuedAudioBytes', -1) <= 24000:
                raise ValueError('Native atmosphere budget exceeded')
            if route['points'][frame['waypoint']].get('indoor') and (frame.get('observerInside') is not True or frame['particles'] != 0):
                raise ValueError('Native indoor shelter failed')
