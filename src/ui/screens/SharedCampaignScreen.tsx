import { useEffect, useRef, useState } from 'react';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { CampaignConnection, campaignHttpUrl, type CampaignCredentials, type ConnectionStatus } from '../../game/network/CampaignConnection';
import { SharedCampaignRenderer } from '../../game/network/SharedCampaignRenderer';
import { getCareerAbilityKit } from '../../game/abilities/abilityData';
import type { PlayerAction, Realm, WorldSnapshot } from '../../shared/orvr/protocol';
import { nearbyKeepPostern } from '../../shared/orvr/postern';
import { equipmentOperatorPosition } from '../../shared/orvr/equipment';

const serverUrl = import.meta.env.VITE_ORVR_SERVER_URL ?? 'ws://127.0.0.1:8788/orvr';
const realmName = (realm: Realm | null) => realm === 'aegis' ? 'Aegis Accord' : realm === 'riftbound' ? 'Riftbound Host' : 'Neutral';
const title = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase());
const metres = (a: { x: number; y?: number; z: number }, b: { x: number; y?: number; z: number }) => Math.hypot(a.x - b.x, (a.y ?? 0) - (b.y ?? 0), a.z - b.z);

export function SharedCampaignScreen() {
  const canvas = useRef<HTMLDivElement>(null);
  const connection = useRef<CampaignConnection | null>(null);
  const renderer = useRef<SharedCampaignRenderer | null>(null);
  const database = useRef<SupabaseClient | null>(null);
  const mounted = useRef(false);
  const joinRequest = useRef<AbortController | null>(null);
  const [authentication, setAuthentication] = useState<string>('checking');
  const [healthAttempt, setHealthAttempt] = useState(0);
  const [credentials, setCredentials] = useState<CampaignCredentials | null>(null);
  const [realm, setRealm] = useState<Realm>('aegis');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [artNotice, setArtNotice] = useState('');
  const [status, setStatus] = useState<ConnectionStatus>('closed');
  const [snapshot, setSnapshot] = useState<WorldSnapshot | null>(null);
  const [target, setTarget] = useState<string | null>(null);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; joinRequest.current?.abort(); };
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setAuthentication('checking');
    const timeout = setTimeout(() => {
      controller.abort(); setAuthentication('offline'); setNotice('The campaign server did not respond. Try connecting again.');
    }, 10000);
    Promise.resolve().then(() => fetch(`${campaignHttpUrl(serverUrl)}/health`, { signal: controller.signal }))
      .then(response => { if (!response.ok) throw new Error('Campaign server is recovering.'); return response.json(); })
      .then(health => {
        if (!['development-loopback', 'supabase'].includes(health?.authentication)) throw new Error('The campaign server has an unsupported sign-in configuration.');
        if (!controller.signal.aborted) { setAuthentication(health.authentication); setNotice(''); }
      })
      .catch(error => { if (!controller.signal.aborted) { setAuthentication('offline'); setNotice(error instanceof Error ? error.message : 'The campaign server is unavailable.'); } })
      .finally(() => clearTimeout(timeout));
    return () => { clearTimeout(timeout); controller.abort(); };
  }, [healthAttempt]);
  useEffect(() => {
    if (!credentials || !canvas.current) return;
    const transport = new CampaignConnection(serverUrl, credentials);
    connection.current = transport;
    let world: SharedCampaignRenderer;
    try { world = new SharedCampaignRenderer(canvas.current, transport); }
    catch {
      transport.close(); connection.current = null; setCredentials(null);
      setNotice('WebGL could not start. Check your browser graphics settings.'); return;
    }
    renderer.current = world;
    world.onNotice = setArtNotice; world.onTarget = setTarget;
    let activation: string | undefined;
    transport.onSnapshot = next => {
      if (activation !== next.zone?.activationId) { activation = next.zone?.activationId; setTarget(null); }
      setSnapshot(next); world.update(next);
    };
    transport.onStatus = next => {
      setStatus(next);
      if (next === 'closed') { setCredentials(null); setSnapshot(null); setTarget(null); }
    };
    transport.onNotice = setNotice;
    const subscription = database.current?.auth.onAuthStateChange((event, session) => {
      if (event === 'TOKEN_REFRESHED' && session) transport.updateToken(session.access_token);
      if (event === 'SIGNED_OUT') { setNotice('Sign in again to resume the campaign.'); transport.close(); }
    }).data.subscription;
    transport.connect();
    return () => {
      subscription?.unsubscribe();
      transport.onSnapshot = () => undefined; transport.onStatus = () => undefined; transport.onNotice = () => undefined;
      world.onNotice = () => undefined; world.onTarget = () => undefined;
      transport.close(); world.dispose();
      if (connection.current === transport) connection.current = null;
      if (renderer.current === world) renderer.current = null;
    };
  }, [credentials]);
  const send = (action: PlayerAction) => {
    setNotice(connection.current?.send(action) ? '' : 'Waiting for the campaign connection or zone handoff.');
  };
  const join = async () => {
    if (joinRequest.current || !['development-loopback', 'supabase'].includes(authentication)) return;
    const controller = new AbortController();
    joinRequest.current = controller;
    const active = () => mounted.current && !controller.signal.aborted;
    setBusy(true); setNotice('');
    try {
      if (authentication === 'development-loopback') {
        const response = await fetch(`${campaignHttpUrl(serverUrl)}/dev/session`, {
          method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ realm, name }), signal: controller.signal,
        });
        if (!response.ok) throw new Error('Unable to create a campaign session.');
        const session = await response.json();
        if (typeof session?.token !== 'string' || !session.token || typeof session?.characterId !== 'string' || !session.characterId) throw new Error('The campaign server returned an invalid session.');
        if (active()) setCredentials(session);
      } else {
        const url = import.meta.env.VITE_ORVR_SUPABASE_URL;
        const key = import.meta.env.VITE_ORVR_SUPABASE_PUBLISHABLE_KEY;
        if (!url || !key) throw new Error('Campaign sign-in has not been configured for this build.');
        database.current ??= createClient(url, key);
        const client = database.current;
        const { data: auth, error } = await client.auth.signInWithPassword({ email, password });
        if (!active()) return;
        setPassword('');
        if (error || !auth.session) throw new Error(error?.message ?? 'Sign-in failed.');
        const { data: characters, error: readError } = await client.from('orvr_characters').select('id,realm').order('created_at').limit(1);
        if (!active()) return;
        if (readError) throw readError;
        let characterId: string | undefined = characters?.[0]?.id;
        if (!characterId) {
          const { data, error: createError } = await client.rpc('create_orvr_character', { p_name: name, p_realm: realm });
          if (!active()) return;
          if (createError) throw createError;
          characterId = data;
        }
        if (!characterId) throw new Error('No campaign recruit could be found.');
        setCredentials({ token: auth.session.access_token, characterId });
      }
    } catch (error) { if (active()) setNotice(error instanceof Error ? error.message : 'Unable to join the campaign.'); }
    finally { if (joinRequest.current === controller) joinRequest.current = null; if (active()) setBusy(false); }
  };
  const self = snapshot?.self;
  const zone = snapshot?.zone;
  const abilities = getCareerAbilityKit(self?.className).abilities.filter(ability => self?.abilityIds?.includes(ability.id));
  const targetEntity = snapshot?.players.find(player => player.id === target) ?? (target && zone ? zone.npcs[target] ?? zone.equipment[target] ?? zone.caravans[target] : null);
  const ownKeeps = zone ? Object.values(zone.keeps).filter(keep => keep.owner === self?.realm) : [];
  const nearKeep = zone && self ? zone.config.keeps.find(keep => metres(keep.quartermaster, self.position) <= 12 && zone.keeps[keep.id]?.owner === self.realm) : null;
  const nearObjective = zone && self ? zone.config.objectives.find(objective => metres(objective.position, self.position) <= 12 && zone.objectives[objective.id]?.owner === self.realm) : null;
  const nearEquipment = zone && self ? Object.values(zone.equipment).filter(machine => machine.health > 0 && machine.realm === self.realm && metres(equipmentOperatorPosition(machine), self.position) <= 6) : [];
  const nearPostern = zone && self && zone.status === 'active' && !self.equipmentId
    ? zone.config.keeps.flatMap(keep => {
      const postern = zone.keeps[keep.id]?.owner === self.realm ? nearbyKeepPostern(keep, self.position) : undefined;
      return postern ? [{ keep, postern }] : [];
    })[0] : undefined;
  return <main className="shared-campaign">
    <div className="shared-world" ref={canvas} />
    {!credentials ? <section className="shared-entry">
      <span className="shared-eyebrow">AEGIS ACCORD · RIFTBOUND HOST</span>
      <h1>The contested frontier</h1>
      <p>Three battlefield objectives. Two keeps. One advancing campaign.</p>
      <p className="shared-muted">Campaign playtest · larger landscapes and replacement art are in production.</p>
      <form onSubmit={event => { event.preventDefault(); void join(); }}>
        <label>Recruit name<input value={name} onChange={event => setName(event.target.value)} minLength={2} maxLength={32} required placeholder="Your name on the frontier" autoComplete="nickname" /></label>
        <label>Realm<select value={realm} onChange={event => setRealm(event.target.value as Realm)}><option value="aegis">Aegis Accord</option><option value="riftbound">Riftbound Host</option></select></label>
        {authentication === 'supabase' && <><label>Email<input type="email" required autoComplete="username" value={email} onChange={event => setEmail(event.target.value)} /></label><label>Password<input type="password" required autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)} /></label></>}
        <button disabled={busy || authentication === 'checking' || authentication === 'offline'}>{busy ? 'Joining…' : authentication === 'checking' ? 'Finding campaign…' : 'Enter the campaign'}</button>
      </form>
      {authentication === 'offline' && <button onClick={() => setHealthAttempt(value => value + 1)}>Retry connection</button>}
      <p role="status">{notice}</p><a href={import.meta.env.BASE_URL}>Return to character selection</a>
    </section> : <>
      <header className="shared-header"><div><span className="shared-eyebrow">{realmName(self?.realm ?? realm)} · ROUND {snapshot?.round ?? 1}</span><h1>{zone ? title(zone.id) : 'Entering the frontier…'}</h1></div><div className="shared-connection"><span>{status}</span><button onClick={() => { setCredentials(null); setSnapshot(null); }}>Leave campaign</button></div></header>
      {zone && self && <>
        <aside className="shared-orders">
          <h2>{zone.status === 'staging' ? `Muster · ${Math.ceil(zone.stagingRemaining)}s` : zone.status === 'active' ? 'Campaign orders' : 'Quiet frontier'}</h2>
          <p>Hold both keeps to advance the front. Escort supplies to fund your siege.</p>
          {zone.config.objectives.map(objective => { const state = zone.objectives[objective.id]; return <div className="shared-objective" key={objective.id}><b>{title(objective.id.replace(`${zone.id}_`, ''))}</b><span>{realmName(state?.owner ?? null)} · {Math.round(metres(self.position, objective.position))}m</span>{state?.capturingRealm && <progress value={state.captureSeconds} max={30} />}{state?.readyShipment && <em>Shipment ready</em>}</div>; })}
          {Object.values(zone.keeps).map(keep => <div className="shared-objective" key={keep.id}><b>{realmName(keep.owner)} keep · Level {keep.level}</b><span>{keep.supplies} supplies · {keep.deliveredSupplies} delivered</span><span>Outer {Math.ceil(keep.gates.outer.health / 10)}% · Inner {Math.ceil(keep.gates.inner.health / 10)}%</span></div>)}
          <details><summary>Travel to a front</summary>{snapshot.fronts.filter(front => !front.locked && front.zoneId).map(front => <button key={front.pairing} onClick={() => send({ type: 'transfer', zoneId: front.zoneId! })}>{title(front.pairing)} · {title(front.zoneId!)}</button>)}</details>
        </aside>
        <aside className="shared-map-panel"><CampaignMap snapshot={snapshot} /><span>{Math.round(self.position.x)}, {Math.round(self.position.z)} · {((zone.config.bounds.maxX - zone.config.bounds.minX) / 1000).toFixed(1)} km landscape</span><p>{artNotice}</p></aside>
        <section className="shared-action-panel">
          <div className="shared-vitals"><b>{self.displayName} · {self.className}</b><span>{self.health}/{self.maxHealth} health · {Math.floor(self.mana)}/{self.maxMana} mana</span><progress value={self.health} max={self.maxHealth} /></div>
          {self.queued ? <p>Realm capacity reached · queue position {snapshot.queuePosition}. Your place is held in safe staging.</p> : self.health <= 0 ? <p>Returning to staging in {Math.ceil(self.respawnRemaining)} seconds.</p> : <>
            <div className="shared-target"><span>{targetEntity ? `${'displayName' in targetEntity ? targetEntity.displayName : title(targetEntity.id.replace(`${zone.id}_`, ''))} · ${Math.ceil(targetEntity.health)} health` : 'Click a character to select a target'}</span><button disabled={!targetEntity || targetEntity.health <= 0 || status !== 'online'} onClick={() => target && send({ type: 'attack', targetId: target })}>Attack</button></div>
            <div className="shared-hotbar">{abilities.map(ability => <button key={ability.id} title={ability.summary} onClick={() => send({ type: 'ability', abilityId: ability.id, targetId: ability.targeting.target === 'self' ? self.id : target ?? '' })}>{ability.name}</button>)}</div>
            <div className="shared-interactions">
              {nearPostern && <button disabled={status !== 'online' || (self.cooldowns.postern ?? 0) > zone.seconds}
                onClick={() => send({ type: 'postern', keepId: nearPostern.keep.id, posternId: nearPostern.postern.id })}>
                {nearPostern.postern.label ?? 'Use defender postern'}</button>}
              {nearObjective && <button disabled={!zone.objectives[nearObjective.id]?.readyShipment} onClick={() => send({ type: 'dispatch', objectiveId: nearObjective.id })}>Dispatch supply wagon</button>}
              {nearKeep && <>{(['ram', 'oil', 'catapult'] as const).map((equipment, index) => <button key={equipment} onClick={() => send({ type: 'purchase', keepId: nearKeep.id, equipment })}>{title(equipment)} · {[100, 50, 150][index]} supplies</button>)}</>}
              {ownKeeps.flatMap(keep => (['outer', 'inner'] as const).map(gate => <button key={`${keep.id}:${gate}`} hidden={metres(self.position, zone.config.keeps.find(config => config.id === keep.id)![gate === 'outer' ? 'outerGate' : 'innerGate']) > 12} onClick={() => send({ type: 'repair', keepId: keep.id, gate })}>Repair {gate} gate · 25 supplies</button>))}
              {!self.equipmentId && nearEquipment.map(machine => <button key={machine.id} onClick={() => send({ type: 'board', equipmentId: machine.id })}>Operate {machine.kind}</button>)}
              {self.equipmentId && <><button onClick={() => send({ type: 'operate', equipmentId: self.equipmentId!, targetId: target ?? undefined })}>Use siege engine</button><button onClick={() => send({ type: 'leaveEquipment' })}>Leave engine</button>{zone.config.keeps.filter(keep => zone.keeps[keep.id]?.owner !== self.realm).flatMap(keep => (['outer', 'inner'] as const).map(gate => <button key={`${keep.id}:${gate}`} onClick={() => send({ type: 'operate', equipmentId: self.equipmentId!, targetId: zone.keeps[keep.id].gates[gate].id })}>Strike {gate} gate</button>))}</>}
            </div>
          </>}
          <p className="shared-notice" role="status">{notice || 'WASD to move · right drag to look · scroll to zoom · stay within 25m to escort a wagon'}</p>
        </section>
      </>}
    </>}
  </main>;
}

function CampaignMap({ snapshot }: { snapshot: WorldSnapshot }) {
  const zone = snapshot.zone!, self = snapshot.self!, bounds = zone.config.bounds;
  const point = (position: { x: number; z: number }) => ({ x: (position.x - bounds.minX) / (bounds.maxX - bounds.minX) * 240, y: (position.z - bounds.minZ) / (bounds.maxZ - bounds.minZ) * 240 });
  const color = (realm: Realm | null) => realm === 'aegis' ? '#7dbbd1' : realm === 'riftbound' ? '#d5866d' : '#c4c0a4';
  return <svg className="shared-map" viewBox="-5 -5 250 250" aria-label="Campaign tactical map">
    <rect x="0" y="0" width="240" height="240" rx="4" fill="#1c2928" />
    {zone.config.objectives.flatMap(objective => Object.values(objective.routes ?? {}).map((route, index) => <polyline key={`${objective.id}:${index}`} points={route!.map(position => { const p = point(position); return `${p.x},${p.y}`; }).join(' ')} fill="none" stroke="#46504a" strokeWidth="1.5" />))}
    {zone.config.objectives.map(objective => { const p = point(objective.position); return <circle key={objective.id} cx={p.x} cy={p.y} r="5" fill={color(zone.objectives[objective.id]?.owner ?? null)}><title>{title(objective.id)}</title></circle>; })}
    {zone.config.keeps.map(keep => { const p = point(keep.position); return <rect key={keep.id} x={p.x - 6} y={p.y - 6} width="12" height="12" fill={color(zone.keeps[keep.id]?.owner ?? keep.realm)}><title>{realmName(zone.keeps[keep.id]?.owner ?? keep.realm)} keep</title></rect>; })}
    {Object.values(zone.caravans).filter(wagon => wagon.health > 0 && wagon.status !== 'delivered').map(wagon => { const p = point(wagon.position); return <circle key={wagon.id} cx={p.x} cy={p.y} r="3" fill="#e9c76e" />; })}
    <circle cx={point(self.position).x} cy={point(self.position).y} r="4" fill="white" stroke="#152429" strokeWidth="1.5" />
  </svg>;
}
