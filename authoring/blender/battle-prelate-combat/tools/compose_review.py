"""Compose captured runtime screenshots into labelled animation review sheets."""
from pathlib import Path
from PIL import Image, ImageDraw
import json

root=Path(__file__).resolve().parents[1]
repo=root.parents[2]
motions=json.loads((repo/'src/game/animation/battlePrelateMotions.json').read_text())['motions']
for variant in ['male','female','novitiate']:
    for phase in ['windup','contact']:
        output=Image.new('RGB',(1000,990),'#17212c')
        draw=ImageDraw.Draw(output)
        for i,motion in enumerate(motions):
            source=root/'review'/f'{variant}_{motion["clip"]}_{phase}.png'
            if not source.exists(): continue
            screenshot=Image.open(source)
            tile=screenshot.crop((550,80,1030,655)).resize((250,300))
            x,y=(i%4)*250,(i//4)*330
            output.paste(tile,(x,y))
            draw.text((x+8,y+304),motion['clip'].removeprefix('prelate_')+' / '+phase,fill='#f0dfba')
        output.save(root/'review'/f'{variant}_{phase}_sheet.png')

# Sampled runtime motion excerpts; hold the last pose between loops.
for view in ['side', 'gameplay']:
    frames, durations = [], []
    samples = [1, 2, 3, 4, 5, 6, 7, 8, 10, 11]
    for index, sample in enumerate(samples):
        output = Image.new('RGB', (960, 615), '#17212c')
        draw = ImageDraw.Draw(output)
        for column, version in enumerate(['before', 'after']):
            source = root/'review'/f'motion_{view}_{version}_{sample:02d}.png'
            if not source.exists(): break
            output.paste(Image.open(source).crop((550, 80, 1030, 655)), (column*480, 0))
            draw.text((column*480+15, 590), f'{version.upper()} - {view} / sampled runtime', fill='#f0dfba')
        else:
            frames.append(output)
            durations.append(round((samples[index+1]-sample)*75) if index+1<len(samples) else 400)
    if frames:
        frames[0].save(root/'review'/f'litany_{view}_comparison.gif', save_all=True,
                       append_images=frames[1:], duration=durations, loop=0)
