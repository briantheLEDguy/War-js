import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';

export type PrimitiveClassification = 'visible_model_or_fallback' | 'technical_geometry' | 'test_fixture'
  | 'authoring_geometry_review' | 'unclassified_geometry_review';
export interface PrimitiveFinding { path: string; line: number; expression: string; classification: PrimitiveClassification; action: string }

/** A constructor match is an audit lead, never permission to delete a collider, effect, or authored mesh. */
export function classifyPrimitive(relative: string, expression: string): PrimitiveClassification {
  if (/^(tests\/|.*\/test-assets\/|.*\/pipeline-tools\/generate_pipeline_test_assets\.py)/.test(relative)) return 'test_fixture';
  if (/AssetLoader\.primitives|buildCharacterMesh|buildEquipmentVisualFallback|buildWorldLifeActor|cityFallback|civicFallback|citadelDecorationFallback/.test(expression)) return 'visible_model_or_fallback';
  if (/^(authoring\/|scripts\/)/.test(relative)) return 'authoring_geometry_review';
  if (/CharacterMeshes|EquipmentMeshes|CityCivicFallback|CityCitadelFallback|WorldLifeAssets/.test(relative)) return 'visible_model_or_fallback';
  if (/abilities\/.*Vfx|enemyAttackTelegraph|\/Terrain\.ts$|\/PathKit\.ts$|WorldEditor.*|Collision|collider|selection|telegraph/i.test(relative)) return 'technical_geometry';
  return 'unclassified_geometry_review';
}

export function auditPrimitives(root: string): { findings: PrimitiveFinding[]; modelFiles: Array<{ path: string; classification: string }>; policy: string } {
  const files = execFileSync('git', ['ls-files', '-z'], { cwd: root, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024 })
    .split('\0').filter(Boolean).sort();
  const findings: PrimitiveFinding[] = [];
  const modelFiles: Array<{ path: string; classification: string }> = [];
  const pattern = /(?:new\s+(?:THREE\.)?(?:Box|Sphere|Cylinder|Capsule|Cone|Icosahedron|Torus|Dodecahedron|Plane|Circle|Ring)Geometry\b|bpy\.ops\.mesh\.primitive_\w+|AssetLoader\.primitives(?:\.\w+)?|buildCharacterMesh\(|buildEquipmentVisualFallback\(|buildWorldLifeActor\(|(?:city|civic|citadelDecoration)Fallback\()/;
  for (const file of files) {
    if (/\.(?:glb|gltf|blend|fbx|obj)$/i.test(file) && /(?:primitive|proxy|test-assets|test_body|test_character)/i.test(file)) {
      modelFiles.push({ path: file, classification: /test/.test(file) ? 'test_fixture_model' : 'name_requires_review' });
    }
    if (!/\.(?:tsx?|mjs|js|py)$/.test(file) || !/^(src|shared|scripts|authoring|tests)\//.test(file)
      || file.startsWith('scripts/unreal/') || !existsSync(path.join(root, file))) continue;
    const lines = readFileSync(path.join(root, file), 'utf8').split(/\r?\n/);
    for (const [index, line] of lines.entries()) {
      if (!pattern.test(line) || /^\s*(?:\/\/|\*|#)/.test(line)) continue;
      const expression = line.trim();
      const classification = classifyPrimitive(file, expression);
      findings.push({ path: file, line: index + 1, expression: expression.slice(0, 240), classification,
        action: classification === 'technical_geometry' ? 'retain_behavior_review_presentation'
          : classification === 'visible_model_or_fallback' ? 'replace_with_validated_authored_asset_before_removal'
          : classification === 'test_fixture' ? 'replace_primitive_model_fixtures_preserve_test_coverage'
          : 'inspect_geometry_and_provenance_no_automatic_deletion' });
    }
  }
  return { findings, modelFiles, policy: 'No deletion is performed. Source-constructor/name matching cannot establish final model quality. Collision, terrain, VFX and editor geometry retain their behavior; visible placeholder models require authored replacements.' };
}
