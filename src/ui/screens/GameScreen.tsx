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

  useEffect(() => {
    if (!containerRef.current || !character) return;
    const game = new Game(containerRef.current, character);
    gameRef.current = game;
    game.start().then(() => setReady(true));

    // preload inventory
    services.inventory.get(character.id).then(setInventory);

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
      </div>
    </div>
  );
}
