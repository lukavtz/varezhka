"""Three-second native moving-hold example, not a walk cycle or lip-sync film.

Both characters breathe and blink, nod from a neck pivot and make a small
shoulder-led gesture. Feet are unchanged and checked on every frame.
"""
import argparse
import json
import math
import sys
from pathlib import Path
import bpy

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import blender_flat as F
import draw_rooms as rooms
import draw_people as people
from support import validate_percent, ensure_channelbag


def pivot(name,parent,local_xy,children):
    joint=F._joint(name,parent,*local_xy)
    F.attach(children,joint)
    return joint


def make_controls(actor):
    root=actor['root'];name=root.name
    preset=people.PRESETS['explain']
    moving=[]
    tags=('.neck','.hoodie.','.hood.','.drawstring','.pocket','.waist.fold')
    for child in list(root.children):
        if child is actor['head'] or child in actor['arms'].values() or any(child.name.startswith(name+t) for t in tags):
            moving.append(child)
    upper=pivot(name+'.breathing',root,preset['pelvis'],moving)
    neck=F._joint(name+'.neck-pivot',root,*preset['neck'])
    F.attach(neck,upper)
    F.attach(actor['head'],neck)
    shoulder=F._joint(name+'.gesture-pivot',root,*preset['shoulderR'])
    F.attach(shoulder,upper)
    F.attach(actor['arms']['R'],shoulder)
    eyes=[]
    for side,x,y in (('L',-16,-7),('R',17,-8)):
        children=[o for o in actor['head'].children if any(o.name==name+t+side for t in ('.eye.white.','.iris.','.pupil.','.eye.glint.'))]
        if len(children)!=4:raise RuntimeError('Eye parts missing: '+name+' '+side)
        eyes.append(pivot(name+'.blink.'+side,actor['head'],(x,y),children))
    feet=[o for o in root.children if o.name.startswith(name+'.boot-root.')]
    return dict(upper=upper,neck=neck,shoulder=shoulder,eyes=eyes,feet=feet)


def blink_scale(frame,centres):
    amount=1.0
    for centre in centres:
        distance=abs(frame-centre)
        if distance<3:amount=min(amount,.075+.925*distance/3)
    return amount


def ease_action(frame,start,end):
    if frame<=start or frame>=end:return 0.0
    return math.sin(math.pi*(frame-start)/(end-start))**2


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--percent',type=int,default=100)
    parser.add_argument('--preview-only',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    validate_percent(args.percent)
    out=args.output.expanduser().resolve();out.mkdir(parents=True,exist_ok=True)
    scene=F.setup(1920,1080,fps=30,duration=3,engine='BLENDER_WORKBENCH')
    scene.display.render_aa='16'
    scene.render.image_settings.compression=30
    scene.render.resolution_percentage=args.percent
    rooms.scene_explain_hall()
    actors=[people.person('Speaker','explain',650,915),
        people.person('Listener','explain',1450,915,facing='left',palette={
            'hoodie':'#49757B','hoodie_dark':'#365B61','hoodie_light':'#668E91',
            'cap':'#CBA14E','cap_dark':'#97743B','cap_light':'#D9B36A'})]
    F.text('floorplan heading','ПЛАН ЭТАЖА',1110,312,24,'#4D6268',z=7)
    controls=[make_controls(actor) for actor in actors]
    baseline={foot.name:tuple(F._screen_xy(foot)) for item in controls for foot in item['feet']}
    for frame in range(1,91):
        scene.frame_set(frame)
        for index,c in enumerate(controls):
            phase=(frame-1)/89*math.tau+index*.9
            c['upper'].scale.y=1+.004*math.sin(phase)
            c['upper'].keyframe_insert('scale',frame=frame)
            c['neck'].rotation_euler.z=.022*math.sin(phase*1.3+index)*ease_action(frame,8,84)
            c['neck'].keyframe_insert('rotation_euler',frame=frame)
            c['shoulder'].rotation_euler.z=(.04 if index==0 else -.035)*ease_action(frame,12+index*22,59+index*22)
            c['shoulder'].keyframe_insert('rotation_euler',frame=frame)
            for eye in c['eyes']:
                eye.scale.y=blink_scale(frame,(26+index*13,70+index*8))
                eye.keyframe_insert('scale',frame=frame)
        progress=(frame-1)/89
        soft=progress*progress*(3-2*progress)
        scene.camera.location=(960+35*soft,540,1000)
        scene.camera.keyframe_insert('location',frame=frame)
        scene.camera.data.ortho_scale=1860-120*soft
        scene.camera.data.keyframe_insert('ortho_scale',frame=frame)
    animated=[obj for obj in bpy.data.objects if obj.animation_data]
    owners=animated+[scene.camera.data]
    for owner in owners:
        data=owner.animation_data
        if not data or not data.action:continue
        bag=ensure_channelbag(data.action,data.action_slot)
        for curve in bag.fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
    maximum_foot_error=0.0
    for frame in range(1,91):
        scene.frame_set(frame)
        for c in controls:
            for foot in c['feet']:
                maximum_foot_error=max(maximum_foot_error,math.dist(F._screen_xy(foot),baseline[foot.name]))
    if maximum_foot_error>1e-5:raise RuntimeError('Moving-hold feet drifted.')
    scene.frame_set(1)
    scene['example_kind']='moving hold, blinks, head nods, shoulder gestures; no walking or speech'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'moving-hold.blend'))
    for frame in (1,27,45,78,90):
        scene.frame_set(frame)
        scene.render.filepath=str(out/f'key-{frame:03d}.png')
        bpy.ops.render.render(write_still=True)
    if not args.preview_only:
        (out/'frames').mkdir(exist_ok=True)
        scene.render.filepath=str(out/'frames'/'frame-')
        bpy.ops.render.render(animation=True)
    report={'kind':'moving-hold animation','duration_seconds':3,'fps':30,'frames':90,
        'resolution':[1920,1080],'percentage':args.percent,'preview_only':args.preview_only,
        'characters':2,'maximum_actual_foot_error':maximum_foot_error,
        'animated_objects':[o.name for o in animated],
        'limits':'No walk cycle, lip sync or narration. These must be authored for a production script.'}
    (out/'animation-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'status':'rendered','mode':'animation','output':str(out),'preview_only':args.preview_only},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
