import { describe, expect, test } from 'vitest';
import {
  assignKeybinding,
  DEFAULT_KEYBINDINGS,
  formatKeybinding,
  keybindingFromKeyboardEvent,
  normalizeKeybinding,
  normalizeKeybindings,
} from '../src/data/keybindings';

describe('keybinding helpers', () => {
  test('normalizes modifier order and rejects invalid bindings', () => {
    expect(normalizeKeybinding('Shift+Ctrl+Tab')).toBe('Ctrl+Shift+Tab');
    expect(normalizeKeybinding('MouseMiddle')).toBe('MouseMiddle');
    expect(normalizeKeybinding('Shift+MouseMiddle')).toBeUndefined();
    expect(normalizeKeybinding('Shift')).toBeUndefined();
    expect(normalizeKeybinding('Shift+ShiftLeft')).toBeUndefined();
  });

  test('reassigning a binding clears its previous action', () => {
    const next = assignKeybinding(DEFAULT_KEYBINDINGS, 'targetNearestEnemy', 'Tab');

    expect(next.targetNearestEnemy).toBe('Tab');
    expect(next.targetNextEnemy).toBeNull();
  });

  test('repairs persisted conflicts while retaining valid custom bindings', () => {
    const bindings = normalizeKeybindings({
      targetNearestEnemy: 'Tab',
      targetPreviousEnemy: 'Shift+Tab',
      autoRun: 'NumLock',
    });

    expect(bindings.targetNearestEnemy).toBe('Tab');
    expect(bindings.targetNextEnemy).toBeNull();
    expect(bindings.targetPreviousEnemy).toBe('Shift+Tab');
    expect(bindings.autoRun).toBe('NumLock');
  });

  test('formats and captures the requested default targeting bindings', () => {
    expect(formatKeybinding(DEFAULT_KEYBINDINGS.targetNextEnemy)).toBe('Tab');
    expect(formatKeybinding(DEFAULT_KEYBINDINGS.targetNearestEnemy)).toBe('Middle Mouse Button');
    expect(formatKeybinding(DEFAULT_KEYBINDINGS.autoRun)).toBe('Num Lock');
    expect(keybindingFromKeyboardEvent({
      code: 'Tab',
      ctrlKey: false,
      altKey: false,
      shiftKey: true,
      metaKey: false,
    })).toBe('Shift+Tab');
  });
});
