import { useEffect, useState } from 'react';
import { services } from '../../services';
import {
  buildCampaignSnapshot,
  formatCampaignControl,
  type CampaignControl,
  type CampaignSnapshot,
  type CampaignZoneStatus,
} from '../../data/campaign';
import { useGameStore } from '../../state/gameStore';
import { useDraggableWindow } from './useDraggableWindow';

interface CampaignPanelProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CampaignPanel({ open, onOpenChange }: CampaignPanelProps) {
  const {
    panelRef,
    dragHandleProps,
    dragStyle,
    dragClassName,
  } = useDraggableWindow<HTMLElement>();
  const zoneId = useGameStore((s) => s.character?.zoneId ?? null);
  const [snapshot, setSnapshot] = useState<CampaignSnapshot>(() => buildCampaignSnapshot(zoneId));

  useEffect(() => {
    try {
      return services.campaign.subscribeSnapshot(setSnapshot, zoneId);
    } catch (err) {
      console.warn('[CampaignPanel] campaign service unavailable:', err);
      setSnapshot(buildCampaignSnapshot(zoneId));
      return undefined;
    }
  }, [zoneId]);

  const activeZone = snapshot.activeZone ?? snapshot.zones.find((zone) => zone.id === 'dawnline_expanse') ?? snapshot.zones[0];
  const cityReady = snapshot.aegis.citySiegeReady || snapshot.riftbound.citySiegeReady;
  const bossCount = snapshot.zones.filter((zone) => zone.nodeRole === 'boss_lair').length;

  return (
    <>
      {open && (
        <section
          ref={panelRef}
          className={`warfront-panel panel${dragClassName}`}
          style={dragStyle}
          aria-labelledby="campaign-title"
        >
          <header className="warfront-header draggable-window-handle" {...dragHandleProps}>
            <div>
              <h2 id="campaign-title">Campaign</h2>
              <span>Aegis Accord vs Riftbound Host</span>
            </div>
            <button type="button" onClick={() => onOpenChange(false)}>Close</button>
          </header>

          <div className="warfront-score">
            <RealmScore label="Aegis" value={snapshot.aegis.controlledZones} realm="aegis" />
            <RealmScore label="Contested" value={snapshot.contestedZones} realm="contested" />
            <RealmScore label="Riftbound" value={snapshot.riftbound.controlledZones} realm="riftbound" />
          </div>

          <div className="warfront-active">
            <span>{activeZone.tier} Focus</span>
            <strong>{activeZone.name}</strong>
            <small>{activeZone.objectives.map((objective) => objective.label).join(' / ')}</small>
          </div>

          <div className="campaign-map-scroll" aria-label="Aegis and Riftbound campaign map">
            <CampaignMapBoard snapshot={snapshot} />
          </div>

          <div className="warfront-active">
            <span>Active Objectives</span>
            <strong>{activeZone.name}</strong>
            <small>
              {activeZone.objectives.map((objective) =>
                `${objective.label}: ${formatCampaignControl(objective.control)}`,
              ).join(' / ')}
            </small>
            <small>
              Influence: Aegis {activeZone.influence.aegis}/{activeZone.influence.keepSiegeRequired} / Riftbound {activeZone.influence.riftbound}/{activeZone.influence.keepSiegeRequired}
            </small>
          </div>

          <footer className={`warfront-siege${cityReady ? ' ready' : ''}`}>
            <strong>{cityReady ? 'City siege ready' : 'City sieges locked'}</strong>
            <span>
              {cityReady
                ? readyCityCopy(snapshot)
                : `${snapshot.siegeRule} Side boss lairs: ${bossCount}.`}
            </span>
          </footer>
        </section>
      )}
    </>
  );
}

type CampaignMapNode = {
  id: string;
  slot: string;
  label: string;
  stage?: string;
  variant?: 'city' | 'fortress' | 'inner' | 'front';
  kind?: 'zone' | 'boss';
  align?: 'left' | 'right';
};

const CAMPAIGN_MAP_NODES: CampaignMapNode[] = [
  { id: 'cindermaw_pit', slot: 'slot-cindermaw-pit', label: 'T1 Boss', kind: 'boss', align: 'right' },
  { id: 'cinderfen_outskirts', slot: 'slot-cinderfen-outskirts', label: 'Cinderfen Outskirts' },
  { id: 'riftspire_capital', slot: 'slot-riftspire-capital', label: 'Riftspire Citadel', stage: 'City siege', variant: 'city' },
  { id: 'ashen_steppe', slot: 'slot-ashen-steppe', label: 'Ashen Steppe' },
  { id: 'ashfang_pit', slot: 'slot-ashfang-pit', label: 'T1 Boss', kind: 'boss', align: 'left' },

  { id: 'rotwreath_nest', slot: 'slot-rotwreath-nest', label: 'T2 Boss', kind: 'boss', align: 'right' },
  { id: 'bleakroot_causeway', slot: 'slot-bleakroot-causeway', label: 'Bleakroot Causeway' },
  { id: 'rift_gate_fortress', slot: 'slot-rift-gate-fortress', label: 'Voidgate Fortress', stage: 'Final fortress', variant: 'fortress' },
  { id: 'gorepine_pass', slot: 'slot-gorepine-pass', label: 'Gorepine Pass' },
  { id: 'gorepine_warrens', slot: 'slot-gorepine-warrens', label: 'T2 Boss', kind: 'boss', align: 'left' },

  { id: 'nightglass_hollow', slot: 'slot-nightglass-hollow', label: 'T3 Boss', kind: 'boss', align: 'right' },
  { id: 'vilemere_heights', slot: 'slot-vilemere-heights', label: 'Vilemere Heights' },
  { id: 'rift_crownworks', slot: 'slot-rift-crownworks', label: 'Rift Crownworks', stage: 'Inner T4', variant: 'inner' },
  { id: 'obsidian_scar', slot: 'slot-obsidian-scar', label: 'Obsidian Scar' },
  { id: 'obsidian_maw', slot: 'slot-obsidian-maw', label: 'T3 Boss', kind: 'boss', align: 'left' },

  { id: 'shatterline_expanse', slot: 'slot-shatterline-expanse', label: 'Shatterline Expanse', stage: 'Rift front', variant: 'front' },
  { id: 'dawnline_expanse', slot: 'slot-dawnline-expanse', label: 'Dawnline Expanse', stage: 'Aegis front', variant: 'front' },

  { id: 'stormbarrow_lair', slot: 'slot-stormbarrow-lair', label: 'T3 Boss', kind: 'boss', align: 'right' },
  { id: 'ironwood_redoubt', slot: 'slot-ironwood-redoubt', label: 'Ironwood Redoubt' },
  { id: 'aegis_crownworks', slot: 'slot-aegis-crownworks', label: 'Aegis Crownworks', stage: 'Inner T4', variant: 'inner' },
  { id: 'highvale_rampart', slot: 'slot-highvale-rampart', label: 'Highvale Rampart' },
  { id: 'highvale_sanctum', slot: 'slot-highvale-sanctum', label: 'T3 Boss', kind: 'boss', align: 'left' },

  { id: 'briarwatch_den', slot: 'slot-briarwatch-den', label: 'T2 Boss', kind: 'boss', align: 'right' },
  { id: 'greybrook_crossing', slot: 'slot-greybrook-crossing', label: 'Greybrook Crossing' },
  { id: 'aegis_gate_fortress', slot: 'slot-aegis-gate-fortress', label: 'Starfall Gate', stage: 'Final fortress', variant: 'fortress' },
  { id: 'glassriver_ford', slot: 'slot-glassriver-ford', label: 'Glassriver Ford' },
  { id: 'glassriver_depths', slot: 'slot-glassriver-depths', label: 'T2 Boss', kind: 'boss', align: 'left' },

  { id: 'wardens_hollow', slot: 'slot-wardens-hollow', label: 'T1 Boss', kind: 'boss', align: 'right' },
  { id: 'sunmeadow_march', slot: 'slot-sunmeadow-march', label: 'Sunmeadow March' },
  { id: 'aegis_capital', slot: 'slot-aegis-capital', label: 'Bastion of Aegis', stage: 'City siege', variant: 'city' },
  { id: 'brightfen_approach', slot: 'slot-brightfen-approach', label: 'Brightfen Approach' },
  { id: 'mireglass_den', slot: 'slot-mireglass-den', label: 'T1 Boss', kind: 'boss', align: 'left' },
];

const CAMPAIGN_MAP_EDGES = [
  'edge-central',
  'edge-rift-west-lane',
  'edge-rift-east-lane',
  'edge-aegis-west-lane',
  'edge-aegis-east-lane',
  'edge-rift-west-to-center',
  'edge-rift-east-to-center',
  'edge-aegis-west-to-center',
  'edge-aegis-east-to-center',
];

const CAMPAIGN_MAP_ARROWS = [
  'arrow-rift-city-fortress up',
  'arrow-rift-fortress-inner up',
  'arrow-rift-inner-front up',
  'arrow-front-clash dual',
  'arrow-aegis-front-inner down',
  'arrow-aegis-inner-fortress down',
  'arrow-aegis-fortress-city down',
  'arrow-rift-west-one down',
  'arrow-rift-west-two down',
  'arrow-rift-east-one down',
  'arrow-rift-east-two down',
  'arrow-aegis-west-one up',
  'arrow-aegis-west-two up',
  'arrow-aegis-east-one up',
  'arrow-aegis-east-two up',
];

const CAMPAIGN_CAPITAL_LINKS = [
  'link-rift-capital-west to-left',
  'link-rift-capital-east to-right',
  'link-aegis-capital-west to-left',
  'link-aegis-capital-east to-right',
];

function CampaignMapBoard({ snapshot }: { snapshot: CampaignSnapshot }) {
  return (
    <div className="campaign-map-board">
      {CAMPAIGN_MAP_EDGES.map((edge) => (
        <span className={`campaign-map-edge ${edge}`} key={edge} aria-hidden="true" />
      ))}
      {CAMPAIGN_MAP_ARROWS.map((arrow) => (
        <span className={`campaign-map-arrow ${arrow}`} key={arrow} aria-hidden="true" />
      ))}
      {CAMPAIGN_CAPITAL_LINKS.map((link) => (
        <span className={`campaign-map-capital-link ${link}`} key={link} aria-hidden="true" />
      ))}
      {CAMPAIGN_MAP_NODES.map((node) => {
        const zone = snapshot.zones.find((entry) => entry.id === node.id);
        if (!zone) return null;
        return <CampaignMapNodeView key={node.id} node={node} zone={zone} />;
      })}
    </div>
  );
}

function CampaignMapNodeView({
  node,
  zone,
}: {
  node: CampaignMapNode;
  zone: CampaignZoneStatus;
}) {
  const control = formatCampaignControl(zone.control);
  const displayControl = node.kind === 'boss' ? shortCampaignControl(zone.control) : control;
  const objectiveSummary = zone.objectives
    .map((objective) => `${objective.label}: ${formatCampaignControl(objective.control)}`)
    .join(' / ');
  const kind = node.kind ?? 'zone';
  const align = node.align ? ` ${node.align}` : '';
  const variant = node.variant ? ` ${node.variant}` : '';

  return (
    <span
      className={`campaign-map-node ${kind}${align}${variant} ${zone.control} ${node.slot}${zone.current ? ' current' : ''}`}
      title={`${zone.name} - ${control}${objectiveSummary ? ` - ${objectiveSummary}` : ''}`}
    >
      <strong>{node.label}</strong>
      {node.stage && <span className="campaign-map-node-stage">{node.stage}</span>}
      <em>{displayControl}</em>
    </span>
  );
}

function shortCampaignControl(control: CampaignControl): string {
  switch (control) {
    case 'aegis':
      return 'Aegis';
    case 'riftbound':
      return 'Rift';
    case 'contested':
    default:
      return 'Open';
  }
}

function RealmScore({
  label,
  value,
  realm,
}: {
  label: string;
  value: number;
  realm: CampaignControl;
}) {
  return (
    <div className={`warfront-score-card ${realm}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function readyCityCopy(snapshot: CampaignSnapshot): string {
  if (snapshot.aegis.citySiegeReady && snapshot.riftbound.citySiegeReady) {
    return 'Both campaign fronts report city pressure; live rules should resolve one attacker.';
  }
  if (snapshot.aegis.citySiegeReady) return `Aegis can pressure ${snapshot.aegis.targetCityName}.`;
  if (snapshot.riftbound.citySiegeReady) return `Riftbound can pressure ${snapshot.riftbound.targetCityName}.`;
  return snapshot.siegeRule;
}
