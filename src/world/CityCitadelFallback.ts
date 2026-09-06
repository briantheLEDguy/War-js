import * as THREE from 'three';

const sizes: Record<string, [number, number, number]> = {
  throne:[10,8,10], oath_statue:[4,4,8], war_table:[6,4,2], arms_rack:[5,2,3.5],
  provision_rack:[5,2,3], bunk:[3,5,3], hearth:[6,3,6], feast_table:[7,3,1.7],
  archive:[5,1.5,5], counting_desk:[4,2.5,2], treasury:[5,4,3.5], reliquary:[3,3,5],
  chandelier:[8,8,3], tapestry:[5,.4,8],
};

/** Keep missing decorations at their authored scale, with matching mounting origins. */
export function citadelDecorationFallback(kind: string): THREE.Group | null {
  if (!kind.startsWith('aegis_citadel_')) return null;
  const name = kind.slice('aegis_citadel_'.length), dimensions = sizes[name];
  if (!dimensions) return null;
  const [w,d,h] = dimensions, group = new THREE.Group();
  const material = new THREE.MeshStandardMaterial({color:name==='tapestry'?0x702f25:0x544d3b,roughness:.75});
  const box = (width: number, height: number, depth: number, x=0, y=height/2, z=0) => {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(width,height,depth),material);
    mesh.position.set(x,y,z); group.add(mesh);
  };
  if (name==='throne') {
    for (let i=0;i<3;i++) box(w,.3,8-i,0,.15+i*.3,-i*.5);
    box(5,5,1,0,3.4,-2.8); box(4,1,3,0,1.8,-1.4);
    for (const x of [-3.3,3.3]) box(.6,9,.6,x,5,-2.6);
    box(8,.6,4,0,9.6,-1.8);
  } else if (name==='oath_statue') {
    box(4,1.5,4); box(1.7,4,1.2,0,3.5); box(1.2,1.2,1.2,0,6.5);
    box(2,2.8,.3,.7,3.6,.85);
  } else if (name==='chandelier') {
    for (const [radius,y] of [[3.7,.6],[2.5,2]]) {
      const ring=new THREE.Mesh(new THREE.TorusGeometry(radius,.13,6,24),material);
      ring.rotation.x=Math.PI/2; ring.position.y=y; group.add(ring);
    }
    box(.12,3,.12);
  } else if (name==='tapestry') {
    box(w,h,d); box(w+.2,.15,d+.1,0,h);
  } else if (name==='bunk') {
    for (const y of [.5,2]) box(w,.3,d,0,y);
    for (const x of [-1.3,1.3]) for (const z of [-2.3,2.3]) box(.15,h,.15,x,h/2,z);
  } else if (['war_table','feast_table','counting_desk'].includes(name)) {
    box(w,.3,d,0,h-.15);
    for (const x of [-w*.4,w*.4]) for (const z of [-d*.35,d*.35]) box(.22,h-.3,.22,x,(h-.3)/2,z);
  } else if (name==='reliquary') {
    box(w,1,d); box(w*.75,h-1,d*.75,0,(h+1)/2);
  } else box(w,h,d);
  return group;
}
