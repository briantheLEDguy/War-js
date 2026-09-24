"""Final fresh-Editor checks for installed characters, equipped motion and deletion."""
from pathlib import Path
import runpy

for name in ('verify-world-character-imports.py','measure-equipped-motion.py','verify-native-animation-removal.py'):
    runpy.run_path(str(Path(__file__).with_name(name)))
