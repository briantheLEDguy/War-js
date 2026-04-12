import { useEffect, useState } from 'react';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';
import type { CharacterSummary } from '../../services/types';

const RACES: CharacterSummary['race'][] = ['empire', 'greenskin', 'dwarf', 'elf'];
const CLASSES = ['Warrior', 'Archer', 'Mage', 'Shaman', 'Healer'];

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
  const [newClass, setNewClass] = useState(CLASSES[0]);
  const [newRace, setNewRace] = useState<CharacterSummary['race']>('empire');

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
        <p style={{ color: 'var(--dim)', fontSize: 12, marginTop: -8 }}>
          Signed in as {user?.email}
        </p>

        <div className="character-list">
          {characterList.length === 0 && (
            <div style={{ color: 'var(--dim)', fontSize: 13, padding: '8px 0' }}>
              No characters yet. Create one below.
            </div>
          )}
          {characterList.map((c) => (
            <div
              key={c.id}
              className={`character-row ${selected === c.id ? 'selected' : ''}`}
              onClick={() => setSelected(c.id)}
            >
              <div>
                <div className="name">{c.name}</div>
                <div className="meta">
                  Lv {c.level} {titleCase(c.race)} {c.className} &mdash; {c.zoneId}
                </div>
              </div>
            </div>
          ))}
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
                onChange={(e) => setNewRace(e.target.value as CharacterSummary['race'])}
              >
                {RACES.map((r) => (
                  <option key={r} value={r}>
                    {titleCase(r)}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label>Class</label>
              <select value={newClass} onChange={(e) => setNewClass(e.target.value)}>
                {CLASSES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
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

function titleCase(s: string) {
  return s.slice(0, 1).toUpperCase() + s.slice(1);
}
