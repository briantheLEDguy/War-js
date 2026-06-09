/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUPABASE_URL?: string;
  readonly VITE_SUPABASE_ANON_KEY?: string;
  readonly VITE_ASSET_VERSION?: string;
  readonly VITE_GM_ENABLED?: string;
  readonly VITE_GM_EMAILS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
