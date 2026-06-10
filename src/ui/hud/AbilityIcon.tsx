import type { ReactNode } from 'react';
import type {
  AbilityDefinition,
  AbilityIconAccent,
  AbilityIconFrame,
  AbilityIconSymbol,
} from '../../game/abilities/types';

interface Props {
  ability: AbilityDefinition;
}

export function AbilityIcon({ ability }: Props) {
  const { icon } = ability.visual;
  return (
    <svg
      className={`ability-icon-svg icon-${icon.symbol} frame-${icon.frame} accent-${icon.accent}`}
      viewBox="0 0 64 64"
      aria-hidden="true"
      focusable="false"
    >
      {renderFrame(icon.frame)}
      {renderSeedMarks(icon.seed)}
      <g className="ability-icon-symbol">
        {renderSymbol(icon.symbol)}
      </g>
      {renderAccent(icon.accent)}
    </svg>
  );
}

function renderFrame(frame: AbilityIconFrame): ReactNode {
  switch (frame) {
    case 'diamond':
      return <path className="ability-icon-frame" d="M32 4 60 32 32 60 4 32Z" />;
    case 'shield':
      return <path className="ability-icon-frame" d="M32 5 55 14v15c0 15-9 25-23 31C18 54 9 44 9 29V14Z" />;
    case 'rune':
      return <path className="ability-icon-frame" d="M14 7h36l7 7v36l-7 7H14l-7-7V14Z" />;
    case 'burst':
      return <path className="ability-icon-frame" d="m32 3 7 13 14-5-5 14 13 7-13 7 5 14-14-5-7 13-7-13-14 5 5-14-13-7 13-7-5-14 14 5Z" />;
    default:
      return <circle className="ability-icon-frame" cx="32" cy="32" r="27" />;
  }
}

function renderSeedMarks(seed: number): ReactNode {
  const count = 2 + (seed % 3);
  return Array.from({ length: count }, (_, index) => {
    const angle = ((seed >> (index * 3)) % 360) * (Math.PI / 180);
    const x = 32 + Math.cos(angle) * 21;
    const y = 32 + Math.sin(angle) * 21;
    return (
      <path
        key={index}
        className="ability-icon-mark"
        d={`M${x - 2.5} ${y}h5M${x} ${y - 2.5}v5`}
      />
    );
  });
}

function renderAccent(accent: AbilityIconAccent): ReactNode {
  switch (accent) {
    case 'chevron':
      return <path className="ability-icon-accent" d="m24 48 8-7 8 7" />;
    case 'cross':
      return <path className="ability-icon-accent" d="M32 45v10M27 50h10" />;
    case 'dot':
      return <circle className="ability-icon-accent-fill" cx="48" cy="46" r="4" />;
    case 'spark':
      return <path className="ability-icon-accent" d="m48 39 2 7 7 2-7 2-2 7-2-7-7-2 7-2Z" />;
    case 'tear':
      return <path className="ability-icon-accent-fill" d="M48 39c5 6 7 10 7 13a7 7 0 0 1-14 0c0-3 2-7 7-13Z" />;
    default:
      return null;
  }
}

function renderSymbol(symbol: AbilityIconSymbol): ReactNode {
  switch (symbol) {
    case 'arrow':
      return <path d="M15 46 46 15l3 13 10-10-13-3 10-10-3-3-10 10-3-13-31 31Z" />;
    case 'axe':
      return <path d="M19 53 45 27l-8-8 5-5c7 1 12 6 14 13-6-1-10 1-14 5l-5 5 8 8-8 8-8-8-8 8Z" />;
    case 'banner':
      return <path d="M22 53V10h24l-5 9 5 9H25v25Z" />;
    case 'blade':
      return <path d="M18 54 30 23 47 6l5 5-17 17-12 31Zm9-16 8 8" />;
    case 'bolt':
      return <path d="M36 4 12 36h17l-3 24 26-36H35Z" />;
    case 'bomb':
      return <path d="M18 36a16 16 0 1 0 32 0 16 16 0 0 0-32 0Zm24-17 6-9 7 7-9 6" />;
    case 'chain':
      return <path d="M21 38 11 28a10 10 0 0 1 14-14l7 7-6 6-7-7a2 2 0 0 0-3 3l10 10Zm22-12 10 10a10 10 0 0 1-14 14l-7-7 6-6 7 7a2 2 0 0 0 3-3L38 31Z" />;
    case 'chalice':
      return <path d="M20 10h24v13c0 8-5 13-12 13S20 31 20 23Zm12 26v12m-10 6h20" />;
    case 'claw':
      return <path d="M18 53c3-17 7-32 15-45-1 17-4 31-9 45Zm16 0c1-16 5-29 14-39 0 15-3 27-8 39Zm-26 0c4-13 5-24 5-36 7 11 8 23 1 36Z" />;
    case 'cross':
      return <path d="M27 8h10v17h17v10H37v21H27V35H10V25h17Z" />;
    case 'crown':
      return <path d="m10 47 5-27 12 12 5-20 5 20 12-12 5 27Zm4 7h36" />;
    case 'dagger':
      return <path d="m19 55 10-23 20-20 3 3-20 20Zm5-28 13 13m-17 4 7 7" />;
    case 'eye':
      return <path d="M5 32c7-12 16-18 27-18s20 6 27 18c-7 12-16 18-27 18S12 44 5 32Zm18 0a9 9 0 1 0 18 0 9 9 0 0 0-18 0Z" />;
    case 'fang':
      return <path d="M21 8c7 12 9 27 4 47-8-11-11-23-4-47Zm22 0c-7 12-9 27-4 47 8-11 11-23 4-47Z" />;
    case 'flame':
      return <path d="M32 58c-11-5-17-13-17-23 0-8 5-14 11-20 0 7 2 10 6 13 2-9 7-15 15-21-1 11 4 16 4 26 0 11-8 20-19 25Z" />;
    case 'hammer':
      return <path d="m13 49 24-24-7-7 8-8 17 17-8 8-7-7-24 24Z" />;
    case 'leaf':
      return <path d="M12 50c5-27 21-39 40-38 1 19-11 35-38 40 11-6 20-14 27-25-10 7-18 15-29 23Z" />;
    case 'paw':
      return <path d="M20 38c7 0 17 7 17 14 0 5-4 7-9 5-5-2-8-2-13 0s-9 0-9-5c0-7 7-14 14-14Zm-8-10a5 7 0 1 0 0-14 5 7 0 0 0 0 14Zm16-5a5 8 0 1 0 0-16 5 8 0 0 0 0 16Zm16 5a5 7 0 1 0 0-14 5 7 0 0 0 0 14Z" />;
    case 'rune':
      return <path d="M18 8h28L34 28h16L21 56l10-23H15Z" />;
    case 'shield':
      return <path d="M32 8 51 15v14c0 12-7 20-19 26-12-6-19-14-19-26V15Zm0 7v32" />;
    case 'skull':
      return <path d="M16 28c0-12 8-20 16-20s16 8 16 20c0 8-4 13-10 16v10H26V44c-6-3-10-8-10-16Zm7 1h8v7h-8Zm10 0h8v7h-8Z" />;
    case 'spear':
      return <path d="M17 55 42 30l-8-8L52 7l5 5-15 18-8-8-25 25Z" />;
    case 'star':
      return <path d="m32 6 7 18 19 1-15 12 5 19-16-11-16 11 5-19L6 25l19-1Z" />;
    case 'turret':
      return <path d="M18 45h28v9H18Zm5-17h18l6 17H17Zm4-16h10l6 9H21Z" />;
    case 'vortex':
      return <path d="M48 21c-8-11-29-7-31 8-2 17 21 23 29 8-10 7-23 2-22-8 1-11 16-15 24-8Zm-29 22c8 11 29 7 31-8 2-17-21-23-29-8 10-7 23-2 22 8-1 11-16 15-24 8Z" />;
    default:
      return <path d="M32 8 50 50H14Z" />;
  }
}
