import json
import struct
import unittest
from glb_sampling import animation_times, inspection_times


def model(values):
    binary = b'pad!' + b''.join(struct.pack('<ff', t, 99) for t in values)
    doc = {'bufferViews': [{'buffer': 0, 'byteOffset': 4, 'byteStride': 8}],
           'accessors': [{'bufferView': 0, 'componentType': 5126, 'type': 'SCALAR', 'count': len(values)}],
           'animations': [{'name': 'run', 'samplers': [{'input': 0}, {'input': 0}]}]}
    text = json.dumps(doc).encode()
    text += b' ' * (-len(text) % 4)
    chunks = struct.pack('<II', len(text), 0x4E4F534A) + text + struct.pack('<II', len(binary), 0x004E4942) + binary
    return struct.pack('<III', 0x46546C67, 2, 12 + len(chunks)) + chunks


class SamplingTests(unittest.TestCase):
    def test_actual_keys_preserve_subframes_and_deduplicate_samplers(self):
        keys = animation_times(model([0, 1 / 30, 2 / 30]))['run']
        samples = inspection_times(keys)
        self.assertEqual(len(samples), 5)
        self.assertAlmostEqual(samples[1], 1 / 60, places=7)
        self.assertAlmostEqual(1 + samples[2] * 24, 1.8, places=6)

    def test_irregular_times_receive_one_midpoint_each(self):
        for actual, expected in zip(inspection_times([0, .02, .10]), [0, .01, .02, .06, .10], strict=True):
            self.assertAlmostEqual(actual, expected)

    def test_reject_reversed_times(self):
        with self.assertRaises(ValueError):
            animation_times(model([0, .2, .1]))

    def test_reject_truncated_model(self):
        with self.assertRaises(ValueError):
            animation_times(model([0, 1])[:-4])


if __name__ == '__main__':
    unittest.main()
