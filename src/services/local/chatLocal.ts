import type { ChatMessage, ChatService, Unsubscribe } from '../types';

export class ChatLocal implements ChatService {
  private log: ChatMessage[] = [
    {
      id: 'sys-welcome',
      channel: 'system',
      from: 'System',
      body: 'Welcome to War-js. Type a message and press Enter.',
      timestamp: Date.now(),
    },
  ];
  private subs = new Set<(msg: ChatMessage) => void>();

  async history(channel: ChatMessage['channel']): Promise<ChatMessage[]> {
    return this.log.filter((m) => m.channel === channel || m.channel === 'system');
  }

  async send(channel: ChatMessage['channel'], from: string, body: string): Promise<void> {
    const msg: ChatMessage = {
      id: crypto.randomUUID(),
      channel,
      from,
      body,
      timestamp: Date.now(),
    };
    this.log.push(msg);
    for (const s of this.subs) s(msg);
  }

  subscribe(cb: (msg: ChatMessage) => void): Unsubscribe {
    this.subs.add(cb);
    return () => this.subs.delete(cb);
  }
}
