import { lazy, Suspense, useEffect } from 'react';
import { services } from '../services';
import { useGameStore } from '../state/gameStore';
import { LoginScreen } from './screens/LoginScreen';
import { CharacterSelectScreen } from './screens/CharacterSelectScreen';
import { GameScreen } from './screens/GameScreen';
import { ModelReviewScreen } from './screens/ModelReviewScreen';
import './styles.css';
const CombatAnimationReviewScreen = import.meta.env.DEV
  ? lazy(() => import('./screens/CombatAnimationReviewScreen').then((module) => ({ default: module.CombatAnimationReviewScreen }))) : null;

export function App() {
  const modelReview = new URLSearchParams(window.location.search).get('modelReview');
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
      {modelReview === 'combat' && CombatAnimationReviewScreen ? <Suspense fallback="Loading animation review…"><CombatAnimationReviewScreen /></Suspense> : <>
      {modelReview === 'roster' && <ModelReviewScreen />}
      {modelReview !== 'roster' && <>
      {screen === 'login' && <LoginScreen />}
      {screen === 'character-select' && <CharacterSelectScreen />}
      {screen === 'world' && <GameScreen />}
      </>}
      </>}
    </div>
  );
}
