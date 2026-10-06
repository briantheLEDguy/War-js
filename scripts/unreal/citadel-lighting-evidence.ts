/** Actor names are level-local; the published authored and Dutch suns share a name. */
export const CITADEL_LIGHTING_V2_IDENTITIES = {
  sun: ['authored', 'DirectionalLight_0', 'DirectionalLight', 'Aegis workbench sun',
    'DirectionalLightComponent', 'WarZoneObject_aegis_capital_DirectionalLight_0'],
  soft_sky_fill: ['authored', 'DirectionalLight_1', 'DirectionalLight', 'Crownward soft sky fill',
    'DirectionalLightComponent', 'WarZoneObject_aegis_capital_DirectionalLight_1'],
  ambient_sky: ['authored', 'SkyLight_0', 'SkyLight', 'Aegis workbench sky',
    'SkyLightComponent', 'WarZoneObject_aegis_capital_SkyLight_0'],
  distance_haze: ['authored', 'ExponentialHeightFog_0', 'ExponentialHeightFog', 'Crownward cold distance haze',
    'ExponentialHeightFogComponent', 'WarZoneObject_aegis_capital_ExponentialHeightFog_0'],
  exposure: ['authored', 'PostProcessVolume_0', 'PostProcessVolume', 'Aegis daylight exposure',
    null, 'WarZoneObject_aegis_capital_PostProcessVolume_0'],
  atmosphere: ['authored', 'SkyAtmosphere_0', 'SkyAtmosphere', 'Aegis atmosphere',
    'SkyAtmosphereComponent', 'WarZoneObject_aegis_capital_SkyAtmosphere_0'],
  dutch_street_fill: ['Bastion_Dutch_Geometry', 'DirectionalLight_0', 'DirectionalLight', 'Bastion overcast street fill',
    'DirectionalLightComponent', 'WarWorldObject_dutch_bastion_overcast_fill'],
} as const;
export type CitadelLightingFixtureId = keyof typeof CITADEL_LIGHTING_V2_IDENTITIES;
export interface CitadelLightingValidationOptions { historical?: true }

/** Bounds possible edits; actual receipts must contain exactly the signed chosen fields. */
export const CITADEL_LIGHTING_V2_PROPERTY_ALLOWANCES: Record<CitadelLightingFixtureId, readonly string[]> = {
  sun: ['intensity', 'temperature', 'use_temperature', 'cast_shadows', 'cast_dynamic_shadows',
    'atmosphere_sun_light', 'atmosphere_sun_light_index', 'forward_shading_priority', 'light_source_angle'],
  soft_sky_fill: ['intensity', 'use_temperature', 'cast_shadows', 'cast_dynamic_shadows', 'atmosphere_sun_light', 'light_color'],
  ambient_sky: ['intensity', 'real_time_capture', 'lower_hemisphere_is_black', 'lower_hemisphere_color',
    'light_color', 'indirect_lighting_intensity'],
  distance_haze: ['fog_density', 'fog_height_falloff', 'start_distance', 'fog_max_opacity',
    'enable_volumetric_fog', 'fog_inscattering_luminance'],
  exposure: ['override_auto_exposure_method', 'auto_exposure_method',
    'override_auto_exposure_apply_physical_camera_exposure', 'auto_exposure_apply_physical_camera_exposure',
    'override_auto_exposure_bias', 'auto_exposure_bias', 'override_auto_exposure_min_brightness',
    'auto_exposure_min_brightness', 'override_auto_exposure_max_brightness', 'auto_exposure_max_brightness',
    'override_histogram_log_min', 'histogram_log_min', 'override_histogram_log_max', 'histogram_log_max',
    'override_auto_exposure_speed_up', 'auto_exposure_speed_up', 'override_auto_exposure_speed_down',
    'auto_exposure_speed_down', 'override_color_saturation', 'color_saturation', 'override_bloom_intensity',
    'bloom_intensity', 'override_lens_flare_intensity', 'lens_flare_intensity',
    'override_dynamic_global_illumination_method', 'dynamic_global_illumination_method',
    'override_reflection_method', 'reflection_method'],
  atmosphere: ['transform_mode', 'bottom_radius', 'ground_albedo', 'atmosphere_height', 'multi_scattering_factor',
    'trace_sample_count_scale', 'rayleigh_scattering_scale', 'rayleigh_scattering', 'rayleigh_exponential_distribution',
    'mie_scattering_scale', 'mie_scattering', 'mie_absorption_scale', 'mie_absorption', 'mie_anisotropy',
    'mie_exponential_distribution', 'other_absorption_scale', 'other_absorption', 'sky_luminance_factor',
    'sky_and_aerial_perspective_luminance_factor', 'aerial_pespective_view_distance_scale', 'height_fog_contribution',
    'transmittance_min_light_elevation_angle', 'aerial_perspective_start_depth'],
  dutch_street_fill: ['intensity', 'use_temperature', 'cast_shadows', 'cast_dynamic_shadows', 'atmosphere_sun_light', 'light_color'],
};

const FIXTURES = {
  DirectionalLight_0: ['DirectionalLight', 'Aegis workbench sun', 'DirectionalLightComponent'],
  DirectionalLight_1: ['DirectionalLight', 'Crownward soft sky fill', 'DirectionalLightComponent'],
  SkyLight_0: ['SkyLight', 'Aegis workbench sky', 'SkyLightComponent'],
  ExponentialHeightFog_0: ['ExponentialHeightFog', 'Crownward cold distance haze', 'ExponentialHeightFogComponent'],
  PostProcessVolume_0: ['PostProcessVolume', 'Aegis daylight exposure', null],
} as const;
const PROPERTY_KEYS = [
  ['intensity', 'temperature', 'use_temperature', 'cast_shadows', 'atmosphere_sun_light', 'forward_shading_priority', 'light_source_angle'],
  ['intensity', 'use_temperature', 'cast_shadows', 'atmosphere_sun_light', 'light_color'],
  ['intensity', 'real_time_capture', 'lower_hemisphere_is_black', 'lower_hemisphere_color', 'light_color', 'indirect_lighting_intensity'],
  ['fog_density', 'fog_height_falloff', 'start_distance', 'fog_max_opacity', 'enable_volumetric_fog', 'fog_inscattering_luminance'],
  ['override_auto_exposure_method', 'auto_exposure_method', 'override_auto_exposure_apply_physical_camera_exposure',
    'auto_exposure_apply_physical_camera_exposure', 'override_auto_exposure_bias', 'auto_exposure_bias',
    'override_auto_exposure_min_brightness', 'auto_exposure_min_brightness', 'override_auto_exposure_max_brightness',
    'auto_exposure_max_brightness', 'override_auto_exposure_speed_up', 'auto_exposure_speed_up',
    'override_auto_exposure_speed_down', 'auto_exposure_speed_down', 'override_color_saturation', 'color_saturation',
    'override_bloom_intensity', 'bloom_intensity', 'override_lens_flare_intensity', 'lens_flare_intensity'],
];
PROPERTY_KEYS[4].push('override_histogram_log_min', 'histogram_log_min', 'override_histogram_log_max', 'histogram_log_max');
const canonical = (v: any): any => Array.isArray(v) ? v.map(canonical) : v && typeof v === 'object'
  ? Object.fromEntries(Object.keys(v).sort().map(k => [k, canonical(v[k])])) : v;
const same = (a: any, b: any) => JSON.stringify(canonical(a)) === JSON.stringify(canonical(b));
const sha = (v: any) => typeof v === 'string' && /^[a-f0-9]{64}$/.test(v);
function readback(wanted: any, actual: any): boolean {
  if (typeof wanted === 'boolean') return actual === wanted;
  if (typeof wanted === 'number') return Number.isFinite(wanted) && typeof actual === 'number'
    && Number.isFinite(actual) && Math.abs(actual - wanted) <= Math.max(.00001, Math.abs(wanted) * .000001);
  if (!wanted || typeof wanted !== 'object') return false;
  if (wanted.kind === 'enum') {
    const enums: Record<string, string[]> = { AutoExposureMethod: ['AEM_HISTOGRAM'],
      DynamicGlobalIlluminationMethod: ['SCREEN_SPACE'], ReflectionMethod: ['SCREEN_SPACE'],
      SkyAtmosphereTransformMode: ['PLANET_TOP_AT_ABSOLUTE_WORLD_ORIGIN', 'PLANET_TOP_AT_COMPONENT_TRANSFORM', 'PLANET_CENTER_AT_COMPONENT_TRANSFORM'] };
    return same(Object.keys(wanted).sort(), ['kind', 'type', 'value'])
      && enums[wanted.type]?.includes(wanted.value) === true && actual === wanted.type + '.' + wanted.value;
  }
  return ['color', 'linear_color', 'vector4'].includes(wanted.kind) && Array.isArray(wanted.value)
    && same(Object.keys(wanted).sort(), ['kind', 'value'])
    && wanted.value.length === 4 && Array.isArray(actual) && actual.length === 4
    && (wanted.kind !== 'color' || wanted.value.every((n: any) => Number.isInteger(n) && n >= 0 && n <= 255))
    && wanted.value.every((v: any, i: number) => readback(v, actual[i]));
}

/** Five signed copies may change lighting; every other preserved actor remains immutable. */
function requireNativeCitadelLightingV1(receipt: any, blueprint: any): void {
  const specs = blueprint.lightingTreatment?.fixtures, changes = receipt.sharedLightingChanges;
  const preservation = receipt.outsideMaskPreservation, prefix = `/Game/WorldRebuild/AegisCitadel_${receipt.revision}/Layers/`;
  if (blueprint.lightingTreatment?.schemaVersion !== 1 || blueprint.lightingTreatment.exposureUnits !== 'native_luminance'
    || blueprint.lightingTreatment.expectedExtendedEV100 !== false || receipt.exposureUsesExtendedEV100 !== false
    || receipt.exposureUnits !== 'native_luminance'
    || !Array.isArray(specs) || specs.length !== 5 || !Array.isArray(changes) || changes.length !== 5
    || !Array.isArray(preservation) || !preservation.length || new Set(specs.map(s => s.actor)).size !== 5
    || new Set(changes.map(c => c.actor)).size !== 5)
    throw new Error('Exactly five signed native lighting changes and preservation witnesses are required.');
  Object.entries(FIXTURES).forEach(([actor, identity], index) => {
    const spec = specs.find(s => s.actor === actor), change = changes.find(c => c.actor === actor);
    if (!spec || !change || spec.klass !== identity[0] || spec.label !== identity[1] || spec.component !== identity[2]
      || !sha(spec.sourceStateHash) || !sha(receipt.sourceHashes?.[spec.package]) || receipt.packageHashes?.[spec.package]
      || change.sourcePackage !== spec.package || !new RegExp('^' + prefix + 'RetainedCity_[0-9]+$').test(String(change.package))
      || !receipt.sceneryLevels?.includes(change.package)
      || !sha(receipt.packageHashes?.[change.package]) || change.sourceStateHash !== spec.sourceStateHash
      || !sha(change.actualStateHash) || !same(change.requestedProperties, spec.properties)
      || !same(Object.keys(spec.properties ?? {}).sort(), PROPERTY_KEYS[index].slice().sort()))
      throw new Error('Native lighting identity, source state, ownership or property allowance changed: ' + actor);
    if (index === 4 && (spec.properties.auto_exposure_min_brightness !== 64 || spec.properties.auto_exposure_max_brightness !== 4096
      || spec.properties.histogram_log_min !== 1 || spec.properties.histogram_log_max !== 14
      || spec.properties.override_histogram_log_min !== true || spec.properties.override_histogram_log_max !== true))
      throw new Error('Native luminance exposure and logarithmic histogram must match the signed existing project mode.');
    const expected = [...Object.keys(spec.properties), ...(spec.rotationDegrees ? ['rotationDegrees'] : [])].sort();
    if (!same(Object.keys(change.actualPropertyReadback ?? {}).sort(), expected)
      || Object.entries(spec.properties).some(([key, value]) => !readback(value, change.actualPropertyReadback[key]))
      || spec.rotationDegrees && (index > 1 || !Array.isArray(spec.rotationDegrees) || spec.rotationDegrees.length !== 3
        || !Array.isArray(change.actualPropertyReadback.rotationDegrees)
        || change.actualPropertyReadback.rotationDegrees.length !== 3
        || spec.rotationDegrees.some((n: any, i: number) => typeof n !== 'number' || !Number.isFinite(n)
          || typeof change.actualPropertyReadback.rotationDegrees[i] !== 'number'
          || !Number.isFinite(change.actualPropertyReadback.rotationDegrees[i])
          || Math.abs(n - change.actualPropertyReadback.rotationDegrees[i]) > .001)))
      throw new Error('Actual lighting readback differs from the signed properties: ' + actor);
    if (!preservation.some(p => p.source === spec.package && p.candidate === change.package))
      throw new Error('A lighting change lacks its exact copied-layer preservation boundary.');
  });
  if (new Set(preservation.map(p => p.candidate)).size !== preservation.length) throw new Error('Duplicate preserved layer.');
  for (const row of preservation) {
    const expected = changes.filter(c => c.package === row.candidate && c.sourcePackage === row.source).map(c => c.actor).sort();
    if (row.matchesExpected !== true || !sha(receipt.sourceHashes?.[row.source]) || !sha(receipt.packageHashes?.[row.candidate])
      || !receipt.sceneryLevels?.includes(row.candidate)
      || !sha(row.preservedStateSha256) || !Number.isSafeInteger(row.preservedActorCount) || row.preservedActorCount < 0
      || !Array.isArray(row.explicitLightingChanges) || !same(row.explicitLightingChanges.slice().sort(), expected))
      throw new Error('An unrelated preserved actor was allowed through the lighting exception.');
  }
}

const SOURCE_PREFIX = '/Game/WorldRebuild/DutchBastion_d105951f4aab/Layers/';
const CLOUD_MATERIAL = '/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst';
const CLOUD_IDENTITY = { id: 'citadel_cloud', actor: 'VolumetricCloud_0', klass: 'VolumetricCloud',
  label: 'Bastion mountain cloud canopy', component: 'VolumetricCloudComponent',
  requiredTag: 'WarWorldObject_aegis_citadel_cloud' } as const;
export const CITADEL_CLOUD_SCALARS = { Layout_CloudGlobalScale: 8, Cloud_GlobalCoverage: .25,
  Cloud_GlobalDensity: .008, StormClouds: .65 } as const;
export const CITADEL_CLOUD_VECTORS = { Cloud_AlbedoColor: [.65, .70, .78, .5],
  Storm_LightningColor: [0, 0, 0, 0], Layout_CloudTypeMask: [0, 0, 1, 0] } as const;
const object = (value: any) => value && typeof value === 'object' && !Array.isArray(value);
const point = (value: any) => Array.isArray(value) && value.length === 3
  && value.every((n: any) => typeof n === 'number' && Number.isFinite(n));

function requireMeasuredPolicy(id: CitadelLightingFixtureId, properties: any): void {
  const required: Partial<Record<CitadelLightingFixtureId, any>> = {
    sun: { intensity: 12500, temperature: 5600 }, ambient_sky: { intensity: .35 },
    soft_sky_fill: { intensity: 800, cast_shadows: true, cast_dynamic_shadows: true },
    distance_haze: { fog_density: .006, start_distance: 7000, fog_max_opacity: .4 },
    dutch_street_fill: { intensity: 0, cast_shadows: true, cast_dynamic_shadows: true,
      light_color: { kind: 'color', value: [173, 192, 218, 255] } },
    atmosphere: { rayleigh_scattering_scale: .0331, rayleigh_exponential_distribution: 8 },
    exposure: { auto_exposure_min_brightness: 64, auto_exposure_max_brightness: 4096,
      override_histogram_log_min: true, histogram_log_min: 1, override_histogram_log_max: true, histogram_log_max: 14,
      override_dynamic_global_illumination_method: true,
      dynamic_global_illumination_method: { kind: 'enum', type: 'DynamicGlobalIlluminationMethod', value: 'SCREEN_SPACE' },
      override_reflection_method: true, reflection_method: { kind: 'enum', type: 'ReflectionMethod', value: 'SCREEN_SPACE' } },
  };
  if (!object(properties) || !Object.keys(properties).length
    || Object.keys(properties).some(key => !CITADEL_LIGHTING_V2_PROPERTY_ALLOWANCES[id].includes(key))
    || Object.entries(required[id] ?? {}).some(([key, value]) => !same(properties[key], value))
    || id === 'atmosphere' && !same(Object.keys(properties).sort(), ['rayleigh_exponential_distribution', 'rayleigh_scattering_scale']))
    throw new Error('A copied fixture exceeds its exact signed native lighting policy: ' + id);
}

/** Fresh candidates require seven exact copies and one separately owned, source-bound cloud. */
export function requireNativeCitadelLighting(receipt: any, blueprint: any,
  options: CitadelLightingValidationOptions = {}): void {
  if (blueprint.lightingTreatment?.schemaVersion === 1 && options.historical === true)
    return requireNativeCitadelLightingV1(receipt, blueprint);
  const treatment = blueprint.lightingTreatment, specs = treatment?.fixtures, changes = receipt.sharedLightingChanges;
  const preserved = receipt.outsideMaskPreservation, prefix = `/Game/WorldRebuild/AegisCitadel_${receipt.revision}/Layers/`;
  if (treatment?.schemaVersion !== 2 || !/^[a-f0-9]{12}$/.test(receipt.revision)
    || treatment.exposureUnits !== 'native_luminance' || treatment.expectedExtendedEV100 !== false
    || treatment.existingAtmospherePreserved !== false
    || receipt.exposureUsesExtendedEV100 !== false || receipt.exposureUnits !== 'native_luminance'
    || !Array.isArray(specs) || specs.length !== 7 || !Array.isArray(changes) || changes.length !== 7
    || specs.some(s => !object(s)) || changes.some(c => !object(c))
    || new Set(specs.map(s => s.id)).size !== 7 || new Set(changes.map(c => c.id)).size !== 7
    || !Array.isArray(preserved) || !preserved.length)
    throw new Error('Fresh lighting requires version2, seven source-bound fixture IDs and exact preservation witnesses.');
  for (const [id, identity] of Object.entries(CITADEL_LIGHTING_V2_IDENTITIES)) {
    const spec = specs.find(s => s.id === id), change = changes.find(c => c.id === id);
    const sourcePackage = SOURCE_PREFIX + identity[0];
    if (!spec || !change || spec.package !== sourcePackage || spec.actor !== identity[1] || spec.klass !== identity[2]
      || spec.label !== identity[3] || spec.component !== identity[4] || spec.requiredTag !== identity[5]
      || !sha(spec.sourceStateHash) || !sha(spec.sourcePackageSha256)
      || receipt.sourceHashes?.[sourcePackage] !== spec.sourcePackageSha256 || receipt.packageHashes?.[sourcePackage] !== undefined
      || change.sourcePackage !== sourcePackage || change.sourceStateHash !== spec.sourceStateHash
      || change.sourcePackageSha256 !== spec.sourcePackageSha256 || !sha(change.actualStateHash)
      || !new RegExp('^' + prefix + 'RetainedCity_[0-9]+$').test(String(change.package))
      || !receipt.sceneryLevels?.includes(change.package) || !sha(receipt.packageHashes?.[change.package])
      || ['actor', 'klass', 'label', 'component', 'requiredTag'].some(key => change[key] !== spec[key])
      || !Array.isArray(change.actualTags) || new Set(change.actualTags).size !== change.actualTags.length
      || !same(change.actualTags.slice().sort(), [spec.requiredTag,
        ...(['sun', 'ambient_sky', 'exposure', 'atmosphere'].includes(id) ? ['WarCapitalWorkbench']
          : id === 'dutch_street_fill' ? ['WarDutchBastion'] : [])].sort())
      || !same(change.requestedProperties, spec.properties))
      throw new Error('Copied native lighting source/identity/ownership changed: ' + id);
    requireMeasuredPolicy(id as CitadelLightingFixtureId, spec.properties);
    if (id === 'sun' && !same(spec.rotationDegrees, [-20, 30, 0]))
      throw new Error('The signed native sun rotation differs from the measured private scene policy.');
    const expectedKeys = [...Object.keys(spec.properties), ...(spec.rotationDegrees !== undefined ? ['rotationDegrees'] : [])].sort();
    if (!object(change.actualPropertyReadback) || !same(Object.keys(change.actualPropertyReadback).sort(), expectedKeys)
      || Object.entries(spec.properties).some(([key, value]) => !readback(value, change.actualPropertyReadback[key]))
      || spec.rotationDegrees !== undefined && (!['sun', 'soft_sky_fill', 'dutch_street_fill'].includes(id)
        || !point(spec.rotationDegrees) || !point(change.actualPropertyReadback.rotationDegrees)
        || spec.rotationDegrees.some((n: number, i: number) => Math.abs(n - change.actualPropertyReadback.rotationDegrees[i]) > .001))
      || !preserved.some(p => p.source === sourcePackage && p.candidate === change.package))
      throw new Error('Actual lighting readback differs from exact signed fields: ' + id);
  }
  if (new Set(preserved.map(p => p.candidate)).size !== preserved.length) throw new Error('Duplicate preserved scenery layer.');
  for (const row of preserved) {
    const expected = changes.filter(c => c.package === row.candidate && c.sourcePackage === row.source).map(c => c.id).sort();
    if (row.matchesExpected !== true || !sha(receipt.sourceHashes?.[row.source]) || !sha(receipt.packageHashes?.[row.candidate])
      || !receipt.sceneryLevels?.includes(row.candidate) || !sha(row.preservedStateSha256)
      || !Number.isSafeInteger(row.preservedActorCount) || row.preservedActorCount < 0
      || !Array.isArray(row.explicitLightingChanges) || !same(row.explicitLightingChanges.slice().sort(), expected))
      throw new Error('An unrelated actor was allowed through copied lighting preservation exceptions.');
  }
  const cloud = treatment.cloudFixture, placed = receipt.nativeCloudPlacement;
  if (!object(cloud) || !object(placed)
    || Object.entries(CLOUD_IDENTITY).some(([key, value]) => cloud[key] !== value || placed[key] !== value)
    || !point(cloud.pointCm) || !same(cloud.pointCm, [0, 0, 0]) || !point(placed.actualPointCm)
    || !same(placed.pointCm, cloud.pointCm) || placed.actualPointCm.some((n: number, i: number) => Math.abs(n - cloud.pointCm[i]) > .001)
    || placed.package !== prefix + 'GothicCitadel' || !receipt.sceneryLevels?.includes(placed.package)
    || !sha(receipt.packageHashes?.[placed.package]) || !sha(placed.stateHash)
    || !Array.isArray(placed.actualTags) || !placed.actualTags.includes(CLOUD_IDENTITY.requiredTag)
    || placed.actualTags.some((tag: any) => typeof tag !== 'string' || !tag || tag.length > 128)
    || new Set(placed.actualTags).size !== placed.actualTags.length
    || !object(cloud.material) || cloud.material.package !== CLOUD_MATERIAL
    || cloud.material.path !== CLOUD_MATERIAL + '.m_SimpleVolumetricCloud_Inst' || !sha(cloud.material.sha256)
    || receipt.sourceHashes?.[CLOUD_MATERIAL] !== cloud.material.sha256 || receipt.packageHashes?.[CLOUD_MATERIAL] !== undefined
    || !same(placed.material, cloud.material)
    || !same(cloud.properties, { layer_bottom_altitude: .5, layer_height: 1.2,
      view_sample_count_scale: 2, shadow_view_sample_count_scale: 2 })
    || !same(placed.requestedProperties, cloud.properties)
    || !object(placed.actualPropertyReadback) || !same(Object.keys(placed.actualPropertyReadback).sort(), Object.keys(cloud.properties).sort())
    || Object.entries(cloud.properties).some(([key, value]) => !readback(value, placed.actualPropertyReadback[key])))
    throw new Error('The owned native cloud differs from its signed material, actor or exact layer readbacks.');
  const instance = cloud.materialInstance, actual = placed.materialInstance;
  const ownedPackage = `/Game/WorldRebuild/AegisCitadel_${receipt.revision}/Materials/MI_Cloud`;
  if (!object(instance) || !same(Object.keys(instance).sort(), ['name', 'parent', 'scalarParameters', 'vectorParameters'])
    || instance.name !== 'MI_Cloud' || instance.parent !== cloud.material.path
    || !same(instance.scalarParameters, CITADEL_CLOUD_SCALARS) || !same(instance.vectorParameters, CITADEL_CLOUD_VECTORS)
    || !object(actual) || !same(Object.keys(actual).sort(), ['package', 'path', 'sha256', 'parent',
      'requestedScalarParameters', 'actualScalarReadback', 'requestedVectorParameters', 'actualVectorReadback',
      'registeredScalarParameters', 'registeredVectorParameters'].sort())
    || actual.package !== ownedPackage || actual.path !== ownedPackage + '.MI_Cloud'
    || actual.parent !== instance.parent || !sha(actual.sha256)
    || receipt.packageHashes?.[ownedPackage] !== actual.sha256 || receipt.sourceHashes?.[ownedPackage] !== undefined
    || placed.actualMaterial !== actual.path)
    throw new Error('The cloud material instance must be privately owned and bound to the unchanged Engine parent.');
  for (const [kind, wanted] of [['Scalar', instance.scalarParameters], ['Vector', instance.vectorParameters]] as const) {
    const requested = actual[`requested${kind}Parameters`], observed = actual[`actual${kind}Readback`];
    const registered = actual[`registered${kind}Parameters`];
    if (!same(requested, wanted) || !object(observed) || !same(Object.keys(observed).sort(), Object.keys(wanted).sort())
      || !Array.isArray(registered) || !registered.length || registered.length > 256
      || registered.some((name: any) => typeof name !== 'string' || !name || name.length > 128)
      || new Set(registered).size !== registered.length
      || Object.entries(wanted).some(([name, value]) => !registered.includes(name)
        || (kind === 'Scalar' ? !readback(value, observed[name])
          : !readback({ kind: 'linear_color', value }, observed[name]))))
      throw new Error('Cloud material parameters lack exact registered names and typed native readbacks: ' + kind);
  }
}
