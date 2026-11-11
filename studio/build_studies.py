"""Render five editable native-geometry pose studies using the latest mitten style."""
import argparse
import json
import sys
from pathlib import Path
import bpy

P=Path(__file__).resolve().parent
sys.path.insert(0,str(P))
import blender_flat as F
import draw_rooms as rooms
import draw_people as people
from support import validate_percent

SPECS=[
    (1,'01-walking-corridor',rooms.scene_hall,'walk',1040,915),
    (2,'02-seated-workspace',rooms.scene_office,'seated',960,940),
    (3,'03-kneeling-workshop',rooms.scene_workshop,'crouch',1000,930),
    (4,'04-carrying-parcel',rooms.scene_storage,'carry',1050,915),
    (5,'05-explaining-floorplan',rooms.scene_explain_hall,'explain',650,915),
]


def serial(value):
    if isinstance(value,bpy.types.Object):return value.name
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items() if k!='objects'}
    if isinstance(value,(tuple,list)):return [serial(v) for v in value]
    if value is None or isinstance(value,(str,int,float,bool)):return value
    return str(value)


def draw_scene(number):
    _,slug,draw_room,pose,x,floor=next(row for row in SPECS if row[0]==number)
    scene=F.setup(1920,1080,duration=1,engine='BLENDER_WORKBENCH')
    scene.display.render_aa='16'
    scene.render.image_settings.compression=40
    layout=draw_room()
    actors=[people.person('Hero',pose,x,floor)]
    if pose=='carry':
        box=actors[0]['contacts']['box']
        rooms.cargo_box(box['x'],box['y'],box['w'],box['h'],z=25)
    if number==5:
        second=people.person('Colleague','carry',1450,915,facing='left',prop_kind='board',
            palette={'hoodie':'#49757B','hoodie_dark':'#365B61','hoodie_light':'#668E91',
                     'cap':'#CBA14E','cap_dark':'#97743B','cap_light':'#D9B36A'})
        actors.append(second)
        folder=second['contacts']['box']
        fx,fy,fw,fh=(folder[k] for k in ('x','y','w','h'))
        F.rect('folio back',fx-5,fy-6,fw+10,fh+8,'#4B696D',F.INK,3,25,radius=5)
        F.rect('folio paper',fx+8,fy+7,fw-16,fh-10,'#EEE5CF','#8A9A8A',1.5,25.2)
        F.line('folio folded edge',[(fx+25,fy+35),(fx+fw-25,fy+35)],'#8D9C8C',2,25.3)
        F.rect('folio diagram',fx+27,fy+57,fw-60,fh-84,'#DBE2D2','#728A82',2,25.4)
        F.line('folio room',[(fx+fw*.52,fy+57),(fx+fw*.52,fy+fh-27)],'#728A82',2,25.45)
        F.text('floorplan heading','ПЛАН ЭТАЖА',1110,312,24,'#4D6268',z=7)
    return scene,slug,layout,actors


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--percent',type=int,default=100)
    parser.add_argument('--only',type=int,nargs='*',choices=range(1,6))
    options=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    validate_percent(options.percent)
    out=options.output.expanduser().resolve()
    (out/'renders').mkdir(parents=True,exist_ok=True)
    (out/'scenes').mkdir(parents=True,exist_ok=True)
    report=[]
    for number,*_ in SPECS:
        if options.only and number not in options.only:continue
        scene,slug,layout,actors=draw_scene(number)
        metadata={'number':number,'slug':slug,'resolution':[1920,1080],
                  'render_percentage':options.percent,'room':serial(layout),'actors':serial(actors),
                  'purpose':'Static pose drawing; a still is not proof of a walk cycle.'}
        (out/'scenes'/f'{slug}.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf8')
        scene['pose_study']=slug
        scene.render.resolution_percentage=options.percent
        scene.render.filepath=str(out/'renders'/f'{slug}.png')
        scene.frame_set(1)
        bpy.ops.wm.save_as_mainfile(filepath=str(out/'scenes'/f'{slug}.blend'))
        bpy.ops.render.render(write_still=True)
        report.append({'slug':slug,'png':str(out/'renders'/f'{slug}.png')})
    print(json.dumps({'status':'rendered','mode':'stills','output':str(out),'items':report},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
