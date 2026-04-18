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
  const pendingZoneTransition = useGameStore((s) => s.pendingZoneTransition);

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
    const game = new Game(containerRef.current, character);
    gameRef.current = game;
    game.start().then(() => {
      // Only mark ready if this game instance is still the active one.
      // Guards against React Strict Mode's double-invoke of effects, which
      // can cause a partially-initialized game to be passed to the HUD.
      if (gameRef.current === game) setReady(true);
    }).catch((err) => {
      console.error('[Game] start() failed:', err);
    });

    // preload inventory + quest progress
    services.inventory.get(character.id).then(setInventory);
    services.quests
      .list(character.id)
      .then((q) => useGameStore.getState().setQuests(q));

    return () => {
      game.dispose();
      gameRef.current = null;
    };
  }, [character, setInventory]);

  async function logout() {
    if (gameRef.current) gameRef.current.dispose();
    await services.auth.signOut();
    useGameStore.getState().setUser(null);
    useGameStore.getState().setCharacter(null);
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
        WASD move &middot; Space jump &middot; LMB target &middot; 1 attack &middot; 2 heavy &middot; 3 ranged &middot; 4 bandage &middot; I inventory &middot; Enter chat &middot; ` debug
        &nbsp;&nbsp;|&nbsp;&nbsp;Touch: joystick move &middot; ↑ jump &middot; drag camera &middot; pinch zoom &middot; tap target/ability
      </div>
    </div>
  );
}
