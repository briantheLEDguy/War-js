import { env } from '../config/env';
import type { User } from '../services/types';

export function canUseGmTools(user: User | null): boolean {
  if (!env.gmEnabled || !user?.email) return false;
  if (env.gmEmails.includes('*')) return true;
  return env.gmEmails.includes(user.email.toLowerCase());
}

export function gmAccessMessage(user: User | null): string {
  if (!env.gmEnabled) {
    return 'GM tools are disabled. Set VITE_GM_ENABLED=true and restart the dev server.';
  }
  if (!user?.email) {
    return 'GM tools require a signed-in user.';
  }
  return `GM tools are not enabled for ${user.email}. Add it to VITE_GM_EMAILS.`;
}
