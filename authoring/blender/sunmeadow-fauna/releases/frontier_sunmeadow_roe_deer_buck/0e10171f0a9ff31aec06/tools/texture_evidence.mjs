import crypto from 'node:crypto';

export function rgba8MipBytes(width, height) {
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1) throw new Error('Invalid texture dimensions');
  let total = 0;
  for (;;) {
    total += width * height * 4;
    if (width === 1 && height === 1) return total;
    width = Math.max(1, Math.floor(width / 2)); height = Math.max(1, Math.floor(height / 2));
  }
}

export function embeddedPngEvidence(doc, binary) {
  const visited = new Set();
  return doc.images.flatMap(image => {
    if (image.uri || image.mimeType !== 'image/png' || !Number.isInteger(image.bufferView)) throw new Error('Expected embedded PNG resource');
    if (visited.has(image.bufferView)) return [];
    visited.add(image.bufferView);
    const view = doc.bufferViews[image.bufferView], offset = view?.byteOffset ?? 0;
    if (!view || (view.buffer ?? 0) !== 0 || offset < 0 || view.byteLength < 24 || offset + view.byteLength > binary.length) throw new Error('Invalid embedded image range');
    const bytes = binary.subarray(offset, offset + view.byteLength);
    if (!bytes.subarray(0, 8).equals(Buffer.from([137, 80, 78, 71, 13, 10, 26, 10])) || bytes.toString('ascii', 12, 16) !== 'IHDR') throw new Error('Invalid PNG header');
    const width = bytes.readUInt32BE(16), height = bytes.readUInt32BE(20);
    return [{ width, height, bytes: bytes.length, sha256: crypto.createHash('sha256').update(bytes).digest('hex'), rgba8MipBytes: rgba8MipBytes(width, height) }];
  });
}
