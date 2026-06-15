import { describe, expect, test } from 'vitest';
import { GM_COMMAND_HELP, parseGmCommand } from '../src/ui/hud/gmCommands';

describe('GM chat commands', () => {
  test('opens the GM menu from /gm', () => {
    expect(parseGmCommand('/gm')).toEqual({ handled: true, action: 'open_menu' });
  });

  test('opens the GM menu from /gm menu', () => {
    expect(parseGmCommand('/GM menu')).toEqual({ handled: true, action: 'open_menu' });
  });

  test('preserves build mode commands', () => {
    expect(parseGmCommand('/gm build')).toEqual({ handled: true, action: 'build_on' });
    expect(parseGmCommand('/gm build on')).toEqual({ handled: true, action: 'build_on' });
    expect(parseGmCommand('/gm build off')).toEqual({ handled: true, action: 'build_off' });
    expect(parseGmCommand('/gm off')).toEqual({ handled: true, action: 'build_off' });
    expect(parseGmCommand('/gm exit')).toEqual({ handled: true, action: 'build_off' });
  });

  test('returns help for unknown GM subcommands', () => {
    expect(parseGmCommand('/gm dance')).toEqual({ handled: true, action: 'help' });
    expect(GM_COMMAND_HELP).toContain('/gm menu');
  });

  test('ignores non-GM commands', () => {
    expect(parseGmCommand('/gma')).toEqual({ handled: false });
    expect(parseGmCommand('hello')).toEqual({ handled: false });
  });
});
