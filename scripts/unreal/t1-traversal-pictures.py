"""Labeled coverage diagrams of completed native walking fixtures, not footstep traces."""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT/'artifacts/unreal/t1-redesign'
proof = json.loads((DIRECTORY/'traversal-headless-latest.json').read_text())
homes = json.loads((DIRECTORY/'homes-latest.json').read_text())
plan = json.loads((DIRECTORY/'plan.json').read_text())
if proof['signature'] != homes['signature'] or not proof['savedCandidatesUnchanged']:
    raise RuntimeError('Walking coverage requires the matching unchanged candidate')
font = lambda size: ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', size)
for result in proof['zones']:
    identity = result['zone']
    source_file = DIRECTORY/(identity+'.json')
    if hashlib.sha256(source_file.read_bytes()).hexdigest() != plan['candidateHashes'][identity]:
        raise RuntimeError('Walking drawing input changed')
    zone = json.loads(source_file.read_text())
    completed = {r['id'] for r in result['routes'] if r['completed']}
    image = Image.new('RGB', (1400,1050), '#172227'); draw = ImageDraw.Draw(image)
    bounds = zone['spatial']['bounds']
    def p(row):
        return (50+(row['x']-bounds['minX'])/(bounds['maxX']-bounds['minX'])*1300,
                145+(bounds['maxZ']-row['z'])/(bounds['maxZ']-bounds['minZ'])*720)
    def label(row, text, dy=-22):
        x,y = p(row); draw.text((x+12,y+dy), text, font=font(17), fill='#eee8d3', stroke_width=2, stroke_fill='#172227')
    distance = sum(r['distanceCm'] for r in result['routes'])/1000/100
    draw.text((45,25), zone['name']+' — native walking coverage', font=font(35), fill='#eee8d3')
    draw.text((45,78), f"{result['routesCompleted']} completed routes · {distance:.2f} km · normal capsule, steps and movement · no jumps", font=font(20), fill='#b8e0cb')
    draw.polygon([p(row) for row in zone['spatial']['playableOutline']], fill=zone['orvrLayout']['biome']['palette'][0], outline='#d4c99d', width=3)
    for route in zone['orvrLayout']['caravanRoutes']:
        if any(route['id']+'_'+direction not in completed for direction in ('forward','reverse')):
            raise RuntimeError('Supply walking coverage incomplete')
        draw.line([p(row) for row in route['points']], fill='#dcb17e', width=13, joint='curve')
    for route in zone['paths']:
        if any(route['id']+'_'+direction not in completed for direction in ('forward','reverse')):
            raise RuntimeError('Road walking coverage incomplete')
        draw.line([p(row) for row in route['points']], fill='#96dfbc', width=5, joint='curve')
        for row in route['points']:
            x,y = p(row); draw.ellipse((x-3,y-3,x+3,y+3), fill='#e9f1df')
    for keep in zone['orvrLayout']['keeps']:
        x,y = p(keep); draw.rectangle((x-17,y-14,x+17,y+14), fill='#244e7b' if keep['realm']=='aegis' else '#842c38', outline='white', width=2)
        label(keep, keep['realm'].capitalize()+' keep approach')
    for i,bo in enumerate(zone['orvrLayout']['battlefieldObjectives']):
        x,y=p(bo);draw.ellipse((x-13,y-13,x+13,y+13),fill='#ffe5a1',outline='#172227',width=2);label(bo,'Objective '+str(i+1), -46)
    for camp in zone['orvrLayout']['stagingCamps']:
        x,y=p(camp);draw.ellipse((x-19,y-19,x+19,y+19),outline='white',width=3);label(camp,'Staging access')
    label(zone['spawnPoint'], 'Village: two furnished home walks')
    for i in (3,5):label(zone['paths'][0]['points'][i], 'Rotation '+str(1 if i==3 else 2), 18)
    for trigger in zone['zoneTriggers']:
        if trigger['targetZoneId'].endswith(('_hollow','_pit','_den')):label(trigger, 'Optional lair approach')
    draw.text((45,905),'Green: road polylines reached in both directions   Tan: six supply itineraries reached in both directions',font=font(18),fill='#eee8d3')
    draw.text((45,940),'This diagram shows configured coverage. Movement ran through native CharacterMovement with a fixed timestep.',font=font(18),fill='#cecbb9')
    draw.text((45,975),'Vehicle hulls, animated gates, camera clearance, competitive fairness, GM persistence and art approval remain open.',font=font(18),fill='#cecbb9')
    image.save(DIRECTORY/(identity+'_native_walking_coverage.png'))
print(json.dumps(dict(walkingCoverageDrawings=len(proof['zones']), signature=proof['signature'])))
