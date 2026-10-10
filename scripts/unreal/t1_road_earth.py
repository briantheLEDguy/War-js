"""Soft settlement-to-earth road weights; helpers reuse the admitted stochastic texture sampler."""
import copy,math

RECIPE=dict(farSoil=.55,settlementSuppression=.8,villageRange=[75,150],keepRange=[30,75],
    patchMetres=19,patchStrength=.18,macroMetres=47,macroMinimum=.8,macroRange=.24,
    stoneTileMetres=2.8,soilTileMetres=3.2,stoneTint=[.78,.79,.72],soilTint=[.85,.85,.8],normalStrength=.35)


def road_earth_recipe(identity):
    return copy.deepcopy(RECIPE) if identity=='sunmeadow_march' else None


def validate_recipe(r):
    if not isinstance(r,dict) or set(r)!=set(RECIPE):raise ValueError('Invalid road earth controls')
    for key,value in r.items():
        values=value if isinstance(value,list) else [value]
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in values):raise ValueError('Nonfinite road earth control')
    for key in ('villageRange','keepRange'):
        if len(r[key])!=2 or not 1<=r[key][0]<r[key][1]<=200:raise ValueError('Invalid road transition range')
    for key in ('stoneTint','soilTint'):
        if len(r[key])!=3 or any(not 0<=v<=2 for v in r[key]):raise ValueError('Invalid road tint')
    for key in ('farSoil','settlementSuppression','patchStrength','macroMinimum','macroRange','normalStrength'):
        if not 0<=r[key]<=1:raise ValueError('Unbounded road earth mix')
    for key in ('stoneTileMetres','soilTileMetres'):
        if not .5<=r[key]<=12:raise ValueError('Invalid road texture scale')
    for key in ('patchMetres','macroMetres'):
        if not 8<=r[key]<=120:raise ValueError('Invalid road variation scale')


def road_earth_weights(village_distance,keep_distance,patch,macro,recipe=None):
    r=RECIPE if recipe is None else recipe;validate_recipe(r)
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (village_distance,keep_distance,patch,macro)) or min(village_distance,keep_distance)<0 or not 0<=patch<=1 or not 0<=macro<=1:raise ValueError('Invalid road earth sample')
    def transition(distance,limits):
        t=max(0,min(1,(distance-limits[0])/(limits[1]-limits[0])));return 1-t*t*(3-2*t)
    near=max(transition(village_distance,r['villageRange']),transition(keep_distance,r['keepRange']))
    soil=max(0,min(1,r['farSoil']+r['patchStrength']*(patch-.5)))*(1-near*r['settlementSuppression'])
    return dict(soil=soil,macro=r['macroMinimum']+r['macroRange']*macro)


def road_earth_shaders(colour_source,normal_source,recipe=None):
    r=RECIPE if recipe is None else recipe;validate_recipe(r)
    helpers=[]
    for source in (colour_source,normal_source):
        prefix,separator,_=source.partition('};SampleHelper h;')
        if not separator or prefix.count('float noise(float2 p)')!=1 or prefix.count('struct SampleHelper')!=1:raise ValueError('Road sampler must supply exactly one admitted noise helper')
        helpers.append(prefix+'};SampleHelper h;')
    a,b=r['villageRange'];c,d=r['keepRange']
    weights=f'''
float2 p=float2(P.y,-P.x)/100;
float nearVillage=1-smoothstep({a},{b},distance(p,float2(Village.y,-Village.x)/100));
float nearKeep=1-smoothstep({c},{d},min(distance(p,float2(KeepA.y,-KeepA.x)/100),distance(p,float2(KeepB.y,-KeepB.x)/100)));
float soil=saturate({r['farSoil']}+{r['patchStrength']}*(h.noise(p/{r['patchMetres']})-.5))*(1-max(nearVillage,nearKeep)*{r['settlementSuppression']});
'''
    tint=lambda key:','.join(map(str,r[key]))
    colour=helpers[0]+weights+f'''
float3 stone=h.sample(Stone,StoneSampler,p/{r['stoneTileMetres']})*float3({tint('stoneTint')});
float3 earth=h.sample(Soil,SoilSampler,p/{r['soilTileMetres']})*float3({tint('soilTint')});
return lerp(stone,earth,soil)*({r['macroMinimum']}+{r['macroRange']}*h.noise(p/{r['macroMetres']}));
'''
    normal=helpers[1]+weights+f'''
float3 n=normalize(lerp(h.sample(StoneNormal,StoneNormalSampler,p/{r['stoneTileMetres']}),h.sample(SoilNormal,SoilNormalSampler,p/{r['soilTileMetres']}),soil));
return normalize(float3(n.xy*{r['normalStrength']},n.z));
'''
    return colour,normal
