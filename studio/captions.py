"""Native word/phrase captions for the starter's front-orthographic 2D scenes.

Input is [{"text": "word", "start": 0.0, "end": 0.4}, ...] or the path to
an ElevenLabs .alignment.json containing a ``words`` list. Coordinates and
outline width are drawing units, matching the 1920x1080 example canvas.
No audio request, font rasterization or external caption package is used.
"""
import json
import math
from pathlib import Path

import bpy
from bpy_extras.anim_utils import action_ensure_channelbag_for_slot
import blender_flat as F
from support import resolve_font


def load_words(value):
    if isinstance(value,(str,Path)):
        value=json.loads(Path(value).expanduser().read_text(encoding='utf8'))
    if isinstance(value,dict):value=value.get('words')
    if not isinstance(value,list):
        raise ValueError('Captions need a words list or alignment JSON containing words.')
    result=[]
    for item in value:
        text=str(item['text']).strip()
        if not text:continue
        start,end=float(item['start']),float(item['end'])
        if not (math.isfinite(start) and math.isfinite(end) and 0<=start<end):
            raise ValueError('Each word needs finite 0 <= start < end times in seconds.')
        if result and start<result[-1]['end']-1e-6:
            raise ValueError('Word timings overlap. Resolve alignment before adding captions.')
        result.append({'text':text,'start':start,'end':end})
    return result


def _phrases(words,max_words,gap_seconds):
    result=[];chunk=[]
    for word in words:
        if chunk and (len(chunk)>=max_words or word['start']-chunk[-1]['end']>gap_seconds or chunk[-1]['text'].endswith(('.','!','?'))):
            result.append({'text':' '.join(w['text'] for w in chunk),'start':chunk[0]['start'],'end':chunk[-1]['end']})
            chunk=[]
        chunk.append(word)
    if chunk:result.append({'text':' '.join(w['text'] for w in chunk),'start':chunk[0]['start'],'end':chunk[-1]['end']})
    return result


def _visibility(obj,start,end):
    for frame,hidden in ((start-1,True),(start,False),(end,False),(end+1,True)):
        obj.hide_render=hidden
        obj.hide_viewport=hidden
        obj.keyframe_insert('hide_render',frame=frame)
        obj.keyframe_insert('hide_viewport',frame=frame)
    data=obj.animation_data
    bag=action_ensure_channelbag_for_slot(data.action,data.action_slot)
    for curve in bag.fcurves:
        for key in curve.keyframe_points:key.interpolation='CONSTANT'


def _material(color):
    # Datablock lookup survives opening another .blend; a Python pointer cache
    # would retain invalid material references after a scene-file reload.
    name='Caption material '+str(color)
    material=bpy.data.materials.get(name)
    if material:return material
    material=bpy.data.materials.new(name)
    value=F._linear(F.rgba(color))
    material.diffuse_color=value
    material.use_nodes=True
    nodes=material.node_tree.nodes;nodes.clear()
    emission=nodes.new('ShaderNodeEmission')
    emission.inputs['Color'].default_value=value
    emission.inputs['Strength'].default_value=1
    output=nodes.new('ShaderNodeOutputMaterial')
    material.node_tree.links.new(emission.outputs[0],output.inputs['Surface'])
    return material


def _copy_layer(scene,source,name,color,depth,offset=0,shift=None):
    obj=source.copy();obj.data=source.data.copy();obj.name=name
    scene.collection.objects.link(obj)
    obj.data.materials.clear();obj.data.materials.append(_material(color))
    obj.data.offset=offset
    obj.location.z=depth
    if shift:
        obj.location.x+=shift[0];obj.location.y-=shift[1]
    return obj


def add_captions(scene,words,font_path=None,x=None,y=None,size=72,*,
                 mode='word',max_words=4,phrase_gap=.28,max_width=None,
                 outline_width=2,foreground='#FFFFFF',outline_color='#000000',
                 shadow_offset=None,shadow_color='#222222',depth=80,
                 start_frame=None,name_prefix='Caption',pin_to_camera=True):
    """Create editable white font objects and expanded black font silhouettes.

    ``mode='word'`` shows one timed word. ``mode='phrase'`` groups up to
    ``max_words`` words, breaking at pauses and sentence endings. The helper
    fits long cues uniformly and may wrap a phrase into two lines.
    ``x,y`` are the centre anchor and top edge in scene drawing coordinates.
    Defaults are centre / 62% height; choose placement from the shot's layout.
    ``shadow_offset`` optionally adds an offset copy, not a blurred shadow.
    By default captions follow the orthographic camera and keep their screen
    size during pan/zoom. Set ``pin_to_camera=False`` for world-space text.
    Returns cue records with frame ranges and their native Blender objects.
    """
    if mode not in ('word','phrase'):raise ValueError('mode must be word or phrase')
    if max_words<1 or size<=0 or outline_width<0:raise ValueError('Invalid caption size/group/outline.')
    if pin_to_camera and (scene.camera is None or scene.camera.data.type!='ORTHO'):
        raise ValueError('Camera-pinned captions require the starter orthographic camera.')
    rows=load_words(words)
    cues=rows if mode=='word' else _phrases(rows,max_words,phrase_gap)
    font_path=Path(font_path).expanduser() if font_path else resolve_font(bold=True)
    if not font_path or not font_path.is_file():raise FileNotFoundError('Provide font_path or include the bundled Noto Sans font.')
    font=bpy.data.fonts.load(str(font_path),check_existing=True)
    if not font.packed_file:font.pack()
    width,height=scene.render.resolution_x,scene.render.resolution_y
    x=width/2 if x is None else x
    y=height*.62 if y is None else y
    max_width=width*.84 if max_width is None else max_width
    if max_width<=0:raise ValueError('max_width must be positive')
    fps=scene.render.fps/scene.render.fps_base
    base=scene.frame_start if start_frame is None else int(start_frame)
    original_frame=scene.frame_current
    result=[]
    previous_end=None
    for index,cue in enumerate(cues):
        first=base+math.ceil(cue['start']*fps-1e-9)
        last=max(first,base+math.ceil(cue['end']*fps-1e-9)-1)
        if previous_end is not None and first<=previous_end:
            raise ValueError('Words are denser than the frame rate. Use phrase mode or revise timings.')
        previous_end=last
        label=f'{name_prefix}.{index:04d}'
        data=bpy.data.curves.new(label+'.font','FONT')
        data.body=cue['text'];data.font=font;data.size=size
        data.align_x='CENTER';data.align_y='TOP_BASELINE';data.space_line=1.12
        data.materials.append(_material(foreground))
        front=bpy.data.objects.new(label+'.white',data)
        scene.collection.objects.link(front)
        front.location=(x,height-y-size*.78,depth)
        scene.view_layers[0].update()
        if mode=='phrase' and front.dimensions.x>max_width and len(cue['text'].split())>1:
            tokens=cue['text'].split();best=None
            for split in range(1,len(tokens)):
                candidate=' '.join(tokens[:split])+'\n'+' '.join(tokens[split:])
                data.body=candidate;scene.view_layers[0].update()
                if best is None or front.dimensions.x<best[0]:best=(front.dimensions.x,candidate)
            data.body=best[1];scene.view_layers[0].update()
        if front.dimensions.x>max_width:
            data.size*=max_width/front.dimensions.x
            front.location.y=height-y-data.size*.78
            scene.view_layers[0].update()
        layers=[]
        if shadow_offset:
            layers.append(_copy_layer(scene,front,label+'.shadow',shadow_color,depth-.2,outline_width,shadow_offset))
        if outline_width:
            layers.append(_copy_layer(scene,front,label+'.outline',outline_color,depth-.1,outline_width))
        layers.append(front)
        for obj in layers:_visibility(obj,first,last)
        result.append({'text':cue['text'],'start_frame':first,'end_frame':last,'objects':layers})
    if pin_to_camera and result:
        camera=scene.camera
        anchor=bpy.data.objects.new(name_prefix+'.camera-anchor',None)
        scene.collection.objects.link(anchor)
        anchor.parent=camera
        distance=camera.data.clip_start+max(1,(camera.data.clip_end-camera.data.clip_start)*.05)
        anchor.location=(0,0,-distance)
        divisor=max(width,height)
        for axis in (0,1):
            curve=anchor.driver_add('scale',axis)
            variable=curve.driver.variables.new();variable.name='view_size'
            variable.type='SINGLE_PROP'
            variable.targets[0].id_type='CAMERA'
            variable.targets[0].id=camera.data
            variable.targets[0].data_path='ortho_scale'
            curve.driver.expression=f'view_size / {divisor}'
        for cue in result:
            cue['camera_anchor']=anchor
            for obj in cue['objects']:
                location=obj.location.copy()
                obj.parent=anchor
                obj.location=(location.x-width/2,location.y-height/2,location.z-depth)
    scene.frame_set(original_frame)
    scene.view_layers[0].update()
    return result
