import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

export const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
export const projectPath = path.join(repoRoot, 'unreal/AegisWar/AegisWar.uproject');
export const requiredVersion = '5.8.2';

export interface ToolchainReport {
  engineRoot: string | null;
  engineVersion: string | null;
  requiredVersion: string;
  host: string;
  editorCommand: string | null;
  buildCommand: string | null;
  automationCommand: string | null;
  installedBuild: boolean;
  blockers: string[];
  limitations: string[];
}

export function inspectToolchain(engineRoot: string | undefined, host = process.platform): ToolchainReport {
  const root = engineRoot ? path.resolve(engineRoot) : null;
  const report: ToolchainReport = {
    engineRoot: root, engineVersion: null, requiredVersion, host,
    editorCommand: null, buildCommand: null, automationCommand: null, installedBuild: false,
    blockers: [], limitations: [
      'File discovery does not prove compiler/SDK availability, native compilation, packaging, Steam authentication, or performance.',
      'Linux and macOS acceptance requires actual builds and playtests on those platforms.',
    ],
  };
  if (!root) {
    report.blockers.push('Set UNREAL_ENGINE_ROOT or --engine-root to the complete Unreal 5.8.2 installation.');
    return report;
  }
  const versionPath = path.join(root, 'Engine/Build/Build.version');
  if (!existsSync(versionPath)) {
    report.blockers.push(`Missing ${versionPath}; a launcher .egstore directory is not an installed engine.`);
  } else {
    try {
      const v = JSON.parse(readFileSync(versionPath, 'utf8'));
      report.engineVersion = `${v.MajorVersion}.${v.MinorVersion}.${v.PatchVersion}`;
      if (report.engineVersion !== requiredVersion) report.blockers.push(`Expected Unreal ${requiredVersion}; found ${report.engineVersion}.`);
    } catch { report.blockers.push('Engine Build.version is not valid JSON.'); }
  }
  const suffix = host === 'win32' ? 'bat' : 'sh';
  const platformFolder = host === 'win32' ? '' : host === 'darwin' ? 'Mac/' : 'Linux/';
  const candidates = {
    editorCommand: host === 'win32' ? 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
      : host === 'darwin' ? 'Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor' : 'Engine/Binaries/Linux/UnrealEditor',
    buildCommand: `Engine/Build/BatchFiles/${platformFolder}Build.${suffix}`,
    automationCommand: `Engine/Build/BatchFiles/RunUAT.${suffix}`,
  };
  for (const key of ['editorCommand', 'buildCommand', 'automationCommand'] as const) {
    const candidate = path.join(root, candidates[key]);
    if (existsSync(candidate)) report[key] = candidate;
    else report.blockers.push(`Missing ${candidates[key]}.`);
  }
  report.installedBuild = existsSync(path.join(root, 'Engine/Build/InstalledBuild.txt'));
  if (report.installedBuild) report.limitations.push('Dedicated server targets may require a source/installed engine built with server support.');
  return report;
}

export function defaultEngineRoot(): string | undefined {
  if (process.env.UNREAL_ENGINE_ROOT) return process.env.UNREAL_ENGINE_ROOT;
  const candidates = process.platform === 'win32'
    ? ['C:/Program Files/Epic Games/UE_5.8']
    : process.platform === 'darwin' ? ['/Users/Shared/Epic Games/UE_5.8'] : [];
  return candidates.find(candidate => existsSync(candidate));
}

export function parseArguments(args: string[], allowedFlags: string[], allowedValues: string[]): Map<string, string> {
  const result = new Map<string, string>();
  for (let i = 0; i < args.length; i++) {
    const key = args[i];
    if (result.has(key)) throw new Error(`Duplicate option ${key}`);
    if (allowedFlags.includes(key)) result.set(key, 'true');
    else if (allowedValues.includes(key) && args[i + 1] && !args[i + 1].startsWith('--')) result.set(key, args[++i]);
    else throw new Error(`Unknown option or missing value: ${key}`);
  }
  return result;
}

export function isMain(moduleUrl: string): boolean {
  return Boolean(process.argv[1]) && path.resolve(process.argv[1]) === fileURLToPath(moduleUrl);
}

export function runEngineCommand(command: string, args: string[]): number {
  // Encode a literal PowerShell invocation, never interpolate paths into cmd.exe syntax.
  const literal = (value: string) => `'${value.replaceAll("'", "''")}'`;
  const windowsBatch = process.platform === 'win32' && /\.bat$/i.test(command);
  const executable = windowsBatch ? 'powershell.exe' : command;
  const invocation = `& ${[command, ...args].map(literal).join(' ')}; exit $LASTEXITCODE`;
  const commandArgs = windowsBatch
    ? ['-NoProfile', '-NonInteractive', '-EncodedCommand', Buffer.from(invocation, 'utf16le').toString('base64')]
    : args;
  const result = spawnSync(executable, commandArgs, { cwd: repoRoot, stdio: 'inherit', windowsHide: true });
  if (result.error) throw result.error;
  return result.status ?? 1;
}

if (isMain(import.meta.url)) {
  try {
    const args = parseArguments(process.argv.slice(2), [], ['--engine-root']);
    const report = inspectToolchain(args.get('--engine-root') ?? defaultEngineRoot());
    console.log(JSON.stringify(report, null, 2));
    if (report.blockers.length) process.exitCode = 1;
  } catch (error) { console.error(error instanceof Error ? error.message : error); process.exitCode = 1; }
}
