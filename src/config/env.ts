export const env = {
  supabaseUrl: (import.meta.env.VITE_SUPABASE_URL as string | undefined) ?? '',
  supabaseAnonKey: (import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined) ?? '',
  gmEnabled: ((import.meta.env.VITE_GM_ENABLED as string | undefined) ?? '').toLowerCase() === 'true',
  gmEmails: ((import.meta.env.VITE_GM_EMAILS as string | undefined) ?? '')
    .split(',')
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean),
};

export function supabaseEnabled(): boolean {
  return Boolean(env.supabaseUrl && env.supabaseAnonKey);
}
