import { expect, test } from 'vitest';
import { addPlayer, advanceSimulation, createCampaign, defaultZoneConfig, keepPosterns, nearbyKeepPostern, posternExitFor, submitCommand } from '../src/shared/orvr';
import type { PlayerAction, Realm } from '../src/shared/orvr';

function setup(realm: Realm = 'aegis') {
  const config = defaultZoneConfig('sunmeadow_march');
  const keepConfig = config.keeps[0];
  keepConfig.postern = { outside: { x: keepConfig.position.x + 24, y: 0, z: 35 }, inside: { x: keepConfig.position.x + 24, y: 0, z: 28 }, interactionRadius: 3 };
  config.collision = [{ minX: keepConfig.position.x - 32, maxX: keepConfig.position.x + 32, minZ: 30.9, maxZ: 33.1 }];
  const state = createCampaign({ zones: [config] });
  addPlayer(state, { id: 'a', userId: 'u', characterId: 'c', realm, zoneId: config.id });
  const zone = state.zones[config.id], player = state.players.a;
  for (const npc of Object.values(zone.npcs)) npc.health = 0;
  const keep = zone.keeps[keepConfig.id];
  player.position = { ...keepConfig.postern.outside };
  const command = (action: PlayerAction = { type: 'postern', keepId: keep.id }, activationId = zone.activationId) => submitCommand(state, player.id, {
    version: 1, sequence: player.lastSequence + 1, activationId, action,
  });
  return { state, zone, player, keep, config: zone.config, postern: zone.config.keeps[0].postern!, command };
}

test('the owning realm traverses only the fixed rear landings while siege gates remain closed', () => {
  const { state, player, keep, postern, command } = setup();
  player.direction = { x: 1, z: 1 };
  const result = command({ type: 'postern', keepId: keep.id, destination: { x: 500, y: 500, z: 500 } } as PlayerAction);
  expect(result.ok).toBe(true); expect(result.events[0].type).toBe('postern_used');
  expect(player.position).toEqual(postern.inside); expect(player.position).not.toBe(postern.inside);
  expect(player.direction).toEqual({ x: 0, z: 0 });
  expect(keep.gates.outer.health).toBe(keep.gates.outer.maxHealth); expect(keep.gates.inner.health).toBe(keep.gates.inner.maxHealth);
  expect(command().code).toBe('postern_cooldown');
  advanceSimulation(state, 1.1);
  expect(command().ok).toBe(true); expect(player.position).toEqual(postern.outside);
});

test('enemy players and a previous owner after capture cannot use the postern', () => {
  const enemy = setup('riftbound'); expect(enemy.command().code).toBe('invalid_keep');
  const former = setup(); former.keep.owner = 'riftbound';
  expect(former.command().code).toBe('invalid_keep'); expect(former.player.position).toEqual(former.postern.outside);
  const newOwner = setup('riftbound'); newOwner.keep.owner = 'riftbound';
  expect(newOwner.command().ok).toBe(true);
});

test('server proximity uses all three coordinates and checks stale zone activation', () => {
  const game = setup(); game.player.position.z += 3.01;
  expect(game.command().code).toBe('out_of_range');
  game.player.position = { ...game.postern.outside, y: 4 };
  expect(game.command().code).toBe('out_of_range');
  game.player.position = { ...game.postern.outside };
  expect(game.command(undefined, 'earlier-activation').code).toBe('stale_activation');
});

test('dead, queued, inactive and controlled players cannot bypass their movement restrictions', () => {
  const dead = setup(); dead.player.health = 0; expect(dead.command().code).toBe('player_defeated');
  const queued = setup(); queued.player.queued = true; expect(queued.command().code).toBe('queued');
  const staging = setup(); staging.zone.status = 'staging'; expect(staging.command().code).toBe('zone_not_active');
  const controlled = setup(); controlled.player.statuses = [{ id: 'root', kind: 'root', expiresAt: 10, magnitude: 1, sourceId: 'enemy' }];
  expect(controlled.command().code).toBe('controlled_player');
  const mounted = setup(); mounted.player.equipmentId = 'ram'; expect(mounted.command().code).toBe('operating_equipment');
});

test('blocked or occupied destinations reject instead of searching for a different teleport location', () => {
  const blocked = setup(); blocked.config.collision!.push({ minX: blocked.postern.inside.x - 1, maxX: blocked.postern.inside.x + 1, minZ: 27, maxZ: 29 });
  expect(blocked.command().code).toBe('postern_blocked');
  expect(blocked.player.position).toEqual(blocked.postern.outside);
  const occupied = setup();
  addPlayer(occupied.state, { id: 'b', userId: 'b', characterId: 'b', realm: 'riftbound', zoneId: occupied.zone.id });
  occupied.state.players.b.position = { ...occupied.postern.inside };
  expect(occupied.command().code).toBe('postern_occupied');
  expect(occupied.player.position).toEqual(occupied.postern.outside);
});

test('the UI proximity helper identifies exactly one server-configured side', () => {
  const { postern } = setup();
  expect(posternExitFor(postern, postern.outside)).toEqual(postern.inside);
  expect(posternExitFor(postern, postern.inside)).toEqual(postern.outside);
  expect(posternExitFor(postern, { ...postern.inside, z: 31.5 })).toBeNull();
  expect(posternExitFor(undefined, postern.outside)).toBeNull();
});

test('invalid authored postern coordinates/radii fail campaign startup', () => {
  const { config } = setup();
  config.keeps[0].postern!.inside.x = Infinity;
  expect(() => createCampaign({ zones: [config] })).toThrow('Invalid postern');
});

test('named outer and inner entrances enforce their own proximity and preserve closed siege gates', () => {
  const game=setup();
  const config=game.config.keeps[0];
  config.posterns=[{...game.postern,id:'outer',label:'Outer gate passage'},
    {id:'inner',label:'Inner gate passage',outside:{x:config.position.x,y:0,z:16},
      inside:{x:config.position.x,y:0,z:10},interactionRadius:2}];
  expect(keepPosterns(config)).toHaveLength(2);
  expect(nearbyKeepPostern(config,game.player.position)?.id).toBe('outer');
  expect(game.command({type:'postern',keepId:game.keep.id,posternId:'forged'}).code).toBe('invalid_postern');
  expect(game.command({type:'postern',keepId:game.keep.id,posternId:'inner'}).code).toBe('out_of_range');
  expect(game.command({type:'postern',keepId:game.keep.id,posternId:'outer'}).events[0].data.posternId).toBe('outer');
  expect(game.player.position).toEqual(config.posterns[0].inside);
  advanceSimulation(game.state,1.1);
  game.player.position={...config.posterns[1].outside};
  expect(nearbyKeepPostern(config,game.player.position)?.id).toBe('inner');
  expect(game.command({type:'postern',keepId:game.keep.id,posternId:'outer'}).code).toBe('out_of_range');
  expect(game.command({type:'postern',keepId:game.keep.id,posternId:'inner'}).ok).toBe(true);
  expect(game.player.position).toEqual(config.posterns[1].inside);
  expect(game.keep.gates.outer.health).toBe(1000);expect(game.keep.gates.inner.health).toBe(1000);
  advanceSimulation(game.state,1.1);game.keep.owner='riftbound';
  expect(game.command({type:'postern',keepId:game.keep.id,posternId:'inner'}).code).toBe('invalid_keep');
});

test('named lists reject duplicate or missing IDs and supersede their legacy alias', () => {
  const game=setup();const config=game.config.keeps[0];
  config.posterns=[];
  expect(keepPosterns(config)).toEqual([]);expect(game.command().code).toBe('invalid_keep');
  config.posterns=[{...game.postern,id:'same'},{...game.postern,id:'same'}];
  expect(()=>createCampaign({zones:[game.config]})).toThrow('Invalid postern identities');
  config.posterns=[{...game.postern,id:''}];
  expect(()=>createCampaign({zones:[game.config]})).toThrow('Invalid postern identities');
});
