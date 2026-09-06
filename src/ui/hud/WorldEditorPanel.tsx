import { useEffect, useState } from 'react';
import type { Game } from '../../game/Game';
import { useGameStore } from '../../state/gameStore';
import {
  prefabGroupForKind,
  prefabsForGroup,
  WORLD_EDITOR_PREFAB_GROUPS,
  WORLD_EDITOR_PREFABS,
} from '../../world/editor/PrefabCatalog';
import type { WorldEditorTool } from '../../world/editor/WorldEditorRuntime';
import { useDraggableWindow } from './useDraggableWindow';

interface Props {
  game: Game | null;
}

const TOOLS: Array<{ id: WorldEditorTool; label: string }> = [
  { id: 'select', label: 'Select' },
  { id: 'move', label: 'Move' },
  { id: 'rotate', label: 'Rotate' },
  { id: 'voxel_smooth', label: 'Smooth' },
  { id: 'voxel_flatten', label: 'Flatten' },
  { id: 'voxel_roughen', label: 'Roughen' },
  { id: 'paint_material', label: 'Paint' },
  { id: 'stamp_prefab', label: 'Brush' },
  { id: 'collider', label: 'Collider' },
  { id: 'walkable_surface', label: 'Walkable' },
  { id: 'ruler', label: 'Ruler' },
];

const MATERIALS = [
  { id: 'grass', label: 'Grass' },
  { id: 'dirt', label: 'Dirt' },
  { id: 'cobblestone', label: 'Cobble' },
  { id: 'stone', label: 'Stone' },
  { id: 'wood', label: 'Wood' },
  { id: 'water', label: 'Water' },
];

export function WorldEditorPanel({ game }: Props) {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLDivElement>();
  const tool = useGameStore((s) => s.worldEditorTool);
  const settings = useGameStore((s) => s.worldEditorSettings);
  const status = useGameStore((s) => s.worldEditorStatus);
  const selectedId = useGameStore((s) => s.worldEditorSelectedObjectId);
  const setTool = useGameStore((s) => s.setWorldEditorTool);
  const updateSettings = useGameStore((s) => s.updateWorldEditorSettings);
  const setGmBuildMode = useGameStore((s) => s.setGmBuildMode);
  const [publishNotes, setPublishNotes] = useState('');
  const [resetting, setResetting] = useState(false);
  const [assetSearch, setAssetSearch] = useState('');
  const [objectSearch, setObjectSearch] = useState('');
  const applyLabel = getApplyLabel(tool);
  const selectedPrefabGroup = prefabGroupForKind(settings.prefabKind);
  const visiblePrefabs = assetSearch.trim()
    ? WORLD_EDITOR_PREFABS.filter(p => `${p.label} ${p.kind} ${p.model ?? ''}`.toLowerCase().includes(assetSearch.toLowerCase().trim()))
    : prefabsForGroup(selectedPrefabGroup);
  const objects = (game?.worldEditorObjects ?? []).filter(object =>
    `${object.label} ${object.id} ${object.hidden ? 'removed' : ''}`.toLowerCase().includes(objectSearch.toLowerCase().trim()));

  useEffect(() => {
    game?.setWorldEditorTool(tool);
  }, [game, tool]);

  useEffect(() => {
    game?.setWorldEditorSettings(settings);
  }, [game, settings]);

  async function resetDraftToLive(): Promise<void> {
    if (!game || resetting) return;
    const confirmed = window.confirm('Reset the current GM draft to the live world? Unpublished edits for this zone will be discarded.');
    if (!confirmed) return;
    setResetting(true);
    try {
      await game.resetWorldEditorDraftToLive();
    } catch (err) {
      useGameStore.getState().setWorldEditorStatus(`Reset failed: ${(err as Error).message}`);
    } finally {
      setResetting(false);
    }
  }

  return (
    <div ref={panelRef} className={`world-editor-panel${dragClassName}`} style={dragStyle}>
      <div className="world-editor-header draggable-window-handle" {...dragHandleProps}>
        <div>
          <div className="world-editor-title">GM Build</div>
          <div className="world-editor-subtitle">{status || 'Draft ready.'}</div>
        </div>
        <button type="button" onClick={() => setGmBuildMode(false)}>Close</button>
      </div>

      <div className="world-editor-section world-editor-materials world-editor-section-first">
        {MATERIALS.map((material) => (
          <button
            key={material.id}
            type="button"
            className={settings.material === material.id && (tool === 'voxel_add' || tool === 'paint_material') ? 'active' : ''}
            onClick={() => {
              updateSettings({ material: material.id });
              setTool('voxel_add');
            }}
            title={material.label}
          >
            <span className={`world-editor-swatch mat-${material.id}`} />
            {material.label}
          </button>
        ))}
      </div>

      <div className="world-editor-section world-editor-grid">
        <label>
          Search all assets
          <input value={assetSearch} onChange={e => setAssetSearch(e.target.value)} placeholder="Citadel, bridge, lantern…" />
        </label>
        <label>
          Kit
          <select
            value={selectedPrefabGroup}
            onChange={(e) => {
              const [firstPrefab] = prefabsForGroup(e.target.value);
              if (!firstPrefab) return;
              setAssetSearch('');
              updateSettings({ prefabKind: firstPrefab.kind });
              setTool('stamp_prefab');
            }}
          >
            {WORLD_EDITOR_PREFAB_GROUPS.map((group) => (
              <option key={group} value={group}>{group}</option>
            ))}
          </select>
        </label>
        <label>
          Piece
          <select
            value={settings.prefabKind}
            onChange={(e) => {
              updateSettings({ prefabKind: e.target.value });
              setTool('stamp_prefab');
            }}
          >
            {!visiblePrefabs.some(p => p.kind === settings.prefabKind) && <option value={settings.prefabKind}>Choose a matching piece</option>}
            {visiblePrefabs.map((prefab) => (
              <option key={prefab.kind} value={prefab.kind}>{prefab.label}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="world-editor-section world-editor-apply">
        <button type="button" onClick={() => setTool('stamp_prefab')}>
          Preview
        </button>
      </div>

      <div className="world-editor-section world-editor-grid">
        <label>Find placed object
          <input value={objectSearch} onChange={e => setObjectSearch(e.target.value)} placeholder="Name, ID, or removed" />
        </label>
        <label>World objects ({objects.length})
          <select value={selectedId ?? ''} onChange={e => { setTool('select'); game?.selectWorldEditorObject(e.target.value); }}>
            <option value="">Select an object</option>
            {objects.filter((object, i) => i < 150 || object.id === selectedId).map(object =>
              <option key={object.id} value={object.id}>{object.hidden ? '[Removed] ' : ''}{object.label} — {object.id}</option>)}
          </select>
        </label>
        <button type="button" disabled={!selectedId} onClick={() => game?.restoreSelectedWorldEditorObject()}>Restore removed object</button>
      </div>

      <div className="world-editor-tools">
        {TOOLS.map((entry) => (
          <button
            key={entry.id}
            type="button"
            className={tool === entry.id ? 'active' : ''}
            onClick={() => setTool(entry.id)}
          >
            {entry.label}
          </button>
        ))}
      </div>

      <div className="world-editor-section">
        <label>
          Brush
          <input
            type="range"
            min={1}
            max={32}
            step={1}
            value={settings.brushSize}
            onChange={(e) => updateSettings({ brushSize: Number(e.target.value) })}
          />
          <span>{settings.brushSize}</span>
        </label>
        <label>
          Strength
          <input
            type="range"
            min={0.05}
            max={1}
            step={0.05}
            value={settings.brushStrength}
            onChange={(e) => updateSettings({ brushStrength: Number(e.target.value) })}
          />
          <span>{settings.brushStrength.toFixed(2)}</span>
        </label>
      </div>

      <div className="world-editor-section world-editor-apply">
        <button type="button" onClick={() => void game?.applyWorldEditorToolAtPlayer()}>
          {applyLabel}
        </button>
      </div>

      {tool === 'select' && (
        <div className="world-editor-section world-editor-delete">
          <button
            type="button"
            disabled={!selectedId}
            onClick={() => game?.deleteSelectedWorldEditorObject()}
          >
            Delete Object
          </button>
        </div>
      )}

      <div className="world-editor-section world-editor-grid">
        <label>
          Grid
          <input
            type="number"
            min={0}
            step={0.25}
            value={settings.snapGrid}
            onChange={(e) => updateSettings({ snapGrid: Number(e.target.value) })}
          />
        </label>
        <label>
          Angle
          <input
            type="number"
            min={0}
            max={90}
            step={1}
            value={settings.snapAngleDeg}
            onChange={(e) => updateSettings({ snapAngleDeg: Number(e.target.value) })}
          />
        </label>
      </div>

      <div className="world-editor-section world-editor-actions">
        <button type="button" onClick={() => game?.worldEditorUndo()}>Undo</button>
        <button type="button" onClick={() => game?.worldEditorRedo()}>Redo</button>
        <button type="button" onClick={() => void game?.saveWorldEditorDraft()}>Save Draft</button>
      </div>

      <div className="world-editor-section world-editor-reset">
        <button
          type="button"
          disabled={!game || resetting}
          onClick={() => void resetDraftToLive()}
        >
          {resetting ? 'Resetting...' : 'Reset to Live'}
        </button>
      </div>

      <div className="world-editor-section world-editor-publish">
        <input
          value={publishNotes}
          placeholder="Version notes"
          onChange={(e) => setPublishNotes(e.target.value)}
        />
        <button
          type="button"
          onClick={() => {
            void game?.publishWorldEditorDraft(publishNotes);
            setPublishNotes('');
          }}
        >
          Publish
        </button>
      </div>

      <div className="world-editor-selection">
        Selected: {selectedId ?? 'none'}
      </div>
    </div>
  );
}

function getApplyLabel(tool: WorldEditorTool): string {
  if (tool === 'select' || tool === 'move' || tool === 'rotate' || tool === 'scale') return 'Select Nearest';
  if (tool === 'stamp_prefab') return 'Place Brush';
  if (tool === 'collider') return 'Add Collider';
  if (tool === 'walkable_surface') return 'Add Walkable';
  if (tool === 'ruler') return 'Measure Nearest';
  return 'Apply Brush';
}
