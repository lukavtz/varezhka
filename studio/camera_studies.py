"""Native Blender camera framing and a nine-second, 30 fps camera study.

Loads editable Blender art. Camera movement is rendered from geometry;
no post-render crop or image-plane animation is used.
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
from bpy_extras.anim_utils import action_ensure_channelbag_for_slot

ROOT = Path(__file__).resolve().parent
ASPECT = 16 / 9
parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--percent', type=int, default=100)
parser.add_argument('--mode', choices=('stills', 'keys', 'video'), default='stills')
parser.add_argument('--only', type=int, nargs='*')
args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
OUT = args.output.expanduser().resolve()
if not 1 <= args.percent <= 100:
    raise ValueError('Render percentage must be between 1 and 100.')
OUT.mkdir(parents=True,exist_ok=True)

# Focus bounds are in the illustration's screen coordinates, before camera.
STILLS = [
    ('01-walking-corridor', (1025, 550, 1700), 'full figure', (925, 225, 1215, 935)),
    ('02-seated-workspace', (1310, 636.25, 1160), 'seated medium', (790, 355, 1790, 950)),
    ('03-kneeling-workshop', (1250, 647.5, 1200), 'kneeling medium', (805, 390, 1305, 940)),
    ('04-carrying-parcel', (1050, 415, 800), 'box and face', (910, 225, 1220, 630)),
    ('05-explaining-floorplan', (1025, 545, 1450), 'two shot', (495, 225, 1595, 930)),
]
SHOTS = [
    ('05-explaining-floorplan', (960, 540, 1920), (1025, 545, 1450),
        'Two-shot: establish the room, then move attention to the speakers.', (495, 225, 1595, 930)),
    ('03-kneeling-workshop', (1190, 795, 800), (1190, 790, 700),
        'Hand insert: show cuff, closed grip, handle and case together.', (1030, 665, 1305, 935)),
    ('04-carrying-parcel', (1050, 465, 1000), (1050, 450, 850),
        'Medium close-up: retain complete cap, face, both wrists and the parcel.', (910, 225, 1220, 640)),
]


def bounds(spec):
    x, y, width = spec
    height = width / ASPECT
    return (x-width/2, y-height/2, x+width/2, y+height/2)


def margins(spec, focus):
    left, top, right, bottom = bounds(spec)
    return [focus[0]-left, focus[1]-top, right-focus[2], bottom-focus[3]]


def place(scene, spec):
    x, y, width = spec
    scene.camera.location = (x, 1080-y, 1000)
    scene.camera.data.ortho_scale = width


def load(slug):
    bpy.ops.wm.open_mainfile(filepath=str(args.source.expanduser().resolve()/(slug+'.blend')))
    scene = bpy.context.scene
    scene.render.resolution_x, scene.render.resolution_y = 1920, 1080
    scene.render.resolution_percentage = args.percent
    scene.render.fps, scene.render.fps_base = 30, 1
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.compression = 30
    scene.display.render_aa = '16'
    return scene


def animate(scene, start, end):
    scene.frame_start, scene.frame_end = 1, 90
    for frame, spec in ((1,start), (16,start), (75,end), (90,end)):
        scene.frame_set(frame)
        place(scene, spec)
        scene.camera.keyframe_insert('location', frame=frame)
        scene.camera.data.keyframe_insert('ortho_scale', frame=frame)
    for owner in (scene.camera, scene.camera.data):
        data=owner.animation_data
        bag=action_ensure_channelbag_for_slot(data.action, data.action_slot)
        for curve in bag.fcurves:
            for key in curve.keyframe_points:
                key.interpolation='BEZIER'
                key.handle_left_type=key.handle_right_type='AUTO_CLAMPED'


if args.mode == 'stills':
    report=[]
    for number, (slug,spec,kind,focus) in enumerate(STILLS, 1):
        if args.only and number not in args.only:
            continue
        scene=load(slug)
        place(scene,spec)
        safe=margins(spec,focus)
        if min(safe)<8:
            raise ValueError((slug,'unsafe camera framing',safe))
        scene.render.filepath=str(OUT/(slug+'.png'))
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/(slug+'.blend')))
        bpy.ops.render.render(write_still=True)
        report.append(dict(slug=slug,kind=kind,camera=spec,focus=focus,margins=safe))
    (OUT/'still-framing.json').write_text(json.dumps(report,indent=2),encoding='utf8')
else:
    report=[]
    for number,(slug,start,end,intent,focus) in enumerate(SHOTS,1):
        if args.only and number not in args.only:
            continue
        scene=load(slug)
        animate(scene,start,end)
        samples=[]
        for frame in range(1,91):
            scene.frame_set(frame)
            camera=scene.camera
            spec=(camera.location.x,1080-camera.location.y,camera.data.ortho_scale)
            safe=margins(spec,focus)
            if min(safe)<8:
                raise ValueError((slug,frame,'focus outside safe view',safe))
            samples.append(dict(frame=frame,camera=spec,margins=safe))
        scene.frame_set(1)
        bpy.ops.wm.save_as_mainfile(filepath=str(OUT/f'camera-shot-{number:02d}.blend'))
        if args.mode=='keys':
            for frame in (1,45,90):
                scene.frame_set(frame)
                scene.render.filepath=str(OUT/f'shot-{number:02d}-key-{frame:03d}.png')
                bpy.ops.render.render(write_still=True)
        else:
            frame_dir=OUT/f'shot-{number:02d}-frames'
            frame_dir.mkdir(exist_ok=True)
            scene.render.filepath=str(frame_dir/'frame-')
            bpy.ops.render.render(animation=True)
        report.append(dict(shot=number,source=slug,intent=intent,fps=30,frames=90,samples=samples))
    report_file=OUT/('camera-'+args.mode+'-qa.json')
    if args.only and report_file.exists():
        previous={row['shot']:row for row in json.loads(report_file.read_text(encoding='utf8'))}
        previous.update({row['shot']:row for row in report})
        report=[previous[key] for key in sorted(previous)]
    report_file.write_text(json.dumps(report,indent=2),encoding='utf8')
print('CAMERA_STUDIES_COMPLETE',args.mode,flush=True)
