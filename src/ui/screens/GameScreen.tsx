import { useEffect, useRef, useState } from 'react';
import { Game } from '../../game/Game';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';
import { Hud } from '../hud/Hud';

export function GameScreen() {
  const containerRef = useRef<HTMLDivElement>(null);
  const gameRef = useRef<Game | null>(null);
  const [ready, setReady] = useState(false);

  const character = useGameStore((s) => s.character);
  const setScreen = useGameStore((s) => s.setScreen);
  const setInventory = useGameStore((s) => s.setInventory);
  const setCraftingState = useGameStore((s) => s.setCraftingState);
  const pendingZoneTransition = useGameStore((s) => s.pendingZoneTransition);
  const gmBuildMode = useGameStore((s) => s.gmBuildMode);
  const characterMountKey = character ? `${character.id}:${character.zoneId}:${character.bodyVariant}` : null;

  // Handle zone transitions: dispose current game, update character zone, re-mount.
  useEffect(() => {
    if (!pendingZoneTransition || !character) return;
    const { targetZoneId, targetSpawn } = pendingZoneTransition;

    gameRef.current?.dispose();
    gameRef.current = null;
    setReady(false);

    useGameStore.getState().setPendingZoneTransition(null);

    const newPos = targetSpawn ?? { x: 0, y: 0, z: 0 };
    const newChar = { ...character, zoneId: targetZoneId, position: newPos };
    useGameStore.getState().setCharacter(newChar);

    void services.characters.save(character.id, { zoneId: targetZoneId, position: newPos });
  }, [pendingZoneTransition, character]);

  useEffect(() => {
    if (!containerRef.current || !character) return;
    setReady(false);
    const characterSnapshot = character;
    const game = new Game(containerRef.current, characterSnapshot);
    gameRef.current = game;
    game.start().then(() => {
      // Only mark ready if this game instance is still the active one.
      // Guards against React Strict Mode's double-invoke of effects, which
      // can cause a partially-initialized game to be passed to the HUD.
      if (gameRef.current === game) setReady(true);
    }).catch((err) => {
      console.error('[Game] start() failed:', err);
    });

    // preload inventory, quests, and crafting progress
    services.inventory.get(characterSnapshot.id).then(setInventory);
    services.crafting.get(characterSnapshot.id).then(setCraftingState);
    services.quests
      .list(characterSnapshot.id)
      .then((q) => useGameStore.getState().setQuests(q));

    return () => {
      game.dispose();
      gameRef.current = null;
    };
  }, [characterMountKey, setInventory, setCraftingState]);

  useEffect(() => {
    if (!ready || !gameRef.current) return;
    void gameRef.current.setWorldEditorActive(gmBuildMode);
  }, [gmBuildMode, ready]);

  async function logout() {
    if (gameRef.current) gameRef.current.dispose();
    await services.auth.signOut();
    useGameStore.getState().setUser(null);
    useGameStore.getState().setCharacter(null);
    useGameStore.getState().setSettingsOpen(false);
    useGameStore.getState().setGmBuildMode(false);
    setScreen('login');
  }

  if (!character) {
    return <div className="loading">No character selected.</div>;
  }

  return (
    <div className="game-root">
      <div ref={containerRef} className="game-canvas-container" />
      {!ready && <div className="loading">Entering the world...</div>}
      {ready && <Hud game={gameRef.current} />}
      <button className="logout-btn" onClick={logout}>
        Exit to Login
      </button>
      <div className="controls-hint">
        WASD move &middot; Space jump &middot; RMB turn/click doors/equip gear &middot; LMB orbit/target &middot; L+R move &middot; 1-0 class abilities &middot; E interact/gather/craft &middot; I inventory &middot; C character &middot; L quest log &middot; Enter chat &middot; Esc settings &middot; ` debug
        &nbsp;&nbsp;|&nbsp;&nbsp;Touch: joystick move &middot; ↑ jump &middot; drag camera &middot; pinch zoom &middot; tap target/ability
      </div>
    </div>
  );
}
