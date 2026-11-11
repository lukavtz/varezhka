"""Portable asset discovery. This module uses only Python's standard library."""
import os
from pathlib import Path

KIT_ROOT=Path(__file__).resolve().parents[1]


def resolve_font(bold=False):
    custom=os.environ.get('FONT_PATH')
    if custom:
        candidate=Path(custom).expanduser()
        if candidate.is_file():
            return candidate
        raise FileNotFoundError('FONT_PATH must name an existing TTF or OTF font.')
    names=('NotoSans-Bold.ttf','DejaVuSans-Bold.ttf') if bold else ('NotoSans-Regular.ttf','DejaVuSans.ttf')
    candidates=[KIT_ROOT/'assets'/'fonts'/name for name in names]
    win=Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'
    candidates.extend([win/('arialbd.ttf' if bold else 'arial.ttf'),
        Path('/usr/share/fonts/truetype/dejavu')/names[-1],
        Path('/System/Library/Fonts/Supplemental')/('Arial Bold.ttf' if bold else 'Arial.ttf')])
    return next((p for p in candidates if p.is_file()),None)


def ensure_channelbag(action,slot):
    """Blender 5.x slot-aware bags vs 4.4/4.5 legacy channelbags."""
    import bpy_extras.anim_utils as A
    if hasattr(A,'action_ensure_channelbag_for_slot'):
        return A.action_ensure_channelbag_for_slot(action,slot)
    return A.action_ensure_channelbag(action)

def validate_percent(value):
    if not 1<=value<=100:
        raise ValueError('Render percentage must be between 1 and 100.')
    return value
