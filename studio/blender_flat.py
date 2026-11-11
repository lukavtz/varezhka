"""Native flat Blender primitives used by the portable cartoon starter.

Coordinates use a top-left origin, +Y downward, in scene drawing units.
Filled meshes, curves and fonts stay editable; no raster image planes.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
import bpy
from support import resolve_font
from mathutils import Matrix, Vector

W, H, FPS = 1080, 1920, 30
INK = '#2B2923'
_order = 0
_materials = {}
_camera_base = None


def setup(w=1080, h=1920, fps=30, duration=180, *, samples=4,
          engine='BLENDER_EEVEE', clear=True):
    """Reset a scene and return it. Camera exactly fits the supplied canvas."""
    global W, H, FPS, _order, _materials, _camera_base
    W, H, FPS = int(w), int(h), int(fps)
    if clear:
        bpy.ops.wm.read_factory_settings(use_empty=True)
    _order, _materials = 0, {}
    s = bpy.context.scene
    s.render.engine = engine
    if hasattr(s, 'eevee'):
        s.eevee.taa_render_samples = samples
    s.render.resolution_x, s.render.resolution_y = W, H
    s.render.resolution_percentage = 100
    s.render.fps, s.render.fps_base = FPS, 1
    s.frame_start, s.frame_end = 1, max(1, round(duration * FPS))
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGB'
    s.render.image_settings.compression = 10
    s.render.film_transparent = False
    s.view_settings.view_transform = 'Standard'
    s.view_settings.look = 'None'
    s.view_settings.exposure, s.view_settings.gamma = 0, 1
    s.world = bpy.data.worlds.new('Flat world')
    s.world.color = (.05, .05, .05)
    cd = bpy.data.cameras.new('Front orthographic')
    camera = bpy.data.objects.new('Front orthographic', cd)
    s.collection.objects.link(camera)
    camera.location = (W / 2, H / 2, 1000)
    cd.type, cd.ortho_scale = 'ORTHO', max(W, H)
    # All native 2D drawing layers lie around Z=0..55, viewed from Z=1000.
    # A tight 200-unit depth range avoids depth fighting between adjacent
    # flat fills (notably the neck behind the face) and keeps hairlines crisp.
    cd.clip_start, cd.clip_end = 900, 1100
    s.camera = camera
    _camera_base = (camera.location.copy(), cd.ortho_scale)
    if engine == 'BLENDER_WORKBENCH':
        wb = s.display.shading
        wb.light = 'FLAT'
        wb.color_type = 'MATERIAL'
        wb.show_shadows = False
        wb.show_cavity = False
        wb.show_object_outline = False
        wb.show_specular_highlight = False
        wb.background_type = 'WORLD'
        s.display.render_aa = '8'
    return s


def rgba(color):
    if isinstance(color, str):
        h = color.lstrip('#')
        if len(h) in (3, 4):
            h = ''.join(c * 2 for c in h)
        if len(h) not in (6, 8):
            raise ValueError('Expected #RGB, #RRGGBB or #RRGGBBAA')
        q = [int(h[i:i + 2], 16) / 255 for i in range(0, len(h), 2)]
        return tuple(q[:3] + [q[3] if len(q) == 4 else 1.0])
    q = list(color)
    return tuple(q[:3] + [q[3] if len(q) > 3 else 1.0])


def _linear(q):
    return tuple(v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4
                 for v in q[:3]) + (q[3],)


def material(color):
    key = rgba(color)
    if key in _materials:
        return _materials[key]
    c = _linear(key)
    m = bpy.data.materials.new('Flat ' + str(color))
    m.diffuse_color = c
    m.use_nodes = True
    n = m.node_tree.nodes
    n.clear()
    em = n.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = c
    em.inputs['Strength'].default_value = 1
    out = n.new('ShaderNodeOutputMaterial')
    if key[3] < .999:
        tr = n.new('ShaderNodeBsdfTransparent')
        mix = n.new('ShaderNodeMixShader')
        mix.inputs[0].default_value = key[3]
        m.node_tree.links.new(tr.outputs[0], mix.inputs[1])
        m.node_tree.links.new(em.outputs[0], mix.inputs[2])
        m.node_tree.links.new(mix.outputs[0], out.inputs['Surface'])
        try:
            m.surface_render_method = 'BLENDED'
        except (TypeError, AttributeError):
            if hasattr(m, 'surface_render_method'):
                m.surface_render_method = 'DITHERED'
            elif hasattr(m, 'blend_method'):
                m.blend_method = 'BLEND'
    else:
        m.node_tree.links.new(em.outputs[0], out.inputs['Surface'])
    _materials[key] = m
    return m


def _z(z):
    global _order
    _order += 1
    return float(z) + _order * .0004


def _link(obj):
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _clean_points(points):
    """Remove consecutive duplicates and an explicit repeated closing vertex."""
    result=[]
    for point in points:
        p=(float(point[0]),float(point[1]))
        if not result or math.hypot(p[0]-result[-1][0],p[1]-result[-1][1])>1e-6:
            result.append(p)
    if len(result)>2 and math.hypot(result[-1][0]-result[0][0],result[-1][1]-result[0][1])<=1e-6:
        result.pop()
    return result


def group(name, x=0, y=0, z=0):
    obj = _link(bpy.data.objects.new(name, None))
    obj.location = (x, H - y, z)
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = 15
    return obj


def _world_matrix(obj):
    """Evaluate native transform hierarchy without a costly scene-wide update.

    These flat rigs use no transform constraints, so composing local matrices is
    exact and remains fast even when a film contains forty isolated shot roots.
    """
    local = obj.matrix_basis.copy()
    if obj.parent is None:
        return local
    return _world_matrix(obj.parent) @ obj.matrix_parent_inverse @ local


def attach(obj, parent, keep_world=True):
    """Parent one object or an iterable, preserving its world placement."""
    if not isinstance(obj, bpy.types.Object):
        for child in obj:
            attach(child, parent, keep_world)
        return obj
    mw = _world_matrix(obj)
    parent_world = _world_matrix(parent)
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    if keep_world:
        obj.matrix_basis = parent_world.inverted_safe() @ mw
    return obj


def _set_world_xy(obj, x, y):
    """Set screen placement correctly under arbitrary ordinary TRS parents."""
    mw = _world_matrix(obj)
    mw.translation.x, mw.translation.y = x, H-y
    if obj.parent:
        parent_matrix = _world_matrix(obj.parent) @ obj.matrix_parent_inverse
        obj.matrix_basis = parent_matrix.inverted_safe() @ mw
    else:
        obj.matrix_basis = mw


def _screen_xy(obj):
    translation = _world_matrix(obj).translation
    return translation.x, H-translation.y


def line(name, points, stroke=INK, sw=3, z=0, closed=False, **kwargs):
    """Screen-space polyline. ``width``/``col`` aliases ease older script ports."""
    sw, stroke = kwargs.get('width', sw), kwargs.get('col', stroke)
    points = _clean_points(points)
    if len(points) < 2:
        raise ValueError('A line needs at least two points')
    d = bpy.data.curves.new(name, 'CURVE')
    d.dimensions, d.resolution_u = '3D', 1
    d.bevel_depth, d.bevel_resolution = sw / 2, 2
    p = d.splines.new('POLY')
    p.points.add(len(points) - 1)
    for item, (x, y) in zip(p.points, points):
        item.co = (x, H - y, 0, 1)
    p.use_cyclic_u = closed
    d.materials.append(material(stroke))
    obj = _link(bpy.data.objects.new(name, d))
    obj.location.z = _z(z)
    # Flatten bevel depth only along Z; otherwise outlines pierce later fills.
    obj.scale.z = .0001
    return obj


def poly(name, points, fill, stroke=None, sw=3, z=0):
    points = _clean_points(points)
    if fill is None:
        return line(name, points, stroke or INK, sw, z, True)
    if len(points)<3:
        raise ValueError('A filled polygon needs three distinct vertices')
    layer = _z(z)
    d = bpy.data.meshes.new(name)
    d.from_pydata([(x, H - y, layer) for x, y in points], [],
                  [tuple(range(len(points)))])
    d.materials.append(material(fill))
    obj = _link(bpy.data.objects.new(name, d))
    if stroke and sw > 0:
        outline = line(name + '.outline', points, stroke, sw, 0, True)
        outline.location.z = layer + .0001
        # The fill has identity transform here. Direct parenting avoids a full
        # depsgraph evaluation for every outline in a many-shot film.
        outline.parent = obj
    return obj


def rect(name, x, y, w, h, fill, stroke=None, sw=3, z=0, radius=0):
    if not radius:
        return poly(name, [(x, y), (x+w, y), (x+w, y+h), (x, y+h)],
                    fill, stroke, sw, z)
    r = min(radius, abs(w)/2, abs(h)/2)
    return path(name, [(x+r, y), ('L', x+w-r, y),
                      ('Q', x+w, y, x+w, y+r), ('L', x+w, y+h-r),
                      ('Q', x+w, y+h, x+w-r, y+h), ('L', x+r, y+h),
                      ('Q', x, y+h, x, y+h-r), ('L', x, y+r),
                      ('Q', x, y, x+r, y)], fill, stroke, sw, z)


def ellipse(name, cx, cy, rx, ry, fill, stroke=None, sw=3, z=0):
    count = max(32, min(96, math.ceil(max(abs(rx), abs(ry)) / 2)))
    return poly(name, [(cx + rx*math.cos(i*math.tau/count),
                        cy + ry*math.sin(i*math.tau/count))
                       for i in range(count)], fill, stroke, sw, z)


def _svg_commands(d):
    tokens = re.findall(r'[MmLlHhVvCcQqZz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?', d)
    sizes, out, current, first = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'Q': 4}, [], (0, 0), None
    i, op = 0, None
    while i < len(tokens):
        if tokens[i].isalpha():
            op = tokens[i]
            i += 1
            if op.upper() == 'Z':
                if first is not None:
                    out.append(('L', *first))
                    current = first
                continue
        if op is None:
            raise ValueError('SVG path must begin with M')
        n = sizes[op.upper()]
        values = [float(v) for v in tokens[i:i+n]]
        i += n
        if op.upper() == 'H':
            point = ((current[0]+values[0]) if op.islower() else values[0], current[1])
            out.append(('L', *point))
        elif op.upper() == 'V':
            point = (current[0], (current[1]+values[0]) if op.islower() else values[0])
            out.append(('L', *point))
        else:
            if op.islower():
                values = [v + current[j % 2] for j, v in enumerate(values)]
            point = tuple(values[-2:])
            out.append(tuple(values) if op.upper() == 'M' else (op.upper(), *values))
        if op.upper() == 'M':
            first = point
            op = 'l' if op.islower() else 'L'
        current = point
    return out


def path(name, d, fill=None, stroke=None, sw=3, z=0, closed=True):
    """Bezier command list [(x,y),('C',...),('Q',...),('L',...)] or SVG d."""
    commands = _svg_commands(d) if isinstance(d, str) else d
    points, p = [], None
    for a in commands:
        if len(a) == 2:
            p = tuple(a)
            points.append(p)
        elif a[0].upper() in ('M', 'L'):
            p = tuple(a[1:3])
            points.append(p)
        elif a[0].upper() == 'C':
            x, y = p
            x1, y1, x2, y2, x3, y3 = a[1:]
            for j in range(1, 17):
                t, u = j/16, 1-j/16
                points.append((u**3*x+3*u*u*t*x1+3*u*t*t*x2+t**3*x3,
                               u**3*y+3*u*u*t*y1+3*u*t*t*y2+t**3*y3))
            p = (x3, y3)
        elif a[0].upper() == 'Q':
            x, y = p
            x1, y1, x2, y2 = a[1:]
            for j in range(1, 13):
                t, u = j/12, 1-j/12
                points.append((u*u*x+2*u*t*x1+t*t*x2, u*u*y+2*u*t*y1+t*t*y2))
            p = (x2, y2)
    return (poly(name, points, fill, stroke, sw, z) if fill is not None else
            line(name, points, stroke or INK, sw, z, closed))


def text(name, body, x, y, size=48, fill='#FFFFFF', align='CENTER', z=50,
         *, font=None, line_spacing=1.1, max_width=None):
    """Native font geometry; x is the alignment anchor and y is the TOP edge."""
    d = bpy.data.curves.new(name, 'FONT')
    d.body, d.size, d.align_x = str(body), size, align.upper()
    d.align_y, d.space_line = 'TOP_BASELINE', line_spacing
    selected_font = font or resolve_font()
    if selected_font:
        d.font = bpy.data.fonts.load(str(selected_font), check_existing=True)
        if not d.font.packed_file:
            d.font.pack()
    d.materials.append(material(fill))
    obj = _link(bpy.data.objects.new(name, d))
    obj.location = (x, H-y-size*.78, _z(z))
    if max_width:
        bpy.context.view_layer.update()
        if obj.dimensions.x > max_width:
            obj.scale.x = max_width / obj.dimensions.x
    return obj


def _curves(obj):
    action = obj.animation_data.action if obj.animation_data else None
    if not action:
        return []
    old = getattr(action, 'fcurves', None)
    if old is not None:
        return list(old)
    result = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in getattr(strip, 'channelbags', []):
                result.extend(bag.fcurves)
    return result


def _key(obj, data_path, frame, interpolation='BEZIER'):
    obj.keyframe_insert(data_path=data_path, frame=frame)
    for fc in _curves(obj):
        if fc.data_path == data_path:
            for kp in fc.keyframe_points:
                if abs(kp.co.x-frame) < .001:
                    kp.interpolation = interpolation
                    if interpolation == 'BEZIER':
                        kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'


def show(obj, start=1, end=None):
    """Show a complete hierarchy only for inclusive [start,end] frames."""
    end = bpy.context.scene.frame_end if end is None else end
    original = obj.scale.copy()
    if max(abs(v) for v in original) < .0001:
        original = Vector(obj.get('_visible_scale', (1, 1, 1)))
    obj['_visible_scale'] = tuple(original)
    for frame, visible in [(0, False), (max(0, start-1), False),
                           (start, True), (end, True), (end+1, False)]:
        obj.scale = original if visible else (0, 0, 0)
        _key(obj, 'scale', frame, 'CONSTANT')
    obj.scale = original
    return obj


def slide(obj, start, end, from_xy, to_xy, *, interpolation='BEZIER'):
    """Move a top-level group in screen pixels, preserving its Z layer."""
    for frame, (x, y) in [(start, from_xy), (end, to_xy)]:
        obj.location.x, obj.location.y = x, H-y
        _key(obj, 'location', frame, interpolation)
    return obj


def camera_move(start, end, zoom=1, dx=0, dy=0):
    camera = bpy.context.scene.camera
    base_loc, base_scale = _camera_base
    camera.location, camera.data.ortho_scale = base_loc.copy(), base_scale
    _key(camera, 'location', start)
    camera.data.keyframe_insert(data_path='ortho_scale', frame=start)
    camera.location = base_loc + Vector((dx, -dy, 0))
    camera.data.ortho_scale = base_scale / zoom
    _key(camera, 'location', end)
    camera.data.keyframe_insert(data_path='ortho_scale', frame=end)
    return camera


def _joint(name, parent, x=0, y=0, z=0):
    obj = _link(bpy.data.objects.new(name, None))
    obj.parent = parent
    obj.location = (x, -y, z)
    return obj


def _draw(parent, fn, *args, **kwargs):
    obj = fn(*args, **kwargs)
    obj.parent = parent
    obj.matrix_parent_inverse = Matrix.Identity(4)
    # Primitive vertices are screen-based. Remove H once to make rig-local art.
    obj.location.y -= H
    return obj


def _rot(obj, angle, frame=None):
    obj.rotation_euler.z = angle
    if frame is not None:
        _key(obj, 'rotation_euler', frame)



def render(pathname, frame=1, *, save_blend=None):
    """Render an actual camera frame, optionally saving the editable scene."""
    scene = bpy.context.scene
    scene.frame_set(frame)
    scene.render.filepath = str(pathname)
    if save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=str(save_blend))
    bpy.ops.render.render(write_still=True)
