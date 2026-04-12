import { useEffect, useRef, useState } from 'react';
import { services } from '../../services';
import { useGameStore } from '../../state/gameStore';

export function ChatPanel() {
  const [value, setValue] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);
  const logRef = useRef<HTMLDivElement>(null);
  const chat = useGameStore((s) => s.chat);
  const chatFocused = useGameStore((s) => s.chatFocused);
  const setChatFocused = useGameStore((s) => s.setChatFocused);
  const character = useGameStore((s) => s.character);

  useEffect(() => {
    if (chatFocused) inputRef.current?.focus();
  }, [chatFocused]);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [chat.length]);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    const v = value.trim();
    setValue('');
    if (v) {
      await services.chat.send('zone', character?.name ?? 'You', v);
    }
    setChatFocused(false);
    inputRef.current?.blur();
  }

  return (
    <div className="chat">
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
    </div>
  );
}
