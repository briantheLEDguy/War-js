import { type SyntheticEvent, useEffect } from 'react';
import { useGameStore } from '../../state/gameStore';

export function InteractionFeedback() {
  const prompt = useGameStore((s) => s.contextPrompt);
  const feedback = useGameStore((s) => s.abilityFeedback);
  const setContextPrompt = useGameStore((s) => s.setContextPrompt);
  const clearExpiredAbilityFeedback = useGameStore((s) => s.clearExpiredAbilityFeedback);

  useEffect(() => {
    if (!feedback) return;

    const remaining = feedback.expiresAt - Date.now();
    if (remaining <= 0) {
      clearExpiredAbilityFeedback(Date.now());
      return;
    }

    const timer = window.setTimeout(() => clearExpiredAbilityFeedback(Date.now()), remaining);
    return () => window.clearTimeout(timer);
  }, [clearExpiredAbilityFeedback, feedback]);

  const activeFeedback = feedback && feedback.expiresAt > Date.now() ? feedback : null;
  if (!prompt && !activeFeedback) return null;

  function stopHudEvent(event: SyntheticEvent<HTMLButtonElement>) {
    event.preventDefault();
    event.stopPropagation();
  }

  function handleDismissPrompt(event: SyntheticEvent<HTMLButtonElement>) {
    stopHudEvent(event);
    setContextPrompt(null);
  }

  return (
    <div className="interaction-feedback" aria-live="polite">
      {activeFeedback && (
        <div className={`interaction-feedback__notice ${activeFeedback.kind}`}>
          {activeFeedback.message}
        </div>
      )}
      {prompt && (
        <div className={`interaction-feedback__prompt prompt-${prompt.kind}`}>
          <span className="interaction-feedback__key">{prompt.action}</span>
          <span className="interaction-feedback__label">{prompt.label}</span>
          {prompt.detail && <span className="interaction-feedback__detail">{prompt.detail}</span>}
          <button
            className="interaction-feedback__dismiss"
            type="button"
            aria-label="Close prompt"
            onPointerDown={stopHudEvent}
            onClick={handleDismissPrompt}
          >
            x
          </button>
        </div>
      )}
    </div>
  );
}
