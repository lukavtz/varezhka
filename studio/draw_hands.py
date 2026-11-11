"""Shared geometry helpers for simple mitten silhouettes."""
import math
import blender_flat as F
REAR=23.8
FRONT=27.5
DETAIL=28.0


def _group(A,label,origin,angle=0,mirror=1):
    g=F._joint(A.name+'.hand.'+label,A.root,*origin)
    g.rotation_euler.z=-angle
    g.scale.x=mirror
    c,s=math.cos(angle),math.sin(angle)
    def point(p):
        xx,yy=p[0]*mirror,p[1]
        return (origin[0]+xx*c-yy*s,origin[1]+xx*s+yy*c)
    return g,point


def _samples(commands):
    out=[];last=None
    for a in commands:
        if len(a)==2:last=tuple(a);out.append(last)
        elif a[0]=='L':last=tuple(a[1:]);out.append(last)
        elif a[0]=='Q':
            start=last
            for i in range(1,9):
                t=i/8;u=1-t
                out.append((u*u*start[0]+2*u*t*a[1]+t*t*a[3],u*u*start[1]+2*u*t*a[2]+t*t*a[4]))
            last=tuple(a[3:])
        elif a[0]=='C':
            start=last
            for i in range(1,13):
                t=i/12;u=1-t
                out.append((u**3*start[0]+3*u*u*t*a[1]+3*u*t*t*a[3]+t**3*a[5],u**3*start[1]+3*u*u*t*a[2]+3*u*t*t*a[4]+t**3*a[6]))
            last=tuple(a[5:])
    return out


def _skin(A,name,commands,g,z,*,color=None,sw=2.8,open_inlet=False):
    p=A.p
    # An open inlet joins the sleeve without a black transverse wrist cut.
    obj=A.path(name,commands,color or p['skin'],z,'' if open_inlet else p['ink'],0 if open_inlet else sw,g)
    if open_inlet:A.curve(name+'.external',commands,z+.015,p['ink'],sw,g)
    return obj


def _meta(g,tr,*,wrist,palm,thumb,tips,inlet,outline,z=FRONT,**extra):
    values=dict(wrist=tr(wrist),wrist_anchor=tr(wrist),palm=tr(palm),thumb=tr(thumb),
                fingertips=[tr(p) for p in tips],inlet=[tr(p) for p in inlet],
                inlet_width=math.dist(inlet[0],inlet[1]),outline=[tr(p) for p in _samples(outline)],
                z=z,palm_z=z,thumb_z=DETAIL,finger_z=FRONT,
                hand_root_name=g.name)
    values.update(extra)
    return values


def _inlet(origin,mirror,wrist,elbow):
    """Actual cuff normal from the elbow, expressed in canonical hand space."""
    if elbow is None:
        axis=(.35,.93675)
    else:
        wx,wy=origin[0]+mirror*wrist[0],origin[1]+wrist[1]
        dx,dy=(wx-elbow[0])*mirror,wy-elbow[1]
        length=math.hypot(dx,dy)
        axis=(dx/length,dy/length)
    nx,ny=-axis[1]*10,axis[0]*10
    return (wrist[0]+nx,wrist[1]+ny),(wrist[0]-nx,wrist[1]-ny),axis
