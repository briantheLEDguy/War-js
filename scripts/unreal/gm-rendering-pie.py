"""Start the opt-in GM rendering fixture in a disposable Editor process. Never save assets."""
import re
from pathlib import Path

import unreal

# The launcher supplies the selected map, isolated preferences and proof flags.
# A post-tick callback owns only this fixture's Play/exit lifecycle.
run = re.search(r'-WarProofDraftId=([a-f0-9]{32})', unreal.SystemLibrary.get_command_line())
if not run:
    raise RuntimeError('An isolated GM rendering run ID is required')
receipt = Path(unreal.Paths.project_saved_dir()) / 'GmRenderingProof' / run.group(1) / 'report.json'
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
state = {'ending': False}


def tick(_delta):
    if (receipt.parent / 'stop.txt').exists() and not editor.get_game_world():
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.SystemLibrary.quit_editor()
        return
    if not receipt.exists():
        return
    if not state['ending']:
        levels.editor_request_end_play()
        state['ending'] = True
    elif not editor.get_game_world():
        unreal.unregister_slate_post_tick_callback(handle)
        unreal.SystemLibrary.quit_editor()


handle = unreal.register_slate_post_tick_callback(tick)
levels.editor_request_begin_play()
