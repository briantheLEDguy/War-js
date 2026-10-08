"""Rendered acceptance must reject shader fallbacks, even when the commandlet exits successfully."""
import re


def validate_render_log(text):
    failures = [line for line in text.splitlines() if re.search(r'Failed to compile Material|Default Material will be used|Failed to compile global shader', line, re.IGNORECASE)]
    if failures:
        raise ValueError('Rendered material compilation failed: ' + failures[0].strip())
    if not re.search(r'LogRHI:.*(?:D3D|Vulkan|Metal)', text) or 'LogPythonScriptCommandlet:' not in text:
        raise ValueError('Missing rendered RHI or Python execution evidence')
