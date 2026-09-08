/** Real loopback movement/reconnect check against the running authority. */
import { WebSocket } from 'ws';
import { writeFile, mkdir } from 'node:fs/promises';
import { strict as assert } from 'node:assert';
import { CampaignConnection } from '../../../src/game/network/CampaignConnection';
import { campaignGroundHeight } from '../../../src/shared/orvr/navigation';

const origin='http://127.0.0.1:8788';
const health=await (await fetch(origin+'/health')).json();
assert.equal(health.authentication,'development-loopback','Only run against the local development authority');
const response=await fetch(origin+'/dev/session',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({realm:'aegis',name:'Navigation Review'})});
assert(response.ok);
const credentials=await response.json();
Object.assign(globalThis,{WebSocket});
const wait=(ms:number)=>new Promise(resolve=>setTimeout(resolve,ms));
const samples:{position:{x:number;y:number;z:number};error:number}[]=[];
const notices:string[]=[];
async function connect() {
  const connection=new CampaignConnection('ws://127.0.0.1:8788/orvr',credentials);
  connection.onNotice=notice=>notices.push(notice);
  connection.onSnapshot=snapshot=>{
    if(snapshot.self && snapshot.zone) samples.push({position:{...snapshot.self.position},
      error:Math.abs(snapshot.self.position.y-campaignGroundHeight(snapshot.zone.config,snapshot.self.position))});
  };
  connection.connect();
  for(let i=0;i<100&&!connection.snapshot?.self;i++)await wait(50);
  assert(connection.snapshot?.self,'Authority did not return a character snapshot');
  return connection;
}
let connection=await connect();
try {
  const first=connection.snapshot!;
  assert.equal(first.zone?.id,'sunmeadow_march');
  assert.equal(first.zone.config.objectives.length,3);
  assert.equal(first.zone.config.keeps.length,2);
  assert(first.zone.config.keeps.every(keep=>keep.gateFootprints?.outer?.height===4.8));
  const start={...first.self!.position};
  for(let i=0;i<50;i++) {
    assert(connection.send({type:'move',direction:{x:.8,z:.6}}));
    await wait(100);
  }
  assert(connection.send({type:'move',direction:{x:0,z:0}}));
  await wait(700);
  const end={...connection.snapshot!.self!.position};
  const travelled=Math.hypot(end.x-start.x,end.z-start.z);
  assert(travelled>20&&travelled<40,`Unexpected movement distance: ${travelled}`);
  const characterId=connection.snapshot!.self!.id;
  connection.close();await wait(100);
  connection=await connect();
  assert.equal(connection.snapshot!.self!.id,characterId);
  const restored=connection.snapshot!.self!.position;
  assert(Math.hypot(restored.x-end.x,restored.y-end.y,restored.z-end.z)<.001);
  assert.equal(notices.length,0,notices.join('; '));
  const maxGroundError=Math.max(...samples.map(sample=>sample.error));
  assert(maxGroundError<.00001,`Ground disagreement: ${maxGroundError}`);
  const result={status:'passed',campaignId:connection.snapshot!.campaignId,zoneId:first.zone.id,
    objectiveCount:3,keepCount:2,start,end,travelledMetres:travelled,snapshotCount:samples.length,
    maxGroundError,reconnectPositionPreserved:true,notices,
    scope:'Actual running loopback socket movement and reconnect; raised-floor cases have separate focused tests.'};
  await mkdir('artifacts/orvr',{recursive:true});
  await writeFile('artifacts/orvr/shared-navigation-live-review.json',JSON.stringify(result,null,2)+'\n');
  console.info(JSON.stringify(result,null,2));
} finally {connection.close();}
