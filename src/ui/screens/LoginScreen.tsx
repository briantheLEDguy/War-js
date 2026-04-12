import { useState } from 'react';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';

export function LoginScreen() {
  const [email, setEmail] = useState('recruit@war-js.local');
  const [password, setPassword] = useState('password');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const setUser = useGameStore((s) => s.setUser);
  const setScreen = useGameStore((s) => s.setScreen);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr(null);
    try {
      const u = await services.auth.signIn(email, password);
      setUser(u);
      setScreen('character-select');
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : String(ex));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="fullscreen-centered">
      <div className="panel login-panel">
        <div className="backend-tag">Backend: {services.backend}</div>
        <h1>War-js</h1>
        <p style={{ color: 'var(--dim)', fontSize: 12, marginTop: -8 }}>
          Web vertical slice. Any credentials work in local mode.
        </p>
        <form onSubmit={onSubmit}>
          <div className="field">
            <label>Email</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </div>
          <div className="field">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
          <button type="submit" disabled={busy}>
            {busy ? 'Signing In...' : 'Enter the War'}
          </button>
          {err && <div style={{ color: 'var(--red)', fontSize: 12 }}>{err}</div>}
        </form>
        <div className="hint">
          Session is persisted in localStorage. Clear it to sign out fully.
        </div>
      </div>
    </div>
  );
}
