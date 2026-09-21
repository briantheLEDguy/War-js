"""Original city geography shared by layout, terrain imports and traversal fixtures."""
from bisect import bisect_right
from functools import lru_cache
import json
import math
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=1)
def source_map():
    return json.loads((ROOT / "public/assets/maps/aegis_capital.json").read_text())


@lru_cache(maxsize=1)
def elevation_runs():
    runs = source_map()["cityElevation"]["heightRuns"]
    return [row[0] for row in runs], [row[1] for row in runs]


def height(x, z):
    source = source_map()
    segments, size = source["cityElevation"]["segments"], source["size"]
    fx = min(segments, max(0, (x / size + .5) * segments))
    fz = min(segments, max(0, (z / size + .5) * segments))
    ix, iz = min(segments-1, int(fx)), min(segments-1, int(fz))
    tx, tz = fx-ix, fz-iz
    ends, values = elevation_runs()
    def sample(dx, dz):
        return values[bisect_right(ends, (iz+dz)*(segments+1)+ix+dx)]
    h00, h01, h10, h11 = sample(0,0), sample(0,1), sample(1,0), sample(1,1)
    # Match the diagonal used by the browser terrain and native terrain exporter.
    return h00 + tz*(h01-h00) + tx*(h11-h01) if tz >= tx else h00 + tx*(h10-h00) + tz*(h11-h10)


def point(p, offset=0):
    return [p["z"]*100, p["x"]*100, height(p["x"], p["z"])*100 + offset]


def sampled_path(path, spacing=1):
    result = []
    for a, b in zip(path["points"], path["points"][1:]):
        count = max(1, math.ceil(math.hypot(b["x"]-a["x"],b["z"]-a["z"])/spacing))
        for i in range(count):
            result.append({k: a[k]+(b[k]-a[k])*i/count for k in ["x","z"]})
    return result + [path["points"][-1]]


def road_surface():
    positions, indices, normals, uvs = [], [], [], []
    # Sample both length and width. A flat cross-section creates metre-high
    # overlapping lips at switchback corners on a slope.
    for path in source_map()["paths"]:
        samples = sampled_path(path)
        for a, b in zip(samples, samples[1:]):
            dx, dz = b["x"]-a["x"], b["z"]-a["z"]
            length = math.hypot(dx,dz)
            if length < 1e-6:
                continue
            width_steps = max(1, math.ceil(path["width"]))
            for strip in range(width_steps):
                left = path["width"]*(strip/width_steps-.5)
                right = path["width"]*((strip+1)/width_steps-.5)
                start = len(positions)
                for p, side in [(a,left),(a,right),(b,left),(b,right)]:
                    x,z = p["x"]-dz/length*side, p["z"]+dx/length*side
                    positions.append([z*100,x*100,height(x,z)*100+3])
                    normals.append([0,0,1]); uvs.append([x/3,z/3])
                indices.extend([start,start+2,start+1,start+1,start+2,start+3])
    return dict(positions=positions, indices=indices, normals=normals, uvs=uvs)


def mountain_surface():
    """Read the exact authored GLB mesh. Unsupported scene layouts fail closed."""
    data = (ROOT / "public/assets/models/prop_aegis_mountain_massif.glb").read_bytes()
    magic, version, total = struct.unpack_from("<III",data)
    if magic != 0x46546c67 or version != 2 or total != len(data):
        raise ValueError("Invalid authored mountain GLB")
    count, kind = struct.unpack_from("<II",data,12)
    doc = json.loads(data[20:20+count])
    binary_size, binary_kind = struct.unpack_from("<II",data,20+count)
    blob = data[28+count:28+count+binary_size]
    if kind != 0x4e4f534a or binary_kind != 0x004e4942 or len(doc["nodes"]) != 1 or doc["nodes"][0] != {"mesh":0,"name":"aegis_mountain_massif.001"}:
        raise ValueError("Mountain source scene changed; review its transforms before importing")
    def accessor(index):
        a = doc["accessors"][index]; view = doc["bufferViews"][a["bufferView"]]
        fmt = {5126:"f",5123:"H",5125:"I"}[a["componentType"]] * {"SCALAR":1,"VEC2":2,"VEC3":3}[a["type"]]
        offset = view.get("byteOffset",0)+a.get("byteOffset",0)
        stride = view.get("byteStride",struct.calcsize("<"+fmt))
        if "sparse" in a or view.get("buffer",0) != 0:
            raise ValueError("Unsupported mountain accessor")
        return [struct.unpack_from("<"+fmt,blob,offset+i*stride) for i in range(a["count"])]
    primitive, = doc["meshes"][0]["primitives"]
    p = primitive["attributes"]
    # Same source-to-Unreal axis conversion as the capital export.
    positions = [[z*100,x*100,y*100] for x,y,z in accessor(p["POSITION"])]
    normals = [[z,x,y] for x,y,z in accessor(p["NORMAL"])]
    images = []
    for image in doc["images"]:
        if "bufferView" in image:
            view = doc["bufferViews"][image["bufferView"]]
            start = view.get("byteOffset",0)
            content = blob[start:start+view["byteLength"]]
        else:
            file = (ROOT / "public/assets/models" / image["uri"]).resolve()
            if not file.is_relative_to((ROOT / "public/assets/textures").resolve()):
                raise ValueError("Mountain texture must remain in repository textures")
            content = file.read_bytes()
        images.append((image["mimeType"],content))
    source_indices = [i[0] for i in accessor(primitive["indices"])]
    indices = []
    for offset in range(0,len(source_indices),3):
        triangle = source_indices[offset:offset+3]
        a,b,c = [positions[i] for i in triangle]
        u,v = [b[i]-a[i] for i in range(3)],[c[i]-a[i] for i in range(3)]
        cross = [u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        # Two zero-area source triangles sit at the tapered massif edge. Native
        # mesh construction rejects them; removing them changes no visible face.
        if any(abs(n) >= .0001 for n in cross):
            indices.extend(triangle)
    return dict(positions=positions, normals=normals, uvs=[list(v) for v in accessor(p["TEXCOORD_0"])],
                indices=indices, removedDegenerateTriangles=(len(source_indices)-len(indices))//3), doc, images
