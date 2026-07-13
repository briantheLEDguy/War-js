import { useEffect } from 'react';
import { services } from '../services';
import { useGameStore } from '../state/gameStore';
import { LoginScreen } from './screens/LoginScreen';
import { CharacterSelectScreen } from './screens/CharacterSelectScreen';
import { GameScreen } from './screens/GameScreen';
import './styles.css';

export function App() {
  const screen = useGameStore((s) => s.screen);
  const setUser = useGameStore((s) => s.setUser);
  const setScreen = useGameStore((s) => s.setScreen);

  useEffect(() => {
    const existing = services.auth.currentUser();
    if (existing) {
      setUser(existing);
      setScreen('character-select');
    }
  }, [setUser, setScreen]);

  return (
    <div className="app-root">
      {screen === 'login' && <LoginScreen />}
      {screen === 'character-select' && <CharacterSelectScreen />}
      {screen === 'world' && <GameScreen />}
    </div>
  );
}
