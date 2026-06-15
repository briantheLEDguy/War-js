import { useEffect } from 'react';
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

export function SettingsPanel() {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLElement>();
  const settingsOpen = useGameStore((s) => s.settingsOpen);
  const settings = useGameStore((s) => s.settings);
  const setSettingsOpen = useGameStore((s) => s.setSettingsOpen);
  const updateSettings = useGameStore((s) => s.updateSettings);
  const resetSettings = useGameStore((s) => s.resetSettings);

  useEffect(() => {
    if (settingsOpen) panelRef.current?.focus();
  }, [settingsOpen]);

  if (!settingsOpen) return null;

  return (
    <>
      <div
        className="settings-backdrop"
        onClick={() => setSettingsOpen(false)}
      />
      <section
        ref={panelRef}
        className={`settings-panel panel${dragClassName}`}
        style={dragStyle}
        role="dialog"
        aria-modal="true"
        aria-labelledby="settings-title"
        tabIndex={-1}
      >
        <header className="settings-header draggable-window-handle" {...dragHandleProps}>
          <div>
            <h2 id="settings-title">Settings</h2>
            <span>Controls</span>
          </div>
          <button
            className="settings-close"
            type="button"
            onClick={() => setSettingsOpen(false)}
          >
            Close
          </button>
        </header>

        <div className="settings-section">
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

        <footer className="settings-actions">
          <button
            type="button"
            onClick={resetSettings}
            disabled={
              settings.invertCameraX === DEFAULT_GAMEPLAY_SETTINGS.invertCameraX &&
              settings.invertCameraY === DEFAULT_GAMEPLAY_SETTINGS.invertCameraY &&
              settings.mouseLookSensitivity === DEFAULT_GAMEPLAY_SETTINGS.mouseLookSensitivity &&
              settings.touchLookSensitivity === DEFAULT_GAMEPLAY_SETTINGS.touchLookSensitivity &&
              settings.zoomSensitivity === DEFAULT_GAMEPLAY_SETTINGS.zoomSensitivity &&
              settings.viewDistance === DEFAULT_GAMEPLAY_SETTINGS.viewDistance
            }
          >
            Defaults
          </button>
          <button type="button" onClick={() => setSettingsOpen(false)}>
            Done
          </button>
        </footer>
      </section>
    </>
  );
}
