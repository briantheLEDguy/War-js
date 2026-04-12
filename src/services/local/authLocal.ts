import type { AuthService, User } from '../types';

const STORAGE_KEY = 'war-js:local-user';

export class AuthLocal implements AuthService {
  private user: User | null = null;

  constructor() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) this.user = JSON.parse(raw);
    } catch {
      /* ignore */
    }
  }

  async signIn(email: string, _password: string): Promise<User> {
    const user: User = {
      id: `local-${btoa(email).replace(/=+$/, '')}`,
      email,
    };
    this.user = user;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(user));
    } catch {
      /* ignore */
    }
    return user;
  }

  async signOut(): Promise<void> {
    this.user = null;
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  }

  currentUser(): User | null {
    return this.user;
  }
}
