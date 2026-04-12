import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { env, supabaseEnabled } from '../../config/env';

let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient {
  if (!supabaseEnabled()) {
    throw new Error(
      'Supabase not configured. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env',
    );
  }
  if (!client) {
    client = createClient(env.supabaseUrl, env.supabaseAnonKey, {
      auth: { persistSession: true, autoRefreshToken: true },
    });
  }
  return client;
}
