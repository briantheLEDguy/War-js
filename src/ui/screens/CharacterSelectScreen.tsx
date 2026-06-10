import { useEffect, useMemo, useState } from 'react';
import {
  BODY_VARIANT_DISPLAY,
  BODY_VARIANTS,
  CLASSES_BY_RACE,
  DESTRUCTION_RACES,
  ORDER_RACES,
  RACE_DISPLAY,
  normalizeClassName,
} from '../../data/careers';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';
import type { CharacterState, CharacterSummary } from '../../services/types';
import { CharacterPreviewStage } from './CharacterPreviewStage';

export function CharacterSelectScreen() {
  const user = useGameStore((s) => s.user);
  const setUser = useGameStore((s) => s.setUser);
  const setScreen = useGameStore((s) => s.setScreen);
  const characterList = useGameStore((s) => s.characterList);
  const setCharacterList = useGameStore((s) => s.setCharacterList);
  const setCharacter = useGameStore((s) => s.setCharacter);

  const [selected, setSelected] = useState<string | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newRace, setNewRace] = useState<CharacterSummary['race']>('empire');
  const [newClass, setNewClass] = useState(CLASSES_BY_RACE['empire'][0]);
  const [newBodyVariant, setNewBodyVariant] = useState<CharacterSummary['bodyVariant']>('m');
  const [loadedPreviewCharacter, setLoadedPreviewCharacter] = useState<CharacterState | null>(null);

  useEffect(() => {
    if (!user) return;
    services.characters.list(user.id).then((cs) => {
      setCharacterList(cs);
      if (cs.length > 0 && !selected) setSelected(cs[0].id);
    });
  }, [user, setCharacterList, selected]);

  useEffect(() => {
    if (!selected) {
      setLoadedPreviewCharacter(null);
      return;
    }

    let active = true;
    setLoadedPreviewCharacter(null);
    services.characters
      .load(selected)
      .then((state) => {
        if (active) setLoadedPreviewCharacter(state);
      })
      .catch((err) => {
        console.warn('[CharacterSelectScreen] preview load fallback:', err);
        if (active) setLoadedPreviewCharacter(null);
      });

    return () => {
      active = false;
    };
  }, [selected]);

  const selectedSummary = useMemo(
    () => characterList.find((candidate) => candidate.id === selected) ?? null,
    [characterList, selected],
  );

  const createPreviewCharacter = useMemo<CharacterState>(() => ({
    id: 'preview-new-character',
    name: newName.trim() || 'New Hero',
    className: newClass,
    race: newRace,
    bodyVariant: newBodyVariant,
    level: 1,
    xp: 0,
    zoneId: defaultZoneForRace(newRace),
    health: 100,
    maxHealth: 100,
    mana: 100,
    maxMana: 100,
    strength: 10,
    gold: 0,
    position: { x: 0, y: 0, z: 0 },
    rotationY: 0,
    equipment: {},
  }), [newClass, newName, newRace, newBodyVariant]);

  const previewCharacter = showCreate
    ? createPreviewCharacter
    : loadedPreviewCharacter ?? (selectedSummary ? summaryToPreviewState(selectedSummary) : null);

  async function enterWorld() {
    if (!selected) return;
    const state = await services.characters.load(selected);
    setCharacter(state);
    setScreen('world');
  }

  async function createCharacter(e: React.FormEvent) {
    e.preventDefault();
    if (!user || !newName.trim()) return;
    const created = await services.characters.create(user.id, {
      name: newName.trim(),
      className: newClass,
      race: newRace,
      bodyVariant: newBodyVariant,
    });
    const cs = await services.characters.list(user.id);
    setCharacterList(cs);
    setSelected(created.id);
    setShowCreate(false);
    setNewName('');
  }

  async function logout() {
    await services.auth.signOut();
    setUser(null);
    setScreen('login');
  }

  return (
    <div className="fullscreen-centered character-select-screen">
      <div className="character-select-shell">
        <div className="panel character-select-panel">
          <div className="character-select-header">
            <div>
              <div className="backend-tag">Backend: {services.backend}</div>
              <h1>Choose Your Hero</h1>
              <p className="character-userline">Signed in as {user?.email}</p>
            </div>
            <div className="character-count">
              <strong>{characterList.length}</strong>
              <span>{characterList.length === 1 ? 'Hero' : 'Heroes'}</span>
            </div>
          </div>

          <div className="character-list" aria-label="Character list">
            {characterList.length === 0 && (
              <div className="character-empty">
                No characters yet. Create one below to begin your campaign.
              </div>
            )}
            {characterList.map((c) => {
              const isOrder = ORDER_RACES.includes(c.race);
              return (
                <button
                  type="button"
                  key={c.id}
                  className={`character-row ${selected === c.id ? 'selected' : ''}`}
                  onClick={() => setSelected(c.id)}
                  aria-pressed={selected === c.id}
                >
                  <div className="character-row-main">
                    <div className="name">{c.name}</div>
                    <div className="meta">
                      Lv {c.level} {BODY_VARIANT_DISPLAY[c.bodyVariant ?? 'm']} {RACE_DISPLAY[c.race] ?? c.race} {normalizeClassName(c.className)} &mdash; {c.zoneId}
                    </div>
                  </div>
                  <span className={`realm-tag ${isOrder ? 'order' : 'destruction'}`}>
                    {isOrder ? 'Order' : 'Destruction'}
                  </span>
                </button>
              );
            })}
          </div>

          {showCreate && (
            <form className="create-form" onSubmit={createCharacter}>
              <div className="create-form-fields">
                <div className="field">
                  <label>Name</label>
                  <input
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    maxLength={18}
                    autoFocus
                  />
                </div>
                <div className="field">
                  <label>Race</label>
                  <select
                    value={newRace}
                    onChange={(e) => {
                      const r = e.target.value as CharacterSummary['race'];
                      setNewRace(r);
                      setNewClass(CLASSES_BY_RACE[r][0]);
                    }}
                  >
                    <optgroup label="Order">
                      {ORDER_RACES.map((r) => (
                        <option key={r} value={r}>{RACE_DISPLAY[r]}</option>
                      ))}
                    </optgroup>
                    <optgroup label="Destruction">
                      {DESTRUCTION_RACES.map((r) => (
                        <option key={r} value={r}>{RACE_DISPLAY[r]}</option>
                      ))}
                    </optgroup>
                  </select>
                </div>
                <div className="field">
                  <label>Class</label>
                  <select value={newClass} onChange={(e) => setNewClass(e.target.value)}>
                    {CLASSES_BY_RACE[newRace].map((c) => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div className="field">
                  <label>Body</label>
                  <select
                    value={newBodyVariant}
                    onChange={(e) => setNewBodyVariant(e.target.value as CharacterSummary['bodyVariant'])}
                  >
                    {BODY_VARIANTS.map((variant) => (
                      <option key={variant} value={variant}>{BODY_VARIANT_DISPLAY[variant]}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="create-form-actions">
                <button type="submit" disabled={!newName.trim()}>
                  Create
                </button>
                <button type="button" onClick={() => setShowCreate(false)}>
                  Cancel
                </button>
              </div>
            </form>
          )}

          <div className="character-actions">
            <button onClick={logout}>Log Out</button>
            <button onClick={() => setShowCreate((v) => !v)}>
              {showCreate ? 'Close' : 'New Character'}
            </button>
            <button className="primary-action" onClick={enterWorld} disabled={!selected}>
              Enter World
            </button>
          </div>
        </div>
        <CharacterPreviewStage character={previewCharacter} />
      </div>
    </div>
  );
}

function defaultZoneForRace(race: CharacterSummary['race']): string {
  return ORDER_RACES.includes(race) ? 'altdorf' : 'inevitable_city';
}

function summaryToPreviewState(summary: CharacterSummary): CharacterState {
  return {
    ...summary,
    bodyVariant: summary.bodyVariant ?? 'm',
    xp: 0,
    health: 100,
    maxHealth: 100,
    mana: 100,
    maxMana: 100,
    strength: 10,
    gold: 0,
    position: { x: 0, y: 0, z: 0 },
    rotationY: 0,
    equipment: {},
  };
}
