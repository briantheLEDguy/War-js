import { useEffect, useRef, useState } from 'react';
import { canUseGmTools, gmAccessMessage } from '../../editor/gmAuth';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';
import { GM_COMMAND_HELP, parseGmCommand } from './gmCommands';
import { useDraggableWindow } from './useDraggableWindow';

export function ChatPanel() {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLDivElement>();

  const chat = useGameStore((s) => s.chat);
  const chatFocused = useGameStore((s) => s.chatFocused);
  const setChatFocused = useGameStore((s) => s.setChatFocused);
  const character = useGameStore((s) => s.character);
  const [minimized, setMinimized] = useState(false);

  useEffect(() => {
    if (chatFocused) inputRef.current?.focus();
  }, [chatFocused]);

  useEffect(() => {
    if (!minimized && logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [chat.length, minimized]);

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
    const parsed = parseGmCommand(command);
    if (!parsed.handled) return false;

    const store = useGameStore.getState();
    const user = store.user;
    if (!canUseGmTools(user)) {
      appendSystemMessage(gmAccessMessage(user));
      return true;
    }

    if (parsed.action === 'open_menu') {
      store.setGmMenuOpen(true);
      appendSystemMessage('GM menu opened.');
      return true;
    }
    if (parsed.action === 'build_on') {
      store.setGmBuildMode(true);
      appendSystemMessage('GM build mode enabled.');
      return true;
    }
    if (parsed.action === 'build_off') {
      store.setGmBuildMode(false);
      appendSystemMessage('GM build mode disabled.');
      return true;
    }

    appendSystemMessage(GM_COMMAND_HELP);
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

  return (
    <div
      ref={panelRef}
      className={`chat${minimized ? ' chat--minimized' : ''}${dragClassName}`}
      style={dragStyle}
    >
      <div className="chat-titlebar draggable-window-handle" {...dragHandleProps}>
        <span className="chat-drag-handle" aria-hidden="true">::</span>
        <span className="chat-title">Chat</span>
        <button
          className="chat-minimize-btn"
          onClick={() => setMinimized((m) => !m)}
          aria-label={minimized ? 'Expand chat' : 'Minimise chat'}
          title={minimized ? 'Expand chat' : 'Minimise chat'}
        >
          {minimized ? '+' : '-'}
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
