import motions from './battlePrelateMotions.json';
import type { AbilityAnimation, AbilityDefinition, AbilityMotionVariant } from '../abilities/types';

export function prelateAnimation(slot: number, fallback: AbilityAnimation): AbilityAnimation {
  const variants: AbilityMotionVariant[] = motions.motions.filter((m) => m.slot === slot).map((m) => ({
    clip: m.clip, durationSec: m.durationSec, contactSec: m.contact,
  }));
  if (!variants.length) return fallback;
  return {
    ...fallback, ...variants[0], variants: variants.length > 1 ? variants : undefined,
    blendInSec: 0.1, blendOutSec: 0.16,
    notifyWindows: [{ name: 'impact', start: variants[0].contactSec / variants[0].durationSec, end: variants[0].contactSec / variants[0].durationSec }],
  };
}

/** Per-player sequence; only successful activations enter this resolver. */
export class AbilityMotionSequence {
  private next = 0;
  private lastLitanyAt = -Infinity;

  resolve(ability: AbilityDefinition, now: number): AbilityDefinition {
    const variants = ability.animation.variants;
    if (!variants?.length) return ability;
    if (now - this.lastLitanyAt >= 3000 || now < this.lastLitanyAt) this.next = 0;
    const motion = variants[this.next++ % variants.length];
    this.lastLitanyAt = now;
    return { ...ability, animation: { ...ability.animation, ...motion,
      notifyWindows: [{ name: 'impact', start: motion.contactSec / motion.durationSec, end: motion.contactSec / motion.durationSec }],
    } };
  }
}
