import { createHmac, randomBytes, timingSafeEqual } from 'node:crypto';
import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import type { PlayerIdentity, Realm } from '../src/shared/orvr/protocol';
import { recruitCombatProfile } from './abilityCatalog';

export interface Authenticator {
  verify(token: string, characterId: string): Promise<PlayerIdentity>;
}

/** Development credentials are issued only by the loopback-only development server. */
export class DevelopmentAuthenticator implements Authenticator {
  private readonly secret = randomBytes(32);
  private readonly identities = new Map<string, PlayerIdentity>();
  issue(realm: Realm, name: string): { token: string; characterId: string } {
    const characterId = randomBytes(16).toString('hex');
    const identity: PlayerIdentity = {
      id: characterId, characterId, userId: characterId, realm,
      ...recruitCombatProfile(realm),
      displayName: name.trim().slice(0, 32) || (realm === 'aegis' ? 'Aegis Scout' : 'Riftbound Scout'),
    };
    this.identities.set(characterId, identity);
    const payload = Buffer.from(JSON.stringify({ characterId, expires: Date.now() + 8 * 60 * 60 * 1000 })).toString('base64url');
    return { characterId, token: `${payload}.${this.sign(payload)}` };
  }
  async verify(token: string, characterId: string): Promise<PlayerIdentity> {
    const [payload, signature, extra] = token.split('.');
    if (!payload || !signature || extra) throw new Error('Invalid development session.');
    const expected = Buffer.from(this.sign(payload));
    const actual = Buffer.from(signature);
    if (actual.length !== expected.length || !timingSafeEqual(actual, expected)) throw new Error('Invalid session signature.');
    const claims = JSON.parse(Buffer.from(payload, 'base64url').toString('utf8'));
    const identity = this.identities.get(characterId);
    if (!identity || claims.characterId !== characterId || !Number.isFinite(claims.expires) || claims.expires <= Date.now()) {
      throw new Error('Session expired or does not own this character.');
    }
    return { ...identity };
  }
  private sign(payload: string): string { return createHmac('sha256', this.secret).update(payload).digest('base64url'); }
}

export class SupabaseAuthenticator implements Authenticator {
  private readonly client: SupabaseClient;
  constructor(url: string, publishableKey: string, private readonly repository: SupabaseClient) {
    this.client = createClient(url, publishableKey, { auth: { persistSession: false, autoRefreshToken: false } });
  }
  async verify(token: string, characterId: string): Promise<PlayerIdentity> {
    // getUser validates the access token with Auth; editable metadata is never an authority source.
    const { data: userData, error: authError } = await this.client.auth.getUser(token);
    if (authError || !userData.user) throw new Error('Session is invalid or expired.');
    const { data, error } = await this.repository.from('orvr_characters')
      .select('id,user_id,name,realm').eq('id', characterId).eq('user_id', userData.user.id).single();
    if (error || !data || data.id !== characterId || data.user_id !== userData.user.id
      || (data.realm !== 'aegis' && data.realm !== 'riftbound')) throw new Error('Character access denied.');
    // This integration currently issues fixed playtest recruits; persisted unlock progression is not active.
    return {
      id: data.id, characterId: data.id, userId: userData.user.id, displayName: data.name,
      realm: data.realm, ...recruitCombatProfile(data.realm),
    };
  }
}
