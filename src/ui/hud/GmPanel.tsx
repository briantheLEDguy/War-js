import { useEffect, useMemo, useState } from 'react';
import { CAMPAIGN_ZONES } from '../../data/campaign';
import { defaultZoneSpawnPoint } from '../../data/zoneRouting';
import { canUseGmTools } from '../../editor/gmAuth';
import type { Game } from '../../game/Game';
import { createAbilityResourceState } from '../../game/abilities/abilityData';
import { services } from '../../services';
import type { CharacterState, Vec3 } from '../../services/types';
import { useGameStore } from '../../state/gameStore';
import { useDraggableWindow } from './useDraggableWindow';

interface Props {
  game: Game | null;
}

type BusyAction = 'zone' | 'character' | 'copy' | null;

export function GmPanel({ game }: Props) {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLElement>();
  const open = useGameStore((s) => s.gmMenuOpen);
  const user = useGameStore((s) => s.user);
  const character = useGameStore((s) => s.character);
  const gmBuildMode = useGameStore((s) => s.gmBuildMode);
  const gmMoveSpeedMultiplier = useGameStore((s) => s.gmMoveSpeedMultiplier);
  const gmFlyingMode = useGameStore((s) => s.gmFlyingMode);
  const setOpen = useGameStore((s) => s.setGmMenuOpen);
  const setGmBuildMode = useGameStore((s) => s.setGmBuildMode);
  const setGmMoveSpeedMultiplier = useGameStore((s) => s.setGmMoveSpeedMultiplier);
  const setGmFlyingMode = useGameStore((s) => s.setGmFlyingMode);
  const resetHotbarCooldowns = useGameStore((s) => s.resetHotbarCooldowns);
  const [selectedZoneId, setSelectedZoneId] = useState(character?.zoneId ?? CAMPAIGN_ZONES[0]?.id ?? 'aegis_capital');
  const [characterName, setCharacterName] = useState('');
  const [status, setStatus] = useState('Ready.');
  const [busy, setBusy] = useState<BusyAction>(null);

  const authorized = canUseGmTools(user);
  const currentPosition = getCurrentPosition(game, character);
  const currentZoneName = game?.zoneDefinition?.name ?? zoneName(character?.zoneId);
  const selectedZone = useMemo(
    () => CAMPAIGN_ZONES.find((zone) => zone.id === selectedZoneId) ?? CAMPAIGN_ZONES[0],
    [selectedZoneId],
  );

  useEffect(() => {
    if (open) panelRef.current?.focus();
  }, [open]);

  useEffect(() => {
    if (character?.zoneId && CAMPAIGN_ZONES.some((zone) => zone.id === character.zoneId)) {
      setSelectedZoneId(character.zoneId);
    }
  }, [character?.zoneId]);

  useEffect(() => {
    if (open && !authorized) setOpen(false);
  }, [authorized, open, setOpen]);

  if (!open || !authorized) return null;

  async function teleportToSelectedZone(): Promise<void> {
    if (!selectedZone) return;
    setBusy('zone');
    try {
      const spawn = await loadZoneSpawn(selectedZone.id);
      teleportTo(selectedZone.id, spawn, `Teleported to ${selectedZone.name}.`);
    } catch (err) {
      setStatus(`Teleport failed: ${(err as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  async function goToCharacter(event: React.FormEvent): Promise<void> {
    event.preventDefault();
    const name = characterName.trim();
    if (!name) return;
    setBusy('character');
    try {
      const online = await services.world.findPlayerByName(name).catch(() => null);
      if (online) {
        teleportTo(online.zoneId, online.position, `Teleported to online character ${online.name}.`, online.rotationY);
        return;
      }

      const matches = await services.characters.findByName(name);
      if (matches.length === 0) {
        setStatus(`No character named "${name}" was found.`);
        return;
      }
      if (matches.length > 1) {
        setStatus(`Multiple characters named "${name}" were found. Rename one before using GM goto.`);
        return;
      }

      const target = matches[0];
      teleportTo(target.zoneId, target.position, `Teleported to saved position for ${target.name}.`, target.rotationY);
    } catch (err) {
      setStatus(`Character lookup failed: ${(err as Error).message}`);
    } finally {
      setBusy(null);
    }
  }

  function teleportTo(zoneId: string, position: Vec3, message: string, rotationY?: number): void {
    const activeCharacter = useGameStore.getState().character;
    if (!activeCharacter) {
      setStatus('No active character is loaded.');
      return;
    }

    if (activeCharacter.zoneId === zoneId) {
      if (!game) {
        setStatus('The world is still loading. Try again in a moment.');
        return;
      }
      const next = game.teleportPlayerTo(position, rotationY);
      setStatus(`${message} ${formatPoint(next)}`);
      return;
    }

    useGameStore.getState().setPendingZoneTransition({
      targetZoneId: zoneId,
      targetSpawn: position,
    });
    setStatus(`${message} Loading ${zoneName(zoneId)}...`);
  }

  function returnToZoneSpawn(): void {
    const zoneId = character?.zoneId;
    if (!zoneId) {
      setStatus('No active zone is loaded.');
      return;
    }
    const spawn = game?.zoneDefinition?.spawnPoint ?? defaultZoneSpawnPoint(zoneId);
    teleportTo(zoneId, spawn, `Returned to ${zoneName(zoneId)} spawn.`);
  }

  function healAndRestore(): void {
    const activeCharacter = useGameStore.getState().character;
    if (!activeCharacter) {
      setStatus('No active character is loaded.');
      return;
    }
    const patch = {
      health: activeCharacter.maxHealth,
      mana: activeCharacter.maxMana,
    };
    useGameStore.getState().setPlayerDead(false);
    useGameStore.getState().updateCharacter(patch);
    const resource = createAbilityResourceState(activeCharacter.className);
    useGameStore.getState().setAbilityResource({ ...resource, current: resource.max });
    void services.characters.save(activeCharacter.id, patch);
    setStatus('Health, mana, and class resource restored.');
  }

  function resetCooldowns(): void {
    resetHotbarCooldowns();
    setStatus('Ability cooldowns reset.');
  }

  async function copyCoordinates(): Promise<void> {
    setBusy('copy');
    const point = getCurrentPosition(game, useGameStore.getState().character);
    const text = `${character?.zoneId ?? 'unknown'} ${formatPoint(point)}`;
    try {
      await navigator.clipboard.writeText(text);
      setStatus(`Copied ${text}`);
    } catch {
      setStatus(text);
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <div className="gm-backdrop" onClick={() => setOpen(false)} />
      <section
        ref={panelRef}
        className={`gm-panel panel${dragClassName}`}
        style={dragStyle}
        role="dialog"
        aria-modal="true"
        aria-labelledby="gm-title"
        tabIndex={-1}
        onKeyDown={(event) => {
          if (event.key === 'Escape') setOpen(false);
        }}
      >
        <header className="gm-header draggable-window-handle" {...dragHandleProps}>
          <div>
            <h2 id="gm-title">GM Tools</h2>
            <span>{currentZoneName} - {formatPoint(currentPosition)}</span>
          </div>
          <button type="button" onClick={() => setOpen(false)}>Close</button>
        </header>

        <div className="gm-section">
          <h3>Zone Teleport</h3>
          <div className="gm-zone-row">
            <select
              value={selectedZoneId}
              onChange={(event) => setSelectedZoneId(event.currentTarget.value)}
            >
              {CAMPAIGN_ZONES.map((zone) => (
                <option key={zone.id} value={zone.id}>
                  {zone.name} - {zone.tier}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => void teleportToSelectedZone()}
              disabled={busy === 'zone'}
            >
              Teleport
            </button>
          </div>
          <small>{selectedZone?.id}</small>
        </div>

        <form className="gm-section" onSubmit={(event) => void goToCharacter(event)}>
          <h3>Go To Character</h3>
          <div className="gm-zone-row">
            <input
              value={characterName}
              onChange={(event) => setCharacterName(event.currentTarget.value)}
              placeholder="Character name"
              maxLength={32}
            />
            <button type="submit" disabled={!characterName.trim() || busy === 'character'}>
              Go
            </button>
          </div>
        </form>

        <div className="gm-section">
          <h3>Movement</h3>
          <label className="gm-range">
            <span>
              Speed Multiplier
              <strong>{gmMoveSpeedMultiplier.toFixed(2)}x</strong>
            </span>
            <input
              type="range"
              min="0.25"
              max="6"
              step="0.25"
              value={gmMoveSpeedMultiplier}
              onChange={(event) => setGmMoveSpeedMultiplier(event.currentTarget.valueAsNumber)}
            />
          </label>
          <label className="gm-toggle">
            <span>
              Flying Mode
              <small>Q down / E up</small>
            </span>
            <input
              type="checkbox"
              checked={gmFlyingMode}
              onChange={(event) => {
                setGmFlyingMode(event.currentTarget.checked);
                setStatus(event.currentTarget.checked ? 'Flying mode enabled. Use Q down and E up.' : 'Flying mode disabled.');
              }}
            />
          </label>
        </div>

        <div className="gm-section">
          <h3>Utilities</h3>
          <div className="gm-actions">
            <button type="button" onClick={() => void copyCoordinates()} disabled={busy === 'copy'}>
              Copy Coords
            </button>
            <button type="button" onClick={returnToZoneSpawn}>
              Zone Spawn
            </button>
            <button type="button" onClick={healAndRestore}>
              Restore
            </button>
            <button type="button" onClick={resetCooldowns}>
              Cooldowns
            </button>
            <button
              type="button"
              className={gmBuildMode ? 'active' : ''}
              onClick={() => {
                setGmBuildMode(!gmBuildMode);
                setStatus(!gmBuildMode ? 'GM build mode enabled.' : 'GM build mode disabled.');
              }}
            >
              Build {gmBuildMode ? 'On' : 'Off'}
            </button>
          </div>
        </div>

        <footer className="gm-status">{status}</footer>
      </section>
    </>
  );
}

async function loadZoneSpawn(zoneId: string): Promise<Vec3> {
  const fallback = defaultZoneSpawnPoint(zoneId);
  try {
    const response = await fetch(`${import.meta.env.BASE_URL}assets/maps/${zoneId}.json`);
    if (!response.ok) return fallback;
    const zone = await response.json() as { spawnPoint?: Partial<Vec3> };
    return isFinitePoint(zone.spawnPoint) ? {
      x: zone.spawnPoint.x,
      y: Number.isFinite(zone.spawnPoint.y) ? zone.spawnPoint.y : 0,
      z: zone.spawnPoint.z,
    } : fallback;
  } catch {
    return fallback;
  }
}

function getCurrentPosition(game: Game | null, character: CharacterState | null): Vec3 {
  const playerPos = game?.playerPos;
  if (playerPos) {
    return { x: playerPos.x, y: playerPos.y, z: playerPos.z };
  }
  return character?.position ?? { x: 0, y: 0, z: 0 };
}

function formatPoint(point: Vec3): string {
  return `x ${formatNumber(point.x)}, y ${formatNumber(point.y)}, z ${formatNumber(point.z)}`;
}

function formatNumber(value: number): string {
  return Number.isFinite(value) ? value.toFixed(1) : '0.0';
}

function zoneName(zoneId: string | null | undefined): string {
  if (!zoneId) return 'Unknown zone';
  return CAMPAIGN_ZONES.find((zone) => zone.id === zoneId)?.name ?? zoneId;
}

function isFinitePoint(point: Partial<Vec3> | null | undefined): point is Vec3 {
  return Boolean(point && Number.isFinite(point.x) && Number.isFinite(point.z));
}
