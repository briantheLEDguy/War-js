import { useEffect, useRef, useState } from 'react';
import { canUseGmTools, gmAccessMessage } from '../../editor/gmAuth';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';

export function ChatPanel() {
  const [value, setValue] = useState('');
  const inputRef  = useRef<HTMLInputElement>(null);
  const logRef    = useRef<HTMLDivElement>(null);
  const panelRef  = useRef<HTMLDivElement>(null);

  const chat           = useGameStore((s) => s.chat);
  const chatFocused    = useGameStore((s) => s.chatFocused);
  const setChatFocused = useGameStore((s) => s.setChatFocused);
  const character      = useGameStore((s) => s.character);

  // ── Minimise ──────────────────────────────────────────────────────────────
  const [minimized, setMinimized] = useState(false);

  // ── Drag-to-reposition ────────────────────────────────────────────────────
  // null  = use default CSS position (bottom / left)
  // {x,y} = user has dragged; use top / left inline style
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const dragOffset = useRef<{ dx: number; dy: number } | null>(null);

  function handleDragStart(e: React.PointerEvent<HTMLDivElement>) {
    if (!panelRef.current) return;
    const rect = panelRef.current.getBoundingClientRect();
    dragOffset.current = { dx: e.clientX - rect.left, dy: e.clientY - rect.top };
    e.currentTarget.setPointerCapture(e.pointerId);
  }

  function handleDragMove(e: React.PointerEvent<HTMLDivElement>) {
    if (!dragOffset.current || !panelRef.current) return;
    const panel = panelRef.current;
    let x = e.clientX - dragOffset.current.dx;
    let y = e.clientY - dragOffset.current.dy;
    // Keep fully inside the viewport
    x = Math.max(0, Math.min(x, window.innerWidth  - panel.offsetWidth));
    y = Math.max(0, Math.min(y, window.innerHeight - panel.offsetHeight));
    setPos({ x, y });
  }

  function handleDragEnd() {
    dragOffset.current = null;
  }

  // ── Side-effects ──────────────────────────────────────────────────────────
  useEffect(() => {
    if (chatFocused) inputRef.current?.focus();
  }, [chatFocused]);

  useEffect(() => {
    if (!minimized && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [chat.length, minimized]);

  // ── Chat submit ───────────────────────────────────────────────────────────
  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const v = value.trim();
    setValue('');
    if (v) {
      if (handleGmCommand(v)) {
        setChatFocused(false);
        inputRef.current?.blur();
        return;
      }
      await services.chat.send('zone', character?.name ?? 'You', v);
    }
    setChatFocused(false);
    inputRef.current?.blur();
  }

  function handleGmCommand(command: string): boolean {
    const normalized = command.toLowerCase();
    if (!normalized.startsWith('/gm')) return false;

    const store = useGameStore.getState();
    const user = store.user;
    if (!canUseGmTools(user)) {
      appendSystemMessage(gmAccessMessage(user));
      return true;
    }

    if (normalized === '/gm build' || normalized === '/gm build on') {
      store.setGmBuildMode(true);
      appendSystemMessage('GM build mode enabled.');
      return true;
    }
    if (normalized === '/gm off' || normalized === '/gm build off' || normalized === '/gm exit') {
      store.setGmBuildMode(false);
      appendSystemMessage('GM build mode disabled.');
      return true;
    }

    appendSystemMessage('GM commands: /gm build, /gm build off');
    return true;
  }

  function appendSystemMessage(body: string): void {
    useGameStore.getState().appendChat({
      id: `gm-system-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      channel: 'system',
      from: 'System',
      body,
      timestamp: Date.now(),
    });
  }

  // When dragged: switch from bottom/left CSS to top/left inline style.
  // bottom:'auto' cancels the CSS bottom:20px (or mobile bottom:220px).
  const panelStyle: React.CSSProperties | undefined = pos
    ? { left: pos.x, top: pos.y, bottom: 'auto' }
    : undefined;

  return (
    <div
      ref={panelRef}
      className={`chat${minimized ? ' chat--minimized' : ''}`}
      style={panelStyle}
    >
      {/* Title bar — drag handle (left) + minimize toggle (right) */}
      <div
        className="chat-titlebar"
        onPointerDown={handleDragStart}
        onPointerMove={handleDragMove}
        onPointerUp={handleDragEnd}
        onPointerCancel={handleDragEnd}
      >
        <span className="chat-drag-handle" aria-hidden="true">⠿</span>
        <span className="chat-title">Chat</span>
        <button
          className="chat-minimize-btn"
          /* Stop pointer-down bubbling so clicking this never starts a drag */
          onPointerDown={(e) => e.stopPropagation()}
          onClick={() => setMinimized((m) => !m)}
          title={minimized ? 'Expand chat' : 'Minimise chat'}
        >
          {minimized ? '▲' : '▼'}
        </button>
      </div>

      {!minimized && (
        <>
          <div className="chat-log" ref={logRef}>
            {chat.map((m) => (
              <div key={m.id} className={`chat-msg ${m.channel}`}>
                <span className="from">[{m.from}]</span>
                <span>{m.body}</span>
              </div>
            ))}
          </div>
          <form className="chat-input-row" onSubmit={onSubmit}>
            <input
              ref={inputRef}
              value={value}
              placeholder={chatFocused ? 'Say something...' : 'Press Enter to chat'}
              onChange={(e) => setValue(e.target.value)}
              onFocus={() => setChatFocused(true)}
              onBlur={() => setChatFocused(false)}
              onKeyDown={(e) => {
                if (e.key === 'Escape') {
                  setValue('');
                  setChatFocused(false);
                  inputRef.current?.blur();
                }
              }}
            />
          </form>
        </>
      )}
    </div>
  );
}
