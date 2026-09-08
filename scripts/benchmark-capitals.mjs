import { createRequire } from 'node:module';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export async function benchmarkCapitals(options = {}) {
  const url = options.url ?? 'http://127.0.0.1:4000/';
  const output = path.resolve(options.output ?? 'artifacts/performance/run');
  const runs = Number(options.runs ?? 3);
  const seconds = Number(options.seconds ?? 60);
  const require = createRequire(path.resolve(options.driver ?? 'tmp/perf-tools/package.json'));
  const { chromium } = require('playwright');
  await mkdir(output, { recursive: true });
  const browser = await chromium.launch({ executablePath: options.chrome ?? 'C:/Program Files/Google/Chrome/Application/chrome.exe',
    headless: true, args: ['--disable-background-timer-throttling', '--disable-renderer-backgrounding',
      ...(options.gpu === 'high' ? ['--force-high-performance-gpu', '--force_high_performance_gpu'] : [])] });
  const summary = [];
  const percentile = (values, fraction) => [...values].sort((a, b) => a - b)[Math.min(values.length - 1, Math.floor(values.length * fraction))] ?? 0;
  try {
    for (const character of (options.character ? [options.character] : ['Sigmund', 'Grik'])) {
      for (let run = 1; run <= runs; run++) {
        const context = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
        const page = await context.newPage();
        const errors = [];
        const consoleErrors = [];
        const resourceFailures = [];
        const resourceUrl = value => { const parsed = new URL(value); return /^https?:$/.test(parsed.protocol)
          ? parsed.origin + parsed.pathname : parsed.protocol; };
        page.on('pageerror', error => errors.push(error.message));
        page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
        page.on('requestfailed', request => resourceFailures.push({ url: resourceUrl(request.url()), error: request.failure()?.errorText }));
        page.on('response', response => { if (response.status() >= 400) resourceFailures.push({ url: resourceUrl(response.url()), status: response.status() }); });
        await page.addInitScript(() => localStorage.setItem('war-js:gameplay-settings', JSON.stringify({
          renderResolution: 'native', frameRateLimit: 60, viewDistance: 350,
        })));
        await page.goto(`${url}${url.includes('?') ? '&' : '?'}performance`, { timeout: 120_000 });
        await page.getByRole('button', { name: 'Enter Campaign', exact: true }).click();
        await page.getByRole('button', { name: new RegExp(character) }).click();
        await page.getByRole('button', { name: 'Enter World', exact: true }).click();
        await page.waitForFunction(() => (window.__warPerformance?.snapshot().length ?? 0) >= 30, { }, { timeout: 180_000 });
        await page.locator('.loading').waitFor({ state: 'hidden', timeout: 180_000 });
        // Warm the same orbit used for measurement, including its shader/LOD variants.
        const orbit = async step => {
          await page.mouse.move(640, 300);
          await page.mouse.down({ button: 'left' });
          await page.mouse.move(640 + (step % 2 ? -180 : 180), 315, { steps: 12 });
          await page.mouse.up({ button: 'left' });
        };
        for (let step = 0; step < 4; step++) { await orbit(step); await page.waitForTimeout(2500); }
        const renderer = await page.evaluate(() => {
          const gl = document.querySelector('.game-canvas-container canvas')?.getContext('webgl2');
          const extension = gl?.getExtension('WEBGL_debug_renderer_info');
          return { name: extension && gl.getParameter(extension.UNMASKED_RENDERER_WEBGL), multiDraw: !!gl?.getExtension('WEBGL_multi_draw') };
        });
        await page.evaluate(() => window.__warPerformance.reset());
        const start = Date.now();
        for (let step = 0; step < seconds / 10; step++) {
          if (step >= 2 && step < 4) await orbit(step);
          // Short return steps exercise movement without crossing the nearby city exit.
          if (step >= 4) for (let move = 0; move < 8; move++) {
            await page.keyboard.down('w'); await page.waitForTimeout(450); await page.keyboard.up('w');
            await page.keyboard.down('s'); await page.waitForTimeout(450); await page.keyboard.up('s');
          }
          await page.waitForTimeout(Math.max(0, start + (step + 1) * 10_000 - Date.now()));
          console.log(`${character} run ${run}: ${step + 1}0 seconds`);
        }
        await page.keyboard.up('w'); await page.keyboard.up('s');
        const samples = await page.evaluate(() => window.__warPerformance.snapshot());
        if (!samples.length || await page.locator('.loading').count()) {
          await page.screenshot({ path: path.join(output, `${character}-${run}-interrupted.png`) });
          throw new Error('Benchmark interrupted by loading/reload; rerun on a stable build.');
        }
        const intervals = samples.map(sample => sample.intervalMs);
        const result = { character, run, url, renderer, viewport: '1280x720', resolution: 'native', viewDistance: 350,
          frames: samples.length, fps: samples.length * 1000 / intervals.reduce((sum, value) => sum + value, 0),
          p50Ms: percentile(intervals, .5), p95Ms: percentile(intervals, .95), p99Ms: percentile(intervals, .99),
          stallsOver100Ms: intervals.filter(value => value > 100).length,
          simulationP95Ms: percentile(samples.map(sample => sample.simulationMs), .95),
          cameraP95Ms: percentile(samples.map(sample => sample.cameraMs), .95),
          submissionP95Ms: percentile(samples.map(sample => sample.submissionMs), .95),
          callsP50: percentile(samples.map(sample => sample.calls), .5), errors, consoleErrors, resourceFailures };
        await page.screenshot({ path: path.join(output, `${character}-${run}.png`) });
        await writeFile(path.join(output, `${character}-${run}.json`), JSON.stringify({ ...result, samples }, null, 2));
        summary.push(result);
        await writeFile(path.join(output, 'summary.json'), JSON.stringify(summary, null, 2));
        console.log(JSON.stringify(result));
        await context.close();
      }
    }
  } finally { await browser.close(); }
  return summary;
}

if (typeof process !== 'undefined' && process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await benchmarkCapitals(Object.fromEntries(process.argv.slice(2).map(arg => arg.replace(/^--/, '').split('='))));
}
