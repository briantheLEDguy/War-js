import type { ChildProcess } from 'node:child_process';

/** Attach immediately after spawn so cleanup cannot miss an early close event. */
export function trackCombatUiProcess(child: ChildProcess, role: string) {
  let closed = false;
  let failure: Error | undefined;
  const completion = new Promise<void>(resolve => {
    child.once('close', () => { closed = true; resolve(); });
  });
  child.on('error', error => { failure = error; });

  const waitForClose = (timeoutMs: number) => new Promise<boolean>(resolve => {
    const timer = setTimeout(() => resolve(false), timeoutMs);
    void completion.then(() => { clearTimeout(timer); resolve(true); });
  });

  return {
    assertRunning() {
      if (failure) throw new Error(`${role} process failed: ${failure.message}`);
      if (closed || child.exitCode !== null || child.signalCode !== null) {
        throw new Error(`${role} process exited before proof completion (${child.exitCode ?? child.signalCode})`);
      }
    },
    async stop(timeoutMs = 10000) {
      if (closed) return;
      if (child.pid && child.exitCode === null && child.signalCode === null) child.kill();
      if (await waitForClose(timeoutMs)) return;
      // Only signal the process created by this runner; never kill by image name.
      if (child.pid && child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
      if (!await waitForClose(timeoutMs)) {
        throw new Error(`${role} process shutdown was not confirmed (PID ${child.pid ?? 'unavailable'})`);
      }
    },
  };
}

export async function stopCombatUiProcesses(processes: ReturnType<typeof trackCombatUiProcess>[]) {
  const results = await Promise.allSettled(processes.map(process => process.stop()));
  const failures = results.filter((result): result is PromiseRejectedResult => result.status === 'rejected');
  if (failures.length) throw new AggregateError(failures.map(result => result.reason), 'Combat UI processes were not all confirmed closed');
}
