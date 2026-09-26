import { expect, it, vi } from 'vitest';
import { checkDevelopment, gatewayUrl } from '../server/development/check';

it('rejects unsafe or ambiguous gateway endpoints',()=>{
  for(const value of [undefined,'http://host','https://user:pass@host','https://host/path','https://host?token=secret','https://host#fragment']) expect(gatewayUrl(value)).toBeNull();
  expect(gatewayUrl('https://dev.example:8443/')).toBe('https://dev.example:8443');
});
it('checks provider and gateway without claiming authenticated login or deployment',async()=>{
  const fetcher=vi.fn().mockResolvedValueOnce(Response.json({external:{github:true}}))
    .mockResolvedValueOnce(Response.json({error:'Authentication required.'},{status:401}));
  const result=await checkDevelopment({AEGIS_DEV_PUBLISHABLE_KEY:'sb_publishable_test',AEGIS_DEV_GATEWAY_URL:'https://dev.example:8443'},fetcher);
  expect(result).toMatchObject({issues:[],githubEnabled:true,gatewayReachable:true,authenticatedLoginVerified:false,runtimeDeploymentVerified:false});
  expect(fetcher.mock.calls[1][1]).not.toHaveProperty('headers');
});
it('reports missing configuration without using privileged credentials',async()=>{
  const fetcher=vi.fn();
  const result=await checkDevelopment({AEGIS_DEV_PUBLISHABLE_KEY:'sb_secret_forbidden'},fetcher);
  expect(result.issues).toHaveLength(2); expect(fetcher).not.toHaveBeenCalled();
  expect(JSON.stringify(result)).not.toContain('sb_secret');
});
