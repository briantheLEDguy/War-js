"""Paint and retain deterministic frontier PBR source channels and brush records.

These are original material strokes, not photographic lighting or generated
noise. The retained height channel supplies small grain, weave and forging marks;
Blender subsequently bakes geometric normals and actual asset self-occlusion.
"""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
SIZE = 1024
GRAIN = [
 [(22,0),(27,140),(19,295),(24,480),(13,660),(18,850),(22,1023)],
 [(53,0),(60,170),(44,335),(59,530),(53,710),(50,860),(53,1023)],
 [(94,0),(98,205),(78,370),(92,500),(89,750),(92,930),(94,1023)],
 [(137,0),(130,150),(141,288),(125,470),(126,630),(139,830),(137,1023)],
 [(173,0),(169,180),(177,340),(150,520),(167,720),(176,870),(173,1023)],
 [(212,0),(203,240),(211,380),(195,570),(208,755),(222,930),(212,1023)],
 [(243,0),(235,163),(241,307),(250,449),(229,611),(235,860),(243,1023)],
 [(281,0),(296,165),(283,321),(266,453),(289,637),(277,877),(281,1023)],
 [(318,0),(326,185),(315,320),(304,510),(325,683),(328,848),(318,1023)],
 [(354,0),(366,211),(355,363),(334,536),(346,747),(363,918),(354,1023)],
 [(389,0),(380,189),(388,346),(372,520),(391,742),(397,870),(389,1023)],
 [(426,0),(435,147),(415,311),(436,492),(418,647),(432,911),(426,1023)],
 [(463,0),(472,231),(466,390),(450,530),(476,754),(473,911),(463,1023)],
 [(498,0),(491,169),(510,346),(477,523),(501,711),(508,877),(498,1023)],
 [(535,0),(540,141),(528,338),(550,498),(537,687),(529,881),(535,1023)],
 [(568,0),(577,172),(559,363),(582,496),(570,745),(559,910),(568,1023)],
 [(604,0),(598,227),(617,370),(604,570),(591,713),(599,918),(604,1023)],
 [(646,0),(636,160),(643,299),(657,495),(638,705),(639,855),(646,1023)],
 [(681,0),(692,191),(683,343),(665,520),(685,747),(695,906),(681,1023)],
 [(719,0),(710,231),(724,397),(706,567),(718,693),(712,910),(719,1023)],
 [(754,0),(762,173),(749,355),(772,523),(754,698),(760,897),(754,1023)],
 [(791,0),(786,144),(803,317),(782,533),(803,715),(798,876),(791,1023)],
 [(828,0),(836,224),(822,382),(846,521),(827,736),(819,907),(828,1023)],
 [(864,0),(876,173),(858,342),(877,511),(867,731),(854,896),(864,1023)],
 [(901,0),(893,209),(914,378),(889,554),(908,740),(902,918),(901,1023)],
 [(937,0),(947,180),(930,339),(949,524),(935,680),(928,859),(937,1023)],
 [(976,0),(966,212),(988,366),(972,541),(987,765),(978,898),(976,1023)],
 [(1008,0),(1000,183),(1012,342),(995,556),(1009,740),(1002,929),(1008,1023)],
]
KNOTS=[[(279,374),(259,417),(254,473),(264,513),(280,527),(298,500),(304,454),(296,407),(279,374)],
       [(741,710),(725,742),(722,792),(738,829),(752,813),(764,776),(759,737),(741,710)]]
CHECKS=[[(103,0),(104,93),(98,152)],[(410,0),(405,71),(409,135),(402,184)],[(585,1023),(584,939),(578,908)],[(909,1023),(915,977),(908,948)]]
HAMMER=[(57,71),(180,119),(289,59),(437,159),(581,81),(715,123),(891,57),(968,219),(88,301),(227,256),(368,337),(533,275),(690,359),(839,289),(52,481),(194,436),(328,511),(504,443),(663,512),(807,473),(945,553),(107,649),(249,618),(407,688),(562,624),(748,670),(881,632),(53,840),(198,792),(365,886),(517,787),(656,849),(811,793),(966,876),(143,973),(477,957),(723,972)]
HEM_SOIL=[[(0,0),(54,0),(42,122),(72,221),(41,289),(60,417),(32,491),(74,603),(45,750),(67,852),(43,967),(57,1023),(0,1023)],
          [(1023,0),(977,0),(955,126),(984,273),(962,335),(978,441),(948,557),(984,649),(962,771),(974,889),(953,1023),(1023,1023)]]
RUNOFF=[[(40,173),(89,176),(132,193),(174,184)],[(32,446),(108,451),(151,464)],[(48,705),(124,718),(183,713)],
        [(981,89),(923,101),(866,86)],[(984,372),(919,381),(837,374)],[(980,615),(928,622),(871,614)],[(985,937),(934,947),(887,929)]]
END_WEATHER=[[(0,0),(1023,0),(1023,33),(912,28),(841,46),(758,30),(635,52),(510,35),(399,56),(265,34),(117,46),(0,28)],
             [(0,1023),(1023,1023),(1023,997),(891,985),(767,998),(642,976),(519,997),(421,972),(304,994),(203,981),(102,998),(0,983)]]


def paint(name, material):
    base=tuple(material['basecolor']); rough=round(material['roughness']*255); metal=round(material['metallic']*255)
    images={'basecolor':Image.new('RGB',(SIZE,SIZE),base),'roughness':Image.new('L',(SIZE,SIZE),rough),
            'metallic':Image.new('L',(SIZE,SIZE),metal),'height':Image.new('L',(SIZE,SIZE),128)}
    drawers={channel:ImageDraw.Draw(image) for channel,image in images.items()}
    kind=material['paint']
    def color(delta): return tuple(max(0,min(255,v+delta)) for v in base)
    if kind=='wood':
        for i,path in enumerate(GRAIN):
            drawers['basecolor'].line(path,fill=color(-17),width=8,joint='curve')
            drawers['height'].line(path,fill=113,width=5,joint='curve')
            drawers['roughness'].line(path,fill=min(255,rough+14),width=7,joint='curve')
            for offset,width in ((9,3),(-7,2),(14,1),(-13,1)):
                shifted=[(x+offset,y) for x,y in path]
                drawers['basecolor'].line(shifted,fill=color(7 if offset>0 else -8),width=width,joint='curve')
                drawers['height'].line(shifted,fill=131 if offset>0 else 122,width=width,joint='curve')
        for path in KNOTS:
            for width,delta,height in ((16,-12,122),(8,-27,110),(3,3,126)):
                drawers['basecolor'].line(path,fill=color(delta),width=width,joint='curve')
                drawers['height'].line(path,fill=height,width=width,joint='curve')
        for path in CHECKS:
            drawers['basecolor'].line(path,fill=color(-34),width=3,joint='curve')
            drawers['height'].line(path,fill=92,width=3,joint='curve')
    elif kind=='metal':
        for index,(x,y) in enumerate(HAMMER):
            # Subtle hand-forging depressions and narrow scuffs; broad identical
            # bright flecks read as polka dots on the exported dark metal.
            width=(7,11,5,9)[index%4]
            patch=[(x-width,y-3),(x-width//2,y-7),(x+width,y-2),(x+width//2,y+5),(x-width,y+3)]
            drawers['height'].polygon(patch,fill=125)
            drawers['roughness'].polygon(patch,fill=max(0,rough-5))
            if index%3==1:
                drawers['basecolor'].line([(x-width,y+5),(x+4,y+4),(x+width+6,y+1)],fill=color(5),width=1)
        for y in (38,1000):
            drawers['basecolor'].line([(0,y),(SIZE,y)],fill=color(13),width=4)
            drawers['roughness'].line([(0,y),(SIZE,y)],fill=max(0,rough-35),width=8)
    elif kind=='cloth':
        # Finite repeated finished weave brush, with long warp direction matching U/V.
        for x in range(0,SIZE,8):
            drawers['basecolor'].line([(x,0),(x,SIZE)],fill=color(8),width=2)
            drawers['height'].line([(x,0),(x,SIZE)],fill=143,width=2)
        for y in range(0,SIZE,8):
            drawers['basecolor'].line([(0,y),(SIZE,y)],fill=color(-9),width=2)
            drawers['height'].line([(0,y),(SIZE,y)],fill=117,width=2)
        for x in (24,30,994,1000):
            drawers['basecolor'].line([(x,0),(x,SIZE)],fill=color(-18),width=2)
            drawers['height'].line([(x,0),(x,SIZE)],fill=147,width=3)
        for y in range(10,SIZE,18):
            for x in (26,997):
                drawers['basecolor'].line([(x-4,y),(x+4,y+5)],fill=color(27),width=3)
                drawers['height'].line([(x-4,y),(x+4,y+5)],fill=155,width=3)
    else:
        for x,y in HAMMER:
            path=[(x-24,y-12),(x-11,y-5),(x+2,y-8),(x+11,y+1),(x+25,y+5)]
            drawers['basecolor'].line(path,fill=color(-8),width=3,joint='curve')
            drawers['height'].line(path,fill=116,width=2,joint='curve')
            drawers['roughness'].line(path,fill=min(255,rough+13),width=4)
        for x in (19,1005):
            drawers['basecolor'].line([(x,0),(x,SIZE)],fill=color(-18),width=9)
            for y in range(8,SIZE,22):
                drawers['basecolor'].line([(x-6,y),(x+6,y+8)],fill=(151,124,77),width=3)
                drawers['height'].line([(x-6,y),(x+6,y+8)],fill=153,width=3)
    # Exposure follows the authored construction UVs: timber ends, cloth hems,
    # rain run-off and forged edges, rather than indiscriminate random grunge.
    if kind=='wood':
        mask=Image.new('L',(SIZE,SIZE),0); brush=ImageDraw.Draw(mask)
        for polygon in END_WEATHER: brush.polygon(polygon,fill=95)
        mask=mask.filter(ImageFilter.GaussianBlur(12))
        images['basecolor']=Image.composite(Image.new('RGB',(SIZE,SIZE),(92,87,68)),images['basecolor'],mask)
        images['roughness']=Image.composite(Image.new('L',(SIZE,SIZE),238),images['roughness'],mask)
    elif name=='campaign_canvas':
        mask=Image.new('L',(SIZE,SIZE),0); brush=ImageDraw.Draw(mask)
        for polygon in HEM_SOIL: brush.polygon(polygon,fill=215)
        for line in RUNOFF: brush.line(line,fill=90,width=19,joint='curve')
        mask=mask.filter(ImageFilter.GaussianBlur(13))
        images['basecolor']=Image.composite(Image.new('RGB',(SIZE,SIZE),(65,59,45)),images['basecolor'],mask)
        images['roughness']=Image.composite(Image.new('L',(SIZE,SIZE),250),images['roughness'],mask)
        faded=Image.new('L',(SIZE,SIZE),0); fade_brush=ImageDraw.Draw(faded)
        fade_brush.polygon([(343,0),(644,0),(617,186),(679,392),(628,605),(666,825),(612,1023),(377,1023),(409,814),(350,612),(397,380),(363,172)],fill=72)
        faded=faded.filter(ImageFilter.GaussianBlur(48))
        images['basecolor']=Image.composite(Image.new('RGB',(SIZE,SIZE),(147,153,149)),images['basecolor'],faded)
    elif kind=='metal':
        mask=Image.new('L',(SIZE,SIZE),0); brush=ImageDraw.Draw(mask)
        for x,y in [(23,210),(21,475),(1007,682),(27,934)]:
            brush.polygon([(x-18,y-34),(x+9,y-23),(x+16,y+5),(x+7,y+39),(x-17,y+16)],fill=65)
        mask=mask.filter(ImageFilter.GaussianBlur(13))
        images['basecolor']=Image.composite(Image.new('RGB',(SIZE,SIZE),(83,64,42)),images['basecolor'],mask)
        images['roughness']=Image.composite(Image.new('L',(SIZE,SIZE),209),images['roughness'],mask)
        images['metallic']=Image.composite(Image.new('L',(SIZE,SIZE),45),images['metallic'],mask)
    if name in ('accord_standard','rift_standard'):
        emblem=ImageDraw.Draw(images['basecolor']); height=ImageDraw.Draw(images['height'])
        paths=([[(512,765),(512,330)],[(512,590),(430,540),(391,472)],[(512,529),(591,480),(625,412)],
                [(512,450),(451,399),(430,350)],[(512,387),(563,344),(582,301)],
                [(343,287),(373,239),(419,205),(468,184),(518,176),(568,186),(615,207),(652,240),(674,287)]]
               if name=='accord_standard' else [[(305,292),(506,495),(710,291)],[(349,462),(506,621),(669,459)],[(398,631),(507,744),(620,630)]])
        for path in paths:
            emblem.line(path,fill=(191,159,91),width=22,joint='curve')
            height.line(path,fill=141,width=22,joint='curve')
    images['height']=images['height'].filter(ImageFilter.GaussianBlur(.55))
    destination=ROOT/'textures'/'source'; destination.mkdir(parents=True,exist_ok=True)
    for channel,image in images.items(): image.save(destination/f'{name}_{channel}.png')
    return images


def main():
    source=json.loads((ROOT/'source'/'frontier_collection.json').read_text())
    (ROOT/'textures').mkdir(exist_ok=True)
    (ROOT/'textures'/'paint_records.json').write_text(json.dumps({'resolution':SIZE,'grain_paths':GRAIN,'knots':KNOTS,'end_checks':CHECKS,'hammer_marks':HAMMER,'canvas_hem_soil':HEM_SOIL,'canvas_runoff':RUNOFF,'end_weather':END_WEATHER,'materials':source['materials']},indent=2)+'\n')
    sheet=Image.new('RGB',(1280,320*((len(source['materials'])+4)//5)),(28,30,35)); draw=ImageDraw.Draw(sheet)
    for index,(name,material) in enumerate(source['materials'].items()):
        images=paint(name,material); x=index%5*256; y=index//5*320
        sheet.paste(images['basecolor'].resize((240,240)),(x+8,y+32)); draw.text((x+8,y+10),name,fill=(232,223,202))
        draw.text((x+8,y+281),'Original authored PBR strokes',fill=(159,164,174))
    sheet.save(ROOT/'textures'/'material_contact_sheet.png')
    print(f"Wrote original painted source maps and stroke records for {len(source['materials'])} materials.")


if __name__=='__main__': main()
