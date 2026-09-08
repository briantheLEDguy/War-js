import test from 'node:test';
import assert from 'node:assert/strict';
import { embeddedPngEvidence, rgba8MipBytes } from './texture_evidence.mjs';

function fixture() {
  const bytes = Buffer.alloc(24); Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]).copy(bytes);
  bytes.write('IHDR', 12); bytes.writeUInt32BE(1024, 16); bytes.writeUInt32BE(512, 20);
  return { bytes, doc: { images: [{ bufferView: 0, mimeType: 'image/png' }], bufferViews: [{ byteOffset: 0, byteLength: 24 }] } };
}
test('embedded dimensions and memory come from actual GLB image bytes', () => {
  const { bytes, doc } = fixture(), [image] = embeddedPngEvidence(doc, bytes);
  assert.equal(image.width, 1024); assert.equal(image.height, 512);
  assert.equal(image.rgba8MipBytes, rgba8MipBytes(1024, 512)); assert.equal(image.sha256.length, 64);
  doc.images.push({ ...doc.images[0] }); assert.equal(embeddedPngEvidence(doc, bytes).length, 1);
});
test('invalid resource ranges and external images cannot claim atlas evidence', () => {
  const { bytes, doc } = fixture(); doc.bufferViews[0].byteLength = 25;
  assert.throws(() => embeddedPngEvidence(doc, bytes), /range/);
  doc.bufferViews[0].byteLength = 24; doc.images[0].uri = '../unsigned.png';
  assert.throws(() => embeddedPngEvidence(doc, bytes), /embedded/);
  assert.equal(rgba8MipBytes(4, 2), 44);
});
