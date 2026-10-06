import { randomUUID } from 'node:crypto';
import { copyFileSync, existsSync, mkdirSync, readFileSync } from 'node:fs';
import { spawnSync } from 'node:child_process';
import path from 'node:path';
import { defaultEngineRoot, inspectToolchain, isMain, parseArguments, projectPath, repoRoot } from './toolchain';

export function gmRenderingArguments(mode: string, run: string, map: string, host = 'standalone'): string[] {
  if (!['pointer', 'input', 'keyboard', 'direct', 'idle', 'manual'].includes(mode)) throw new Error('Expected pointer, input, keyboard, direct, idle or manual mode.');
  if (!/^[a-f0-9]{32}$/.test(run)) throw new Error('An isolated run ID is required.');
  if (!/^\/Game\/[A-Za-z0-9_/]+$/.test(map)) throw new Error('Expected a local native map package.');
  if (!['standalone', 'pie'].includes(host)) throw new Error('Expected standalone or pie host.');
  const folder = path.join(repoRoot, 'unreal/AegisWar/Saved/GmRenderingProof', run);
  return [projectPath, map, ...(host === 'standalone' ? ['-game'] : []),
    ...(mode === 'manual' ? [] : ['-RenderOffscreen']), '-windowed', '-ForceRes', '-ResX=1280', '-ResY=800',
    '-unattended', '-nop4', '-nosound', '-nosplash', '-WarDevelopmentGM', '-WarInterfaceProof', '-WarGmRenderingProof',
    `-WarProofDraftId=${run}`, `-GameUserSettingsINI=${path.join(folder, 'GmRenderingProof.ini')}`,
    `-EditorPerProjectUserSettingsINI=${path.join(folder, 'GmRenderingEditor.ini')}`,
    `-EditorSettingsINI=${path.join(folder, 'GmRenderingEditorGlobal.ini')}`,
    `-abslog=${path.join(folder, 'game.log')}`,
    `-ExecCmds=t.MaxFPS 30${host === 'pie' ? `,py ${path.join(repoRoot, 'scripts/unreal/gm-rendering-pie.py')}` : ''}`,
    ...(mode === 'direct' ? ['-WarGmRenderingDirect'] : mode === 'idle' ? ['-WarGmRenderingIdle'] : mode === 'input' ? ['-WarGmRenderingHitTest'] : mode === 'keyboard' ? ['-WarGmRenderingKeyboard'] : mode === 'manual' ? ['-WarGmRenderingManual'] : [])];
}

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), [], ['--mode', '--host']);
    const config = readFileSync(path.join(repoRoot, 'unreal/AegisWar/Config/DefaultEngine.ini'), 'utf8');
    const map = config.match(/^GameDefaultMap=(.+)$/m)?.[1].trim();
    if (!map) throw new Error('Missing GameDefaultMap.');
    const run = randomUUID().replaceAll('-', '');
    const mode = args.get('--mode') ?? 'pointer';
    const invocation = gmRenderingArguments(mode, run, map, args.get('--host') ?? 'standalone');
    const engine = inspectToolchain(defaultEngineRoot());
    if (!engine.editorCommand || engine.blockers.length) throw new Error(engine.blockers.join('\n'));
    const folder = path.join(repoRoot, 'unreal/AegisWar/Saved/GmRenderingProof', run);
    mkdirSync(folder, { recursive: true });
    const preferences = path.join(repoRoot, 'unreal/AegisWar/Saved/Config/WindowsEditor/GameUserSettings.ini');
    if (existsSync(preferences)) copyFileSync(preferences, path.join(folder, 'GmRenderingProof.ini'));
    console.log(JSON.stringify({ run, folder, map }));
    const executable = mode === 'manual' ? engine.editorCommand.replace(/-Cmd\.exe$/i, '.exe') : engine.editorCommand;
    const result = spawnSync(executable, invocation, { cwd: repoRoot, stdio: 'inherit', timeout: mode === 'manual' ? 900_000 : 300_000, windowsHide: mode !== 'manual' });
    if (result.error || result.status !== 0) throw new Error(`GM rendering proof failed: ${result.error?.message ?? result.status}; ${folder}`);
    const report = JSON.parse(readFileSync(path.join(folder, 'report.json'), 'utf8').replace(/^\uFEFF/, ''));
    if (report.completed !== true || report.passed !== true) throw new Error('Missing successful diagnostic completion.');
    for (const step of mode === 'manual' ? ['00-baseline'] : ['00-baseline', '01-open', '02-flight', '03-closed', '04-settled', '06-speed', '07-speed-closed', '08-return', '09-walking', '10-final',
      '11-departure', '12-destination', '13-return-pending', '14-capital', '16-roundtrip', '17-roundtrip-settled',
      ...(mode === 'keyboard' ? ['18-guide', '19-guide-closed', '20-f3', '21-f4', '22-f5', '23-keyboard-settled'] : [])]) {
      if (!existsSync(path.join(folder, `${step}.json`)) || !existsSync(path.join(folder, `${step}.png`)) || !existsSync(path.join(folder, `${step}-scene.png`)))
        throw new Error(`Missing state or screenshot for ${step}: ${folder}`);
    }
    if (mode === 'keyboard') {
      const baseline = JSON.parse(readFileSync(path.join(folder, '00-baseline.json'), 'utf8').replace(/^\uFEFF/, ''));
      for (const step of ['02-flight', '04-settled', '07-speed-closed', '17-roundtrip-settled', '19-guide-closed', '23-keyboard-settled']) {
        const state = JSON.parse(readFileSync(path.join(folder, `${step}.json`), 'utf8').replace(/^\uFEFF/, ''));
        if (typeof baseline.viewMode !== 'number' || state.viewMode !== baseline.viewMode || state.showFlags !== baseline.showFlags)
          throw new Error(`Keyboard input changed viewport rendering at ${step}: ${folder}`);
      }
    }
    console.log(JSON.stringify({ ...report, folder }));
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}
