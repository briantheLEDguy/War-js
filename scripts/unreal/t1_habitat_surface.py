"""Continuous world-space habitat masks; reviewed textures remain the visible detail channels."""
import math

SEEDS=dict(sunmeadow_march=14713,cinderfen_outskirts=27431)
HABITAT_SHADER='''struct T1HabitatNoise
{
    uint hash(int2 p, uint seed)
    {
        uint h = asuint(p.x) * 1597334677u ^ asuint(p.y) * 3812015801u ^ seed;
        h ^= h >> 16; h *= 2246822519u; h ^= h >> 13; h *= 3266489917u; h ^= h >> 16;
        return h;
    }
    float value(float2 p, uint seed)
    {
        int2 i = int2(floor(p)); float2 f = frac(p); f = f*f*(3.0-2.0*f);
        float a = float(hash(i, seed) >> 8) / 16777215.0;
        float b = float(hash(i+int2(1,0), seed) >> 8) / 16777215.0;
        float c = float(hash(i+int2(0,1), seed) >> 8) / 16777215.0;
        float d = float(hash(i+int2(1,1), seed) >> 8) / 16777215.0;
        return lerp(lerp(a,b,f.x),lerp(c,d,f.x),f.y);
    }
};
T1HabitatNoise n; uint seed = uint(Seed);
float2 warped = P + (float2(n.value(P/83.0,seed+17u),n.value(P/83.0,seed+31u))-.5)*22.0;
return saturate(float3(n.value(warped/23.0,seed+47u),n.value(warped/79.0,seed+59u),n.value(warped/9.0,seed+71u)));'''


def habitat_recipe(identity):
    if identity not in SEEDS:raise ValueError('Habitat masks require a reviewed first-pair region')
    return dict(seed=SEEDS[identity],shoreMinimumMetres=.65,shoreMaximumMetres=1.6,wetRoughness=.6)


def validate_habitat(row):
    if row not in [habitat_recipe(z) for z in SEEDS]:raise ValueError('Habitat controls differ from a reviewed regional recipe')


def _hash(x,z,seed):
    h=((x&0xffffffff)*1597334677 ^ (z&0xffffffff)*3812015801 ^ seed)&0xffffffff
    h^=h>>16;h=(h*2246822519)&0xffffffff;h^=h>>13;h=(h*3266489917)&0xffffffff;h^=h>>16
    return (h>>8)/16777215


def _noise(x,z,seed):
    ix,iz=math.floor(x),math.floor(z);a,b=x-ix,z-iz;a=a*a*(3-2*a);b=b*b*(3-2*b)
    low=_hash(ix,iz,seed)*(1-a)+_hash(ix+1,iz,seed)*a
    high=_hash(ix,iz+1,seed)*(1-a)+_hash(ix+1,iz+1,seed)*a
    return low*(1-b)+high*b


def habitat_masks(x,z,identity):
    if any(not math.isfinite(v) or abs(v)>5000 for v in (x,z)):raise ValueError('Invalid habitat sample')
    seed=habitat_recipe(identity)['seed'];u=x+(_noise(x/83,z/83,seed+17)-.5)*22;v=z+(_noise(x/83,z/83,seed+31)-.5)*22
    return [_noise(u/scale,v/scale,seed+salt) for scale,salt in [(23,47),(79,59),(9,71)]]


def habitat_shore_band(delta,moisture,identity):
    if not math.isfinite(delta) or not math.isfinite(moisture) or not 0<=moisture<=1:raise ValueError('Invalid shore moisture sample')
    r=habitat_recipe(identity);width=r['shoreMinimumMetres']+(r['shoreMaximumMetres']-r['shoreMinimumMetres'])*moisture
    t=max(0,min(1,1-max(0,delta)/width));return t*t*(3-2*t)
