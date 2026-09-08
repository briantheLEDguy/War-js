import { resolve } from 'node:path';
import { createClient } from '@supabase/supabase-js';
import { startAuthority } from './authority';
import { DevelopmentAuthenticator, SupabaseAuthenticator } from './auth';
import { FileCampaignRepository, SupabaseCampaignRepository } from './persistence';
import { loadCampaignMapConfigs } from './mapConfig';
import { campaignAbilityRules } from './abilityCatalog';

const development = process.argv.includes('--dev-auth');
const campaignId = process.env.ORVR_CAMPAIGN_ID ?? 'world-orvr-v1';
const secret = process.env.SUPABASE_SECRET_KEY;
const url = process.env.SUPABASE_URL;
const publishable = process.env.SUPABASE_PUBLISHABLE_KEY;
if (!development && (!url || !secret || !publishable)) throw new Error('Configure SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY and server-only SUPABASE_SECRET_KEY, or use --dev-auth for loopback testing.');
const database = !development ? createClient(url!, secret!, { auth: { persistSession: false, autoRefreshToken: false } }) : null;
const server = await startAuthority({
  host: process.env.ORVR_HOST ?? '127.0.0.1',
  port: Number(process.env.ORVR_PORT ?? 8788),
  campaign: { id: campaignId, zones: await loadCampaignMapConfigs(), abilities: campaignAbilityRules() },
  allowedOrigins: process.env.ORVR_ALLOWED_ORIGINS?.split(',').map(value => value.trim()).filter(Boolean),
  auth: database ? new SupabaseAuthenticator(url!, publishable!, database) : new DevelopmentAuthenticator(),
  repository: database ? new SupabaseCampaignRepository(database, campaignId) : new FileCampaignRepository(resolve(process.env.ORVR_CHECKPOINT ?? 'artifacts/orvr/campaign.json')),
});
console.info(`[orvr] Shared authority listening at ${server.url} (${development ? 'loopback development sessions' : 'Supabase authentication'})`);
let stopping = false;
const stop = async () => { if (stopping) return; stopping = true; await server.close(); process.exit(0); };
process.on('SIGINT', stop);
process.on('SIGTERM', stop);
