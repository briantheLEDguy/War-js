export type Keybinding = string | null;

export type KeybindAction =
  | 'moveForward'
  | 'moveBackward'
  | 'strafeLeft'
  | 'strafeRight'
  | 'jump'
  | 'autoRun'
  | 'targetAtCursor'
  | 'targetNearestEnemy'
  | 'targetNextEnemy'
  | 'targetPreviousEnemy'
  | 'interactNearby'
  | 'interactAtCursor'
  | 'ability1'
  | 'ability2'
  | 'ability3'
  | 'ability4'
  | 'ability5'
  | 'ability6'
  | 'ability7'
  | 'ability8'
  | 'ability9'
  | 'ability10'
  | 'openInventory'
  | 'openCharacterSheet'
  | 'openQuestLog'
  | 'openWorldMap'
  | 'openGuide'
  | 'focusChat'
  | 'openSettings'
  | 'toggleDebug';

export type Keybindings = Record<KeybindAction, Keybinding>;
export type KeybindCategory = 'Movement' | 'Targeting' | 'Interaction' | 'Abilities' | 'Interface';
type KeybindingInput = 'keyboard' | 'pointer' | 'any';

export interface KeybindDefinition {
  action: KeybindAction;
  category: KeybindCategory;
  label: string;
  detail: string;
  input: KeybindingInput;
  defaultBinding: Keybinding;
}

export const KEYBIND_DEFINITIONS: readonly KeybindDefinition[] = [
  { action: 'moveForward', category: 'Movement', label: 'Move forward', detail: 'Walk in the direction of the camera.', input: 'keyboard', defaultBinding: 'KeyW' },
  { action: 'moveBackward', category: 'Movement', label: 'Move backward', detail: 'Walk away from the direction of the camera.', input: 'keyboard', defaultBinding: 'KeyS' },
  { action: 'strafeLeft', category: 'Movement', label: 'Strafe left', detail: 'Move left relative to the camera.', input: 'keyboard', defaultBinding: 'KeyA' },
  { action: 'strafeRight', category: 'Movement', label: 'Strafe right', detail: 'Move right relative to the camera.', input: 'keyboard', defaultBinding: 'KeyD' },
  { action: 'jump', category: 'Movement', label: 'Jump', detail: 'Jump while grounded.', input: 'keyboard', defaultBinding: 'Space' },
  { action: 'autoRun', category: 'Movement', label: 'Autorun', detail: 'Toggle continuous forward movement. Any movement key stops it.', input: 'keyboard', defaultBinding: 'NumLock' },

  { action: 'targetAtCursor', category: 'Targeting', label: 'Target at cursor', detail: 'Click an enemy to select it, or use a nearby object.', input: 'pointer', defaultBinding: 'MouseLeft' },
  { action: 'targetNearestEnemy', category: 'Targeting', label: 'Target nearest enemy', detail: 'Select the closest living enemy.', input: 'any', defaultBinding: 'MouseMiddle' },
  { action: 'targetNextEnemy', category: 'Targeting', label: 'Cycle next enemy', detail: 'Cycle through nearby living enemies.', input: 'keyboard', defaultBinding: 'Tab' },
  { action: 'targetPreviousEnemy', category: 'Targeting', label: 'Cycle previous enemy', detail: 'Cycle backward through nearby living enemies.', input: 'keyboard', defaultBinding: 'Shift+Tab' },

  { action: 'interactNearby', category: 'Interaction', label: 'Interact nearby', detail: 'Use the closest quest, crafting, gathering, travel, or gate object.', input: 'keyboard', defaultBinding: 'KeyE' },
  { action: 'interactAtCursor', category: 'Interaction', label: 'Interact at cursor', detail: 'Click a gate, door, or other interactable object.', input: 'pointer', defaultBinding: 'MouseRight' },

  ...Array.from({ length: 10 }, (_, index): KeybindDefinition => ({
    action: `ability${index + 1}` as KeybindAction,
    category: 'Abilities',
    label: `Ability ${index + 1}`,
    detail: `Activate hotbar slot ${index + 1}.`,
    input: 'keyboard',
    defaultBinding: `Digit${index === 9 ? 0 : index + 1}`,
  })),

  { action: 'openInventory', category: 'Interface', label: 'Toggle inventory', detail: 'Open or close your inventory.', input: 'keyboard', defaultBinding: 'KeyI' },
  { action: 'openCharacterSheet', category: 'Interface', label: 'Toggle character sheet', detail: 'Open or close character details.', input: 'keyboard', defaultBinding: 'KeyC' },
  { action: 'openQuestLog', category: 'Interface', label: 'Toggle quest log', detail: 'Open or close active quests.', input: 'keyboard', defaultBinding: 'KeyL' },
  { action: 'openWorldMap', category: 'Interface', label: 'Toggle world map', detail: 'Open or close the detailed map.', input: 'keyboard', defaultBinding: 'KeyM' },
  { action: 'openGuide', category: 'Interface', label: 'Toggle guide', detail: 'Open or close the in-game guide.', input: 'keyboard', defaultBinding: 'KeyH' },
  { action: 'focusChat', category: 'Interface', label: 'Focus chat', detail: 'Start typing in chat.', input: 'keyboard', defaultBinding: 'Enter' },
  { action: 'openSettings', category: 'Interface', label: 'Close window / settings', detail: 'Close the top window, or open settings when none are open.', input: 'keyboard', defaultBinding: 'Escape' },
  { action: 'toggleDebug', category: 'Interface', label: 'Toggle debug overlay', detail: 'Show or hide runtime diagnostics.', input: 'keyboard', defaultBinding: 'Backquote' },
];

export const KEYBIND_CATEGORIES: readonly KeybindCategory[] = [
  'Movement',
  'Targeting',
  'Interaction',
  'Abilities',
  'Interface',
];

export const DEFAULT_KEYBINDINGS = Object.fromEntries(
  KEYBIND_DEFINITIONS.map((definition) => [definition.action, definition.defaultBinding]),
) as Keybindings;

const MODIFIER_ORDER = ['Ctrl', 'Alt', 'Shift', 'Meta'] as const;
const MODIFIER_ALIASES: Record<string, typeof MODIFIER_ORDER[number]> = {
  Control: 'Ctrl',
  Ctrl: 'Ctrl',
  Alt: 'Alt',
  Shift: 'Shift',
  Meta: 'Meta',
};
const POINTER_BINDINGS = new Set(['MouseLeft', 'MouseMiddle', 'MouseRight']);

export function normalizeKeybinding(value: unknown): Keybinding | undefined {
  if (value === null) return null;
  if (typeof value !== 'string') return undefined;

  const parts = value.split('+').map((part) => part.trim()).filter(Boolean);
  if (parts.length === 0) return undefined;

  const code = parts.pop();
  if (!code || !/^[A-Za-z][A-Za-z0-9]*$/.test(code)) return undefined;
  const modifiers = new Set<typeof MODIFIER_ORDER[number]>();
  for (const modifier of parts) {
    const normalized = MODIFIER_ALIASES[modifier];
    if (!normalized) return undefined;
    modifiers.add(normalized);
  }

  if (POINTER_BINDINGS.has(code) && modifiers.size > 0) return undefined;
  if (MODIFIER_ALIASES[code] || /^(Shift|Control|Alt|Meta)(Left|Right)$/.test(code)) return undefined;
  return [...MODIFIER_ORDER.filter((modifier) => modifiers.has(modifier)), code].join('+');
}

export function normalizeKeybindings(value: unknown): Keybindings {
  const partial = value && typeof value === 'object'
    ? value as Partial<Record<KeybindAction, unknown>>
    : {};
  let bindings = { ...DEFAULT_KEYBINDINGS };

  for (const definition of KEYBIND_DEFINITIONS) {
    if (!Object.hasOwn(partial, definition.action)) continue;
    const next = normalizeKeybinding(partial[definition.action]);
    if (next !== undefined && isBindingAllowed(definition, next)) {
      bindings = assignKeybinding(bindings, definition.action, next);
    }
  }

  return bindings;
}

export function assignKeybinding(
  current: Keybindings,
  action: KeybindAction,
  binding: Keybinding,
): Keybindings {
  const definition = getKeybindDefinition(action);
  const normalized = normalizeKeybinding(binding);
  if (!definition || normalized === undefined || !isBindingAllowed(definition, normalized)) return current;

  const next = { ...current, [action]: normalized };
  if (!normalized) return next;

  for (const candidate of KEYBIND_DEFINITIONS) {
    if (candidate.action !== action && next[candidate.action] === normalized) {
      next[candidate.action] = null;
    }
  }
  return next;
}

export function getKeybindDefinition(action: KeybindAction): KeybindDefinition | undefined {
  return KEYBIND_DEFINITIONS.find((definition) => definition.action === action);
}

export function getKeybindsForCategory(category: KeybindCategory): readonly KeybindDefinition[] {
  return KEYBIND_DEFINITIONS.filter((definition) => definition.category === category);
}

export function isPointerBinding(binding: Keybinding): boolean {
  const code = getKeybindingCode(binding);
  return code !== null && POINTER_BINDINGS.has(code);
}

export function getKeybindingCode(binding: Keybinding): string | null {
  if (!binding) return null;
  const normalized = normalizeKeybinding(binding);
  return normalized?.split('+').at(-1) ?? null;
}

export function getKeybindingModifiers(binding: Keybinding): ReadonlySet<typeof MODIFIER_ORDER[number]> {
  const normalized = normalizeKeybinding(binding);
  if (!normalized) return new Set();
  const parts = normalized.split('+');
  parts.pop();
  return new Set(parts as typeof MODIFIER_ORDER[number][]);
}

export function formatKeybinding(binding: Keybinding): string {
  if (!binding) return 'Unbound';
  const normalized = normalizeKeybinding(binding);
  if (!normalized) return 'Unbound';
  return normalized.split('+').map(formatKeybindingPart).join(' + ');
}

export function keybindingFromKeyboardEvent(event: Pick<KeyboardEvent, 'code' | 'ctrlKey' | 'altKey' | 'shiftKey' | 'metaKey'>): Keybinding | undefined {
  const modifiers = [
    event.ctrlKey ? 'Ctrl' : '',
    event.altKey ? 'Alt' : '',
    event.shiftKey ? 'Shift' : '',
    event.metaKey ? 'Meta' : '',
  ].filter(Boolean);
  return normalizeKeybinding([...modifiers, event.code].join('+'));
}

export function keybindingFromPointerEvent(event: Pick<PointerEvent, 'button'>): Keybinding | undefined {
  const code = event.button === 0
    ? 'MouseLeft'
    : event.button === 1
      ? 'MouseMiddle'
      : event.button === 2
        ? 'MouseRight'
        : null;
  return code ? normalizeKeybinding(code) : undefined;
}

export function isBindingAllowed(definition: KeybindDefinition, binding: Keybinding): boolean {
  if (!binding) return true;
  if (definition.input === 'any') return true;
  return definition.input === 'pointer' ? isPointerBinding(binding) : !isPointerBinding(binding);
}

function formatKeybindingPart(part: string): string {
  if (part === 'MouseLeft') return 'Left Mouse Button';
  if (part === 'MouseMiddle') return 'Middle Mouse Button';
  if (part === 'MouseRight') return 'Right Mouse Button';
  if (part === 'Space') return 'Space';
  if (part === 'Escape') return 'Esc';
  if (part === 'Backquote') return '`';
  if (part === 'NumLock') return 'Num Lock';
  if (part.startsWith('Key')) return part.slice(3);
  if (part.startsWith('Digit')) return part.slice(5);
  if (part.startsWith('Numpad')) return `Num ${part.slice(6)}`;
  if (part.startsWith('Arrow')) return `${part.slice(5)} Arrow`;
  return part;
}
