import { createClient } from '@supabase/supabase-js';
import { DevelopmentService, uuid } from './service';
const [action,target] = process.argv.slice(2);
if (!['bootstrap-owner','approve','revoke','list'].includes(action)) throw new Error('Usage: dev:admin bootstrap-owner | list | approve <UUID> | revoke <UUID>');
const secret=process.env.AEGIS_DEV_SUPABASE_SECRET, token=process.env.AEGIS_DEV_OWNER_ACCESS_TOKEN;
if (!secret || !token) throw new Error('Owner-only operation requires development service credentials and the owner GitHub-authenticated access token in the environment. Never share these with collaborators.');
const client=createClient('https://mfwnnvnvchwureeckdfx.supabase.co',secret,{auth:{persistSession:false,autoRefreshToken:false}});
const service=new DevelopmentService(client);
const identity=await service.identity(token);
if (action==='bootstrap-owner') {
  const {data,error}=await client.from('dev_members').select('user_id').eq('role','owner');
  if (error || data?.length) throw new Error('An owner already exists, or owner lookup failed.');
  const result=await client.from('dev_members').update({role:'owner',status:'approved',generation:identity.generation+1}).eq('user_id',identity.user_id);
  if (result.error) throw new Error('Owner bootstrap failed.');
  console.info('Verified GitHub identity established as the development owner.');
} else {
  if (identity.role!=='owner' || identity.status!=='approved') throw new Error('Approved owner identity required.');
  if (action==='list') {
    const {data,error}=await client.from('dev_members').select('user_id,github_id,status,role');
    if (error) throw new Error('Member lookup failed.');
    console.info(JSON.stringify(data,null,2));
  } else {
    const {error}=await client.rpc('dev_set_member',{p_actor:identity.user_id,p_target:uuid(target),p_status:action==='approve'?'approved':'revoked'});
    if (error) throw new Error('Membership update failed.');
    console.info('Developer access updated.');
  }
}
