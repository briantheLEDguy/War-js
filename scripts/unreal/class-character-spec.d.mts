export type Race = "empire" | "dwarf" | "high_elf" | "chaos" | "greenskin" | "dark_elf";
export interface ClassCharacterRequest {
  profileKey: string;
  classKey: string;
  className: string;
  race: Race;
  bodyFamily: string;
  bodyVariant: "m" | "f";
  expectedHeightM: number;
  propertyValues: Record<string, number> & { muscle: number; weight: number };
  skin: { assetPack: string; assetName: string; tint: string };
  grooming: Record<string, string>;
  fixtureTargets: Array<{ pack: string; relativePath: string; weight: number }>;
  foundation: {
    schemaVersion: number; classKey: string; className: string; race: Race; variant: "m" | "f";
    shoulderHeightRatio: [number, number]; armorClearanceM: { soft: number; plate: number; joint: number };
    hairTint: string;
    motionPolicy: string; nativeAccepted: false;
  };
}
export const RACE_ANATOMY: Readonly<Record<Race, { muscle: [number, number]; weight: [number, number]; shoulders: [number, number] }>>;
export function digest(value: string | Uint8Array): string;
export function classCharacterSpecs(): ClassCharacterRequest[];
export function assertDraftReceipt<T extends {
  requestSha256: string; classKey: string; variant: string; technicalPassed: boolean;
  nativeAccepted: boolean; runtimeEligible: boolean; files: Array<{ path: string; sha256: string }>;
}>(receipt: T, request: ClassCharacterRequest, directory: string, read?: (path: string) => Uint8Array): T;
