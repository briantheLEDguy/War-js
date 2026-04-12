import type { AuthService, User } from '../types';
import { NotImplementedError } from '../types';

/**
 * TODO(phase2): Wire Supabase Auth.
 *   - signIn: supabase.auth.signInWithPassword({ email, password })
 *   - signOut: supabase.auth.signOut()
 *   - currentUser: supabase.auth.getUser() (memoize via onAuthStateChange)
 */
export class AuthSupabase implements AuthService {
  signIn(_email: string, _password: string): Promise<User> {
    throw new NotImplementedError('AuthSupabase.signIn');
  }
  signOut(): Promise<void> {
    throw new NotImplementedError('AuthSupabase.signOut');
  }
  currentUser(): User | null {
    throw new NotImplementedError('AuthSupabase.currentUser');
  }
}
