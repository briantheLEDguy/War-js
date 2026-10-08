from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts/unreal'))
from t1_render_log import validate_render_log


class RenderLogTest(unittest.TestCase):
    def test_successful_exit_does_not_accept_fallback_materials(self):
        prefix='LogRHI: Using D3D12\nLogPythonScriptCommandlet: Running Python script\n'
        with self.assertRaises(ValueError): validate_render_log(prefix+'LogMaterial: Warning: Failed to compile Material\nSuccess - 0 errors')
        with self.assertRaises(ValueError): validate_render_log(prefix+'Default Material will be used in game')
        validate_render_log(prefix+'LogShaderCompilers: Display: Compiling shaders\n')

    def test_missing_render_backend_fails_closed(self):
        with self.assertRaises(ValueError): validate_render_log('LogRHI: NullRHI\nLogPythonScriptCommandlet: Running Python script')


if __name__ == '__main__': unittest.main()
