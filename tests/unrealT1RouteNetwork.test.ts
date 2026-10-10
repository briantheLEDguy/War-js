import {expect,it} from 'vitest';
import {curveRouteNetwork,mapRouteEdges,projectRouteJoin,routeEdgeKey} from '../scripts/unreal/t1-route-network';
const routes=()=>[
 {id:'advance',width:12,points:[{x:-100,z:0,y:10},{x:0,z:0,y:12},{x:100,z:0,y:10}]},
 {id:'ridge',width:12,points:[{x:-100,z:0,y:10},{x:-100,z:100,y:20},{x:0,z:100,y:25},{x:100,z:100,y:20},{x:100,z:0,y:10}]},
 {id:'rotation',width:12,points:[{x:0,z:100,y:25},{x:0,z:0,y:12},{x:0,z:-100,y:10}]},
];
const moves=[{from:{x:0,z:100},to:{x:30,z:130}}];
it('constructs each shared edge once and preserves exact reversed supply geometry',()=>{
 const input=routes(),copy=structuredClone(input),network=curveRouteNetwork(input,moves);
 expect(input).toEqual(copy);expect(network.curves).toHaveLength(8);expect(network.routes.map(r=>r.width)).toEqual([12,12,12]);
 const ridge=network.routes[1];expect(ridge.points.some(p=>p.x===30&&p.z===130&&p.y===25)).toBe(true);
 const reverse=mapRouteEdges([...input[1].points].reverse(),network.curves);
 expect(reverse).toEqual([...ridge.points].reverse());reverse[0].x=900;expect(ridge.points.at(-1)!.x).toBe(100);
});
it('freezes complete approach edges including their authored vertex density',()=>{
 const input=routes(),frozen=input[0].points.slice(1).map((p,i)=>routeEdgeKey(p,input[0].points[i]));
 const n=curveRouteNetwork(input,moves,frozen);expect(n.routes[0]).toEqual(input[0]);
 expect(()=>curveRouteNetwork(input,[{from:{x:0,z:0},to:{x:1,z:0}}],frozen)).toThrow('Frozen route edge cannot move');
 expect(()=>curveRouteNetwork(input,[],['missing'])).toThrow('Frozen route edge is absent');
});
it('projects a secondary join by the original edge parameter without changing vertical control',()=>{
 const n=curveRouteNetwork(routes(),moves),curve=n.curves.find(c=>routeEdgeKey(c.start,c.end)===routeEdgeKey({x:-100,z:100},{x:0,z:100}))!;
 const p=projectRouteJoin({x:-50,z:100,y:21},n.curves),f=(curve.points.length-1)/2,i=Math.floor(f),u=f-i;
 expect(p.x).toBeCloseTo(curve.points[i].x+(curve.points[i+1].x-curve.points[i].x)*u,12);
 expect(p.z).toBeCloseTo(curve.points[i].z+(curve.points[i+1].z-curve.points[i].z)*u,12);expect(p.y).toBe(21);
 expect(projectRouteJoin({x:250,z:250,y:9},n.curves)).toEqual({x:250,z:250,y:9});
 expect(projectRouteJoin({x:-50,z:100,y:21},JSON.parse(JSON.stringify(n.curves)))).toEqual(p);
});
it('retains unrelated edge geometry and bounds curve sampling inventories',()=>{
 const n=curveRouteNetwork(routes(),moves),p=[{x:300,z:300,y:4},{x:320,z:320,y:6}];
 expect(mapRouteEdges(p,n.curves)).toEqual(p);expect(mapRouteEdges(p,n.curves)[0]).not.toBe(p[0]);
 expect(()=>curveRouteNetwork([{id:'huge',points:[{x:0,z:0},{x:100000,z:0}]}],[],[],2)).toThrow('sampling budget');
 for(const spacing of [1,41,NaN])expect(()=>curveRouteNetwork(routes(),[],[],spacing)).toThrow('inventory');
});
it('rejects missing, duplicate, merged and nonfinite relocation controls',()=>{
 for(const list of [[{from:{x:99,z:99},to:{x:0,z:0}}],[...moves,...moves],[{from:{x:0,z:100},to:{x:0,z:0}}],[{from:{x:0,z:100},to:{x:NaN,z:0}}]])expect(()=>curveRouteNetwork(routes(),list)).toThrow();
 expect(()=>curveRouteNetwork([...routes(),routes()[0]],[])).toThrow('inventory');
 const invalid=routes();invalid[2].points[1].y=40;expect(()=>curveRouteNetwork(invalid,[])).toThrow('junction elevations differ');
 expect(()=>curveRouteNetwork([{id:'zero',points:[{x:0,z:0},{x:0,z:0}]}],[])).toThrow('Zero-length');
 expect(()=>projectRouteJoin({x:0,z:0},[],Infinity)).toThrow('projection');
});
