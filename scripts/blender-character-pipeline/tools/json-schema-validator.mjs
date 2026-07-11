/** Small dependency-free validator for the schema features used by this pipeline. */

function valueType(value) {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  if (Number.isInteger(value)) return "integer";
  if (typeof value === "number") return "number";
  return typeof value;
}

function typeMatches(value, type) {
  if (type === "number") return typeof value === "number" && Number.isFinite(value);
  if (type === "integer") return Number.isInteger(value);
  if (type === "object") return value !== null && typeof value === "object" && !Array.isArray(value);
  if (type === "array") return Array.isArray(value);
  if (type === "null") return value === null;
  return typeof value === type;
}

export function validateJsonSchema(schema, value, location = "$") {
  const errors = [];
  const allowedTypes = schema.type === undefined ? null : Array.isArray(schema.type) ? schema.type : [schema.type];
  if (allowedTypes && !allowedTypes.some((type) => typeMatches(value, type))) {
    errors.push(`${location} must be ${allowedTypes.join(" or ")}; received ${valueType(value)}`);
    return errors;
  }
  if (schema.const !== undefined && value !== schema.const) errors.push(`${location} must equal ${JSON.stringify(schema.const)}`);
  if (schema.enum && !schema.enum.some((entry) => entry === value)) errors.push(`${location} must be one of ${schema.enum.join(", ")}`);
  if (typeof value === "string" && schema.pattern && !(new RegExp(schema.pattern)).test(value)) {
    errors.push(`${location} does not match ${schema.pattern}`);
  }
  if (typeof value === "number") {
    if (schema.minimum !== undefined && value < schema.minimum) errors.push(`${location} must be >= ${schema.minimum}`);
    if (schema.maximum !== undefined && value > schema.maximum) errors.push(`${location} must be <= ${schema.maximum}`);
  }
  if (Array.isArray(value)) {
    if (schema.minItems !== undefined && value.length < schema.minItems) errors.push(`${location} requires at least ${schema.minItems} item(s)`);
    if (schema.maxItems !== undefined && value.length > schema.maxItems) errors.push(`${location} allows at most ${schema.maxItems} item(s)`);
    if (schema.items) value.forEach((entry, index) => errors.push(...validateJsonSchema(schema.items, entry, `${location}[${index}]`)));
  }
  if (value !== null && typeof value === "object" && !Array.isArray(value)) {
    for (const required of schema.required ?? []) {
      if (value[required] === undefined) errors.push(`${location}.${required} is required`);
    }
    const known = schema.properties ?? {};
    for (const [key, entry] of Object.entries(value)) {
      if (known[key]) errors.push(...validateJsonSchema(known[key], entry, `${location}.${key}`));
      else if (schema.additionalProperties === false) errors.push(`${location}.${key} is not allowed`);
      else if (schema.additionalProperties && typeof schema.additionalProperties === "object") {
        errors.push(...validateJsonSchema(schema.additionalProperties, entry, `${location}.${key}`));
      }
    }
  }
  return errors;
}

export function assertJsonSchema(schema, value, label = "record") {
  const errors = validateJsonSchema(schema, value);
  if (errors.length) {
    const error = new Error(`${label} failed schema validation: ${errors.join("; ")}`);
    error.code = "SCHEMA_VALIDATION_FAILED";
    error.details = { errors };
    throw error;
  }
  return value;
}
