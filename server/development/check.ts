export const developmentAuthUrl = 'https://mfwnnvnvchwureeckdfx.supabase.co';
export function gatewayUrl(value: string | undefined): string | null {
  try {
    const url = new URL(value ?? '');
    if (url.protocol !== 'https:' || url.username || url.password || url.search || url.hash || url.pathname !== '/') return null;
    return url.origin;
  } catch { return null; }
}

/** Read-only startup diagnostics. Never send account tokens or server secrets. */
export async function checkDevelopment(env: NodeJS.ProcessEnv, request: typeof fetch = fetch) {
  const issues: string[] = [];
  const key = env.AEGIS_DEV_PUBLISHABLE_KEY;
  let githubEnabled = false, gatewayReachable = false;
  if (!key?.startsWith('sb_publishable_')) issues.push('Configure the development publishable key in .env.development.');
  else {
    try {
      const response = await request(`${developmentAuthUrl}/auth/v1/settings`, {
        headers:{apikey:key}, redirect:'error', signal:AbortSignal.timeout(10000),
      });
      if (!response.ok) issues.push('Development Auth rejected the publishable key.');
      else {
        const settings = await response.json() as { external?: { github?: boolean } };
        githubEnabled = settings.external?.github === true;
        if (!githubEnabled) issues.push('Enable the GitHub provider in the development Supabase project.');
      }
    } catch { issues.push('Development Auth could not be reached.'); }
  }
  const gateway = gatewayUrl(env.AEGIS_DEV_GATEWAY_URL);
  if (!gateway) issues.push('Configure AEGIS_DEV_GATEWAY_URL as the trusted HTTPS gateway origin.');
  else {
    try {
      const response = await request(`${gateway}/session`, {redirect:'error',signal:AbortSignal.timeout(10000)});
      gatewayReachable = response.status === 401 && response.headers.get('content-type')?.includes('application/json') === true;
      if (!gatewayReachable) issues.push('Gateway did not return the expected authentication challenge.');
    } catch { issues.push('Gateway could not be reached with verified TLS.'); }
  }
  return {project:'aegiswar-development',githubEnabled,gatewayReachable,
    authenticatedLoginVerified:false,runtimeDeploymentVerified:false,issues};
}
