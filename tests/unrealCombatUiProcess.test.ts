import { spawn, type ChildProcess } from 'node:child_process';
import { EventEmitter, once } from 'node:events';
import { randomUUID } from 'node:crypto';
import path from 'node:path';
import { describe, expect, it, vi } from 'vitest';
import { stopCombatUiProcesses, trackCombatUiProcess } from '../scripts/unreal/combat-ui-process';

describe('combat UI proof process ownership', () => {
  it('reports failed launches and can clean up after their close event', async () => {
    const child = spawn(path.join(process.cwd(), `missing-engine-${randomUUID()}`), [], { windowsHide: true });
    const tracked = trackCombatUiProcess(child, 'owner');
    // events.once(close) rejects on error; explicitly await the close itself.
    await new Promise<void>(resolve => child.once('close', () => resolve()));
    expect(() => tracked.assertRunning()).toThrow('owner process failed');
    await tracked.stop(100);
  });

  it('recognizes an already completed child without waiting for a second close', async () => {
    const child = spawn(process.execPath, ['-e', 'process.exit(0)'], { windowsHide: true });
    const tracked = trackCombatUiProcess(child, 'server');
    await once(child, 'close');
    expect(() => tracked.assertRunning()).toThrow('exited before proof completion');
    await tracked.stop(100);
  });

  it('awaits shutdown of every owned process and permits repeated cleanup', async () => {
    const children = ['server', 'owner'].map(role => {
      const child = spawn(process.execPath, ['-e', 'setInterval(() => {}, 1000)'], { windowsHide: true });
      return { child, tracked: trackCombatUiProcess(child, role) };
    });
    try {
      await Promise.all(children.map(({ child }) => once(child, 'spawn')));
      for (const { tracked } of children) expect(() => tracked.assertRunning()).not.toThrow();
      await stopCombatUiProcesses(children.map(({ tracked }) => tracked));
      for (const { child, tracked } of children) {
        expect(child.exitCode !== null || child.signalCode !== null).toBe(true);
        expect(() => tracked.assertRunning()).toThrow('exited before proof completion');
      }
      await stopCombatUiProcesses(children.map(({ tracked }) => tracked));
    } finally {
      await stopCombatUiProcesses(children.map(({ tracked }) => tracked));
    }
  });

  it('escalates a stalled child and waits for confirmed closure', async () => {
    vi.useFakeTimers();
    const child = Object.assign(new EventEmitter(), { pid: 123, exitCode: null, signalCode: null,
      kill: vi.fn((signal?: string) => {
        if (signal === 'SIGKILL') child.emit('close');
        return true;
      }) });
    try {
      const tracked = trackCombatUiProcess(child as unknown as ChildProcess, 'owner');
      const stopping = tracked.stop(100);
      await vi.advanceTimersByTimeAsync(100);
      await stopping;
      expect(child.kill.mock.calls).toEqual([[], ['SIGKILL']]);
    } finally { vi.useRealTimers(); }
  });

  it('reports unconfirmed shutdown instead of hanging or claiming resources were released', async () => {
    vi.useFakeTimers();
    const child = Object.assign(new EventEmitter(), { pid: 123, exitCode: null, signalCode: null,
      kill: vi.fn(() => false) });
    try {
      const tracked = trackCombatUiProcess(child as unknown as ChildProcess, 'server');
      const assertion = expect(tracked.stop(100)).rejects.toThrow('shutdown was not confirmed (PID 123)');
      await vi.advanceTimersByTimeAsync(200);
      await assertion;
    } finally { vi.useRealTimers(); }
  });
});
