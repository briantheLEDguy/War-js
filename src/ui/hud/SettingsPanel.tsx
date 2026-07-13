import { useCallback, useEffect, useState } from 'react';
import {
  DEFAULT_KEYBINDINGS,
  formatKeybinding,
  getKeybindDefinition,
  getKeybindsForCategory,
  isBindingAllowed,
  keybindingFromKeyboardEvent,
  keybindingFromPointerEvent,
  KEYBIND_CATEGORIES,
  type KeybindAction,
  type Keybinding,
} from '../../data/keybindings';
import {
  VIEW_DISTANCE_MAX,
  VIEW_DISTANCE_MIN,
  VIEW_DISTANCE_STEP,
  formatViewDistance,
} from '../../config/viewDistance';
import { DEFAULT_GAMEPLAY_SETTINGS, useGameStore } from '../../state/gameStore';
import { useDraggableWindow } from './useDraggableWindow';

function formatMultiplier(value: number): string {
  return `${value.toFixed(2)}x`;
}

type SettingsTab = 'gameplay' | 'keybinds';

export function SettingsPanel() {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLElement>();
  const [activeTab, setActiveTab] = useState<SettingsTab>('gameplay');
  const [capturing, setCapturing] = useState<KeybindAction | null>(null);
  const [captureError, setCaptureError] = useState('');
  const settingsOpen = useGameStore((s) => s.settingsOpen);
  const settings = useGameStore((s) => s.settings);
  const setSettingsOpen = useGameStore((s) => s.setSettingsOpen);
  const updateSettings = useGameStore((s) => s.updateSettings);
  const updateKeybinding = useGameStore((s) => s.updateKeybinding);
  const resetSettings = useGameStore((s) => s.resetSettings);

  const closeSettings = () => {
    setCapturing(null);
    setCaptureError('');
    setSettingsOpen(false);
  };

  const selectTab = (tab: SettingsTab) => {
    setActiveTab(tab);
    setCapturing(null);
    setCaptureError('');
  };

  useEffect(() => {
    if (settingsOpen) panelRef.current?.focus();
  }, [panelRef, settingsOpen]);

  const applyBinding = useCallback((action: KeybindAction, binding: Keybinding) => {
    const definition = getKeybindDefinition(action);
    if (!definition || !isBindingAllowed(definition, binding)) {
      setCaptureError(definition?.input === 'pointer'
        ? 'This action requires a mouse button.'
        : 'This action requires a keyboard key.');
      return;
    }
    updateKeybinding(action, binding);
    setCapturing(null);
    setCaptureError('');
  }, [updateKeybinding]);

  useEffect(() => {
    if (!capturing || !settingsOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.repeat) return;
      event.preventDefault();
      if (event.code === 'Escape') {
        setCapturing(null);
        setCaptureError('');
        return;
      }
      const binding = keybindingFromKeyboardEvent(event);
      if (binding !== undefined) applyBinding(capturing, binding);
    };
    const onPointerDown = (event: PointerEvent) => {
      const target = event.target instanceof Element ? event.target : null;
      if (target?.closest('[data-keybind-control]')) return;
      const binding = keybindingFromPointerEvent(event);
      if (binding === undefined) return;
      event.preventDefault();
      applyBinding(capturing, binding);
    };

    window.addEventListener('keydown', onKeyDown);
    window.addEventListener('pointerdown', onPointerDown);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener('pointerdown', onPointerDown);
    };
  }, [applyBinding, capturing, settingsOpen]);

  if (!settingsOpen) return null;

  const settingsAtDefaults =
    settings.invertCameraX === DEFAULT_GAMEPLAY_SETTINGS.invertCameraX &&
    settings.invertCameraY === DEFAULT_GAMEPLAY_SETTINGS.invertCameraY &&
    settings.mouseLookSensitivity === DEFAULT_GAMEPLAY_SETTINGS.mouseLookSensitivity &&
    settings.touchLookSensitivity === DEFAULT_GAMEPLAY_SETTINGS.touchLookSensitivity &&
    settings.zoomSensitivity === DEFAULT_GAMEPLAY_SETTINGS.zoomSensitivity &&
    settings.viewDistance === DEFAULT_GAMEPLAY_SETTINGS.viewDistance &&
    KEYBIND_CATEGORIES.every((category) => getKeybindsForCategory(category).every(
      (definition) => settings.keybindings[definition.action] === DEFAULT_KEYBINDINGS[definition.action],
    ));

  return (
    <>
      <div
        className="settings-backdrop"
        onClick={closeSettings}
      />
      <section
        ref={panelRef}
        className={`settings-panel settings-keybindings-panel panel${dragClassName}`}
        style={dragStyle}
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        tabIndex={-1}
      >
        <header className="settings-header draggable-window-handle" {...dragHandleProps}>
          <div>
            <h2 id="settings-title">Settings</h2>
            <span>Controls and key bindings</span>
          </div>
          <button
            className="settings-close"
            type="button"
            onClick={closeSettings}
          >
            Close
          </button>
        </header>

        <div className="settings-tabs" role="tablist" aria-label="Settings sections">
          <button
            id="settings-tab-gameplay"
            className={`settings-tab${activeTab === 'gameplay' ? ' active' : ''}`}
            type="button"
            role="tab"
            aria-selected={activeTab === 'gameplay'}
            aria-controls="settings-panel-gameplay"
            onClick={() => selectTab('gameplay')}
          >
            Gameplay
          </button>
          <button
            id="settings-tab-keybinds"
            className={`settings-tab${activeTab === 'keybinds' ? ' active' : ''}`}
            type="button"
            role="tab"
            aria-selected={activeTab === 'keybinds'}
            aria-controls="settings-panel-keybinds"
            onClick={() => selectTab('keybinds')}
          >
            Key binds
          </button>
        </div>

        {activeTab === 'gameplay' && (
          <div
            id="settings-panel-gameplay"
            className="settings-section"
            role="tabpanel"
            aria-labelledby="settings-tab-gameplay"
          >
            <h3>Camera</h3>

            <label className="settings-toggle">
              <span>Invert horizontal look</span>
              <input
                type="checkbox"
                checked={settings.invertCameraX}
                onChange={(e) => updateSettings({ invertCameraX: e.currentTarget.checked })}
              />
            </label>

            <label className="settings-toggle">
              <span>Invert vertical look</span>
              <input
                type="checkbox"
                checked={settings.invertCameraY}
                onChange={(e) => updateSettings({ invertCameraY: e.currentTarget.checked })}
              />
            </label>

            <label className="settings-range">
              <span>
                Mouse look sensitivity
                <strong>{formatMultiplier(settings.mouseLookSensitivity)}</strong>
              </span>
              <input
                type="range"
                min="0.25"
                max="3"
                step="0.05"
                value={settings.mouseLookSensitivity}
                onChange={(e) => updateSettings({ mouseLookSensitivity: e.currentTarget.valueAsNumber })}
              />
            </label>

            <label className="settings-range">
              <span>
                Touch look sensitivity
                <strong>{formatMultiplier(settings.touchLookSensitivity)}</strong>
              </span>
              <input
                type="range"
                min="0.25"
                max="3"
                step="0.05"
                value={settings.touchLookSensitivity}
                onChange={(e) => updateSettings({ touchLookSensitivity: e.currentTarget.valueAsNumber })}
              />
            </label>

            <label className="settings-range">
              <span>
                Zoom speed
                <strong>{formatMultiplier(settings.zoomSensitivity)}</strong>
              </span>
              <input
                type="range"
                min="0.25"
                max="3"
                step="0.05"
                value={settings.zoomSensitivity}
                onChange={(e) => updateSettings({ zoomSensitivity: e.currentTarget.valueAsNumber })}
              />
            </label>

            <label className="settings-range">
              <span>
                View distance
                <strong>{formatViewDistance(settings.viewDistance)}</strong>
              </span>
              <input
                type="range"
                min={VIEW_DISTANCE_MIN}
                max={VIEW_DISTANCE_MAX}
                step={VIEW_DISTANCE_STEP}
                value={settings.viewDistance}
                onChange={(e) => updateSettings({ viewDistance: e.currentTarget.valueAsNumber })}
              />
            </label>
          </div>
        )}

        {activeTab === 'keybinds' && (
          <section
            id="settings-panel-keybinds"
            className="settings-section settings-keybindings"
            role="tabpanel"
            aria-labelledby="settings-tab-keybinds"
          >
          <div className="settings-keybindings-heading">
            <div>
              <h3 id="keybindings-title">Key bindings</h3>
              <p>Click a binding, then press a key or mouse button. Assigning a used binding clears it from its previous action.</p>
            </div>
            <button
              type="button"
              data-keybind-control
              onClick={() => {
                setCapturing(null);
                setCaptureError('');
                updateSettings({ keybindings: DEFAULT_KEYBINDINGS });
              }}
            >
              Reset bindings
            </button>
          </div>
          <p className="settings-gesture-note">Camera: drag with either mouse button to orbit, use the wheel to zoom, or use touch drag/pinch on mobile.</p>
          {captureError && <p className="keybind-capture-error" role="alert">{captureError}</p>}

          <div className="keybind-categories">
            {KEYBIND_CATEGORIES.map((category) => (
              <section className="keybind-category" key={category} aria-labelledby={`keybind-${category}`}>
                <h4 id={`keybind-${category}`}>{category}</h4>
                <div className="keybind-list">
                  {getKeybindsForCategory(category).map((definition) => {
                    const isCapturing = capturing === definition.action;
                    const binding = settings.keybindings[definition.action];
                    return (
                      <div className="keybind-row" key={definition.action}>
                        <div>
                          <strong>{definition.label}</strong>
                          <span>{definition.detail}</span>
                        </div>
                        <div className="keybind-controls">
                          <button
                            type="button"
                            className={`keybind-capture${isCapturing ? ' capturing' : ''}`}
                            data-keybind-control
                            data-keybind-capture={isCapturing ? 'true' : undefined}
                            onClick={() => {
                              setCapturing(definition.action);
                              setCaptureError('');
                            }}
                            aria-label={`Set ${definition.label}; currently ${formatKeybinding(binding)}`}
                          >
                            {isCapturing ? 'Press a key…' : formatKeybinding(binding)}
                          </button>
                          <button
                            type="button"
                            className="keybind-clear"
                            data-keybind-control
                            onClick={() => {
                              setCapturing(null);
                              setCaptureError('');
                              updateKeybinding(definition.action, null);
                            }}
                            disabled={binding === null}
                            aria-label={`Clear ${definition.label}`}
                          >
                            Clear
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>
            ))}
          </div>
          </section>
        )}

        <footer className="settings-actions">
          <button
            type="button"
            onClick={resetSettings}
            disabled={settingsAtDefaults}
          >
            Reset all
          </button>
          <button type="button" onClick={closeSettings}>
            Done
          </button>
        </footer>
      </section>
    </>
  );
}
