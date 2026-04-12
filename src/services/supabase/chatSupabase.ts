import type { ChatMessage, ChatService, Unsubscribe } from '../types';
import { NotImplementedError } from '../types';

/**
 * TODO(phase2): Wire Supabase `chat_messages` + Realtime.
 *   - history:   select * from chat_messages where channel = $ order by created_at
 *   - send:      insert row
 *   - subscribe: supabase.channel(`chat:${channel}`)
 *                  .on('broadcast', { event: 'msg' }, payload => cb(payload))
 *                  or .on('postgres_changes', ...).subscribe()
 */
export class ChatSupabase implements ChatService {
  history(_channel: ChatMessage['channel']): Promise<ChatMessage[]> {
    throw new NotImplementedError('ChatSupabase.history');
  }
  send(_channel: ChatMessage['channel'], _from: string, _body: string): Promise<void> {
    throw new NotImplementedError('ChatSupabase.send');
  }
  subscribe(_cb: (msg: ChatMessage) => void): Unsubscribe {
    throw new NotImplementedError('ChatSupabase.subscribe');
  }
}
