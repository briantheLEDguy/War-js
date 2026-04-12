import { useEffect, useState } from 'react';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';
import type { CharacterSummary } from '../../services/types';

/** WAR realm alignment — determines starting capital city. */
const ORDER_RACES: CharacterSummary['race'][] = ['empire', 'dwarf', 'high_elf'];
const DESTRUCTION_RACES: CharacterSummary['race'][] = ['chaos', 'greenskin', 'dark_elf'];
const ALL_RACES: CharacterSummary['race'][] = [...ORDER_RACES, ...DESTRUCTION_RACES];

/** WAR career lists per race — must match the original game exactly. */
const CAREERS_BY_RACE: Record<CharacterSummary['race'], string[]> = {
  empire:    ['Bright Wizard', 'Witch Hunter', 'Knight of the Blazing Sun', 'Warrior Priest'],
  dwarf:     ['Ironbreaker', 'Slayer', 'Rune Priest', 'Engineer'],
  high_elf:  ['Swordmaster', 'White Lion', 'Archmage', 'Shadow Warrior'],
  chaos:     ['Chosen', 'Marauder', 'Magus', 'Zealot'],
  greenskin: ['Black Orc', 'Squig Herder', 'Shaman', 'Choppa'],
  dark_elf:  ['Witch Elf', 'Blackguard', 'Sorceress', 'Disciple of Khaine'],
};

const RACE_DISPLAY: Record<CharacterSummary['race'], string> = {
  empire:    'Empire',
  dwarf:     'Dwarf',
  high_elf:  'High Elf',
  chaos:     'Chaos',
  greenskin: 'Greenskin',
  dark_elf:  'Dark Elf',
};

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
  const [newClass, setNewClass] = useState(CAREERS_BY_RACE['empire'][0]);

  useEffect(() => {
    if (!user) return;
    services.characters.list(user.id).then((cs) => {
      setCharacterList(cs);
      if (cs.length > 0 && !selected) setSelected(cs[0].id);
    });
  }, [user, setCharacterList, selected]);

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
    <div className="fullscreen-centered">
      <div className="panel character-select-panel">
        <div className="backend-tag">Backend: {services.backend}</div>
        <h1>Choose Your Hero</h1>
        <p style={{ color: 'var(--dim)', fontSize: 12, marginTop: -8, fontStyle: 'italic' }}>
          Signed in as {user?.email}
        </p>

        <div className="character-list">
          {characterList.length === 0 && (
            <div style={{ color: 'var(--dim)', fontSize: 13, padding: '12px 0', textAlign: 'center', fontStyle: 'italic' }}>
              No characters yet. Create one below to begin your campaign.
            </div>
          )}
          {characterList.map((c) => {
            const isOrder = ORDER_RACES.includes(c.race);
            return (
              <div
                key={c.id}
                className={`character-row ${selected === c.id ? 'selected' : ''}`}
                onClick={() => setSelected(c.id)}
              >
                <div>
                  <div className="name">{c.name}</div>
                  <div className="meta">
                    Lv {c.level} {RACE_DISPLAY[c.race] ?? c.race} {c.className} &mdash; {c.zoneId}
                  </div>
                </div>
                <span className={`realm-tag ${isOrder ? 'order' : 'destruction'}`}>
                  {isOrder ? 'Order' : 'Destruction'}
                </span>
              </div>
            );
          })}
        </div>

        {showCreate && (
          <form className="create-form" onSubmit={createCharacter}>
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
                  setNewClass(CAREERS_BY_RACE[r][0]);
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
              <label>Career</label>
              <select value={newClass} onChange={(e) => setNewClass(e.target.value)}>
                {CAREERS_BY_RACE[newRace].map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button type="submit" disabled={!newName.trim()}>
                Create
              </button>
              <button type="button" onClick={() => setShowCreate(false)}>
                Cancel
              </button>
            </div>
          </form>
        )}

        <div className="character-actions" style={{ marginTop: 16 }}>
          <button onClick={logout}>Log Out</button>
          <button onClick={() => setShowCreate((v) => !v)}>
            {showCreate ? 'Close' : 'New Character'}
          </button>
          <button onClick={enterWorld} disabled={!selected}>
            Enter World
          </button>
        </div>
      </div>
    </div>
  );
}

