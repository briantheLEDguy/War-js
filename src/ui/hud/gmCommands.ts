export type GmCommandAction = 'open_menu' | 'build_on' | 'build_off' | 'help';

export interface ParsedGmCommand {
  handled: boolean;
  action?: GmCommandAction;
}

export const GM_COMMAND_HELP = 'GM commands: /gm, /gm menu, /gm build, /gm build off';

export function parseGmCommand(input: string): ParsedGmCommand {
  const parts = input.trim().toLowerCase().split(/\s+/).filter(Boolean);
  if (parts[0] !== '/gm') return { handled: false };

  if (parts.length === 1 || (parts.length === 2 && parts[1] === 'menu')) {
    return { handled: true, action: 'open_menu' };
  }

  if (parts.length === 2 && parts[1] === 'build') {
    return { handled: true, action: 'build_on' };
  }

  if (parts.length === 3 && parts[1] === 'build' && parts[2] === 'on') {
    return { handled: true, action: 'build_on' };
  }

  if (
    (parts.length === 2 && (parts[1] === 'off' || parts[1] === 'exit')) ||
    (parts.length === 3 && parts[1] === 'build' && parts[2] === 'off')
  ) {
    return { handled: true, action: 'build_off' };
  }

  return { handled: true, action: 'help' };
}
