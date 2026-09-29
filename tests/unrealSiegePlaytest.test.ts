import { describe, expect, it } from 'vitest';
import { siegeArguments, siegeStartupStatus, validateSiegeRounds } from '../scripts/unreal/siege-playtest';

describe('isolated siege playtest', () => {
  it('requires three actual results and client activity without claiming human or release acceptance', () => {
    const report = { passed: true, humanPlaytest: false, releaseApproved: false, movementCm: 2000, actionRequests: 5,
      rounds: [1,2,3].map(round => ({ round, elapsed: 840, deaths: 2, milestones: 1, attackersWon: false })) };
    expect(() => validateSiegeRounds(report)).not.toThrow();
    for (const change of [{ humanPlaytest: true }, { movementCm: 0 }, { actionRequests: 0 }, { actionRequests: Infinity },
      { rounds: report.rounds.slice(1) }, { rounds: report.rounds.map(r => ({ ...r, elapsed: 10 })) },
      { rounds: report.rounds.map(r => ({ ...r, attackersWon: true })) },
      { rounds: report.rounds.map(r => ({ ...r, attackersWon: 'false' })) },
      { rounds: report.rounds.map(r => ({ ...r, milestones: -1 })) }])
      expect(() => validateSiegeRounds({ ...report, ...change })).toThrow();
  });
  it('binds the server exclusively to loopback and connects both clients there', () => {
    const server = siegeArguments('server', 18001);
    expect(server).toContain('-MULTIHOME=127.0.0.1');
    expect(server).toContain('/Game/Capitals/Siege/AegisCapital_Siege');
    expect(server[1]).toBe('/Game/Capitals/Siege/AegisCapital_Siege');
    expect(server).toContain('-WarSiegePlaytest');
    expect(server).not.toContain('-WarDevelopmentGM');
    for (const role of ['aegis', 'riftbound'] as const) {
      const client = siegeArguments(role, 18001, 2560, 1080);
      expect(client).toContain('127.0.0.1:18001');
      expect(client[1]).toBe('127.0.0.1:18001');
      expect(client).toContain('-ResX=2560');
      expect(client).not.toContain('-nullrhi');
      expect(client).not.toContain('-unattended');
    }
  });
  it('rejects invalid invocation values before launching processes', () => {
    for (const port of [0, 1023, 65536, NaN, 18000.5]) expect(() => siegeArguments('server', port)).toThrow();
    expect(() => siegeArguments('server', 18001, NaN, 720)).toThrow();
    expect(() => siegeArguments('server', 18001, 1280, 0)).toThrow();
  });
  it('never interprets successful listening as content or gameplay readiness', () => {
    expect(siegeStartupStatus('IpNetDriver listening on port 18001')).toEqual({ listening: true, blocked: null, contentReady: false });
    expect(siegeStartupStatus('WAR_SIEGE_CONTENT_BLOCKED Missing healer\nWAR_SIEGE_CONTENT_BLOCKED Missing engineer\n').blocked).toBe('Missing engineer');
  });
  it('uses the latest content state after a recoverable loading failure', () => {
    const repaired = siegeStartupStatus('WAR_SIEGE_CONTENT_BLOCKED Missing healer\nWAR_SIEGE_CONTENT_READY\n');
    expect(repaired.blocked).toBeNull();
    expect(repaired.contentReady).toBe(true);
    expect(siegeStartupStatus('WAR_SIEGE_CONTENT_READY\nWAR_SIEGE_CONTENT_BLOCKED Missing engineer\n').contentReady).toBe(false);
  });
});
