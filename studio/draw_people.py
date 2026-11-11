"""Five original static human pose drawings, made only from Blender geometry.

person(name, pose, x, floor_y, scale=1, facing='right', palette=None)
returns world-screen joints and contact data as well as the editable root.
Standing height is about 680px; the head including its cap is ~150px.
These are editable pose drawings. See build_animation.py for a small moving-hold example.

Layer contract: shadow9, body/legs20, visible sleeves21..21.2, head22,
tabletop24, carried prop25, palm27, thumb/finger pads28. Chair parts12..15.
"""
from __future__ import annotations
import math,sys,json
from pathlib import Path
import bpy
from mathutils import Vector

import blender_flat as F
import draw_mitten_hands as H

INK='#302A25'
PALETTE=dict(ink=INK,skin='#EED9B0',skin_shadow='#D4B78D',skin_light='#F6E5C6',
             cheek='#D8A087',hoodie='#B96D42',hoodie_dark='#945332',
             hoodie_light='#C9804D',jeans='#365F84',jeans_dark='#294967',
             jeans_light='#4A7597',boot='#594634',boot_light='#756047',
             sole='#BAA385',cap='#6E8248',cap_dark='#4B6032',cap_light='#829957',
             hair='#533927',shadow='#293538')

PRESETS={
 'walk':dict(head=(18,-590),neck=(7,-528),pelvis=(-10,-303),
   shoulderL=(-54,-504),shoulderR=(61,-502),elbowL=(-80,-410),elbowR=(58,-410),
   wristL=(-66,-324),wristR=(120,-363),hipL=(-5,-306),hipR=(3,-301),
   kneeL=(44,-163),kneeR=(-47,-169),ankleL=(93,-24),ankleR=(-106,-48),
   bootL=0,bootR=30,tilt=.035),
 'seated':dict(head=(-28,-479),neck=(-24,-416),pelvis=(-35,-190),
   shoulderL=(-92,-393),shoulderR=(40,-398),elbowL=(1,-320),elbowR=(117,-344),
   wristL=(91,-296),wristR=(186,-296),hipL=(-54,-190),hipR=(-15,-190),
   kneeL=(76,-190),kneeR=(125,-190),ankleL=(74,-24),ankleR=(131,-24),
   bootL=0,bootR=0,tilt=.025),
 'crouch':dict(head=(68,-438),neck=(39,-377),pelvis=(-20,-165),
   shoulderL=(-36,-344),shoulderR=(79,-353),elbowL=(-4,-244),elbowR=(151,-258),
   wristL=(62,-138),wristR=(200,-181),hipL=(-39,-165),hipR=(-4,-161),
   kneeL=(-89,-26),kneeR=(82,-100),ankleL=(-146,-48.3492605204289),ankleR=(22,-24),
   bootL=110,bootR=0,tilt=.085),
 'carry':dict(head=(-18,-590),neck=(-18,-528),pelvis=(-8,-300),
   shoulderL=(-79,-492),shoulderR=(53,-500),elbowL=(-112,-410),elbowR=(125,-428),
   wristL=(-82,-354),wristR=(120,-354),hipL=(-30,-299),hipR=(34,-300),
   kneeL=(-67,-154),kneeR=(47,-159),ankleL=(-57,-24),ankleR=(70,-24),
   bootL=0,bootR=0,tilt=-.025),
 'explain':dict(head=(-3,-590),neck=(-8,-527),pelvis=(-8,-310),
   shoulderL=(-80,-501),shoulderR=(65,-507),elbowL=(-123,-412),elbowR=(136,-459),
   wristL=(-47,-382),wristR=(205,-443),hipL=(-38,-308),hipR=(31,-307),
   kneeL=(-46,-166),kneeR=(56,-169),ankleL=(-45,-24),ankleR=(68,-24),
   bootL=0,bootR=0,tilt=-.025)
}


def _path_points(commands):
    points=[];p=None
    for a in commands:
        if len(a)==2:p=Vector(a);points.append(tuple(p))
        elif a[0]=='L':p=Vector(a[1:]);points.append(tuple(p))
        elif a[0]=='C':
            start=p.copy();a1,a2,end=Vector(a[1:3]),Vector(a[3:5]),Vector(a[5:7])
            for i in range(1,17):
                t=i/16;u=1-t;points.append(tuple(start*u**3+a1*(3*u*u*t)+a2*(3*u*t*t)+end*t**3))
            p=end
        elif a[0]=='Q':
            start=p.copy();control,end=Vector(a[1:3]),Vector(a[3:5])
            for i in range(1,13):
                t=i/12;u=1-t;points.append(tuple(start*u*u+control*(2*u*t)+end*t*t))
            p=end
    return F._clean_points(points)


def _mix(a,b,t):
    aa,bb=F.rgba(a),F.rgba(b)
    return '#'+''.join('%02X'%round(255*(x+(y-x)*t)) for x,y in zip(aa[:3],bb[:3]))


def _tube_edges(a,b,c,widths):
    """Round outer bend, short concave inner fillet; one complete silhouette."""
    A,B,C=Vector(a),Vector(b),Vector(c)
    u,v=B-A,C-B;l1,l2=u.length,v.length;u.normalize();v.normalize()
    n1,n2=Vector((-u.y,u.x)),Vector((-v.y,v.x))
    turn=math.atan2(u.x*v.y-u.y*v.x,u.dot(v))
    w0,w1,w2=widths;edges=[]
    for side in (1,-1):
        start=A+n1*(side*w0);end=C+n2*(side*w2)
        if abs(turn)<.05:
            d=min(17,l1*.25,l2*.25);P=B-u*d+n1*(side*w1);R=B+v*d+n2*(side*w1)
            Q=B+(n1+n2).normalized()*(side*w1)
            middle=[P*(1-t)**2+Q*(2*(1-t)*t)+R*t*t for t in (i/10 for i in range(11))]
        elif turn*side<0:
            angle=math.atan2(side*n1.y,side*n1.x)
            middle=[B+Vector((math.cos(angle+turn*t),math.sin(angle+turn*t)))*w1 for t in (i/12 for i in range(13))]
            P,R=middle[0],middle[-1]
        else:
            M=B+(n1+n2)*(side*w1/max(.16,1+u.dot(v)))
            if (M-B).length>min(l1,l2)*.6:M=B+(M-B).normalized()*min(l1,l2)*.6
            r=min(10,l1*.15,l2*.15);P,R=M-u*r,M+v*r
            middle=[P*(1-t)**2+M*(2*(1-t)*t)+R*t*t for t in (i/10 for i in range(11))]
        edges.append([start.lerp(P,i/7) for i in range(7)]+middle+[R.lerp(end,i/7) for i in range(1,8)])
    left,right=edges
    endcap=[C+n2*(math.cos(t)*w2)+v*(math.sin(t)*5) for t in (math.pi*i/10 for i in range(1,10))]
    startcap=[A-n1*(math.cos(t)*w0)-u*(math.sin(t)*6) for t in (math.pi*i/10 for i in range(1,10))]
    return left+endcap+list(reversed(right))+startcap,edges


def _arm_socket(shoulder,elbow,side):
    S,B=Vector(shoulder),Vector(elbow)
    # The armpit rises when the upper arm is lifted. Keeping it at the resting
    # 65px depth makes a forward-reaching sleeve fold across its own border.
    u=(B-S).normalized();depth=max(35,min(65,65*abs(u.y)))
    crest=S+Vector((-6,5) if side=='L' else (7,4))
    pit=S+Vector((12,depth) if side=='L' else (-10,depth))
    return crest,pit


def _sleeve_edges(a,b,c,widths,side):
    """A lateral shoulder socket, not a tube beginning on the front chest.

    The outer border continues the shirt's shoulder crest. The inner border
    begins at its armpit; there is intentionally no collar-to-elbow stroke.
    The rest of the same silhouette runs through elbow, forearm and cuff.
    """
    S,B,C=Vector(a),Vector(b),Vector(c)
    _,edges=_tube_edges(a,b,c,widths)
    outside=0 if side=='L' else 1
    inside=1-outside
    sign=-1 if side=='L' else 1
    crest,pit=_arm_socket(a,b,side)
    outer_end=edges[outside][7]
    inner_end=edges[inside][7]
    cap=S+Vector((sign*31,18))
    # Use the actual lateral deltoid and armpit from the torso drawing. These
    # roots are not moved inward toward the sternum when the arm is bent.
    outer=[crest*(1-t)**2+cap*(2*(1-t)*t)+outer_end*t*t
           for t in (i/12 for i in range(12))]
    inner_control=pit+(inner_end-pit)*.45
    inner=[pit*(1-t)**2+inner_control*(2*(1-t)*t)+inner_end*t*t
           for t in (i/12 for i in range(12))]
    edges[outside]=outer+edges[outside][7:]
    edges[inside]=inner+edges[inside][7:]
    v=(C-B).normalized();n=Vector((-v.y,v.x));w=widths[2]
    cuff=[C+n*(math.cos(t)*w)+v*(math.sin(t)*5)
          for t in (math.pi*i/10 for i in range(1,10))]
    contour=edges[0]+cuff+list(reversed(edges[1]))
    return contour,edges,cuff


class _Artist:
    def __init__(self,name,root,palette):self.name,self.root,self.p=name,root,palette;self.objects=[]
    def path(self,name,commands,fill=None,z=20,stroke=None,sw=4.1,parent=None):
        if stroke is None and fill is not None:stroke=self.p['ink']
        obj=F._draw(parent or self.root,F.path,self.name+'.'+name,commands,fill,stroke,sw,z,closed=fill is not None)
        self.objects.append(obj);return obj
    def poly(self,name,points,fill,z=20,stroke=None,sw=4.1,parent=None):
        obj=F._draw(parent or self.root,F.poly,self.name+'.'+name,points,fill,stroke,sw,z)
        self.objects.append(obj);return obj
    def ellipse(self,name,cx,cy,rx,ry,fill,z=20,stroke=None,sw=3,parent=None):
        obj=F._draw(parent or self.root,F.ellipse,self.name+'.'+name,cx,cy,rx,ry,fill,stroke,sw,z)
        self.objects.append(obj);return obj
    def line(self,name,points,z=20,col=None,sw=2.1,parent=None):
        obj=F._draw(parent or self.root,F.line,self.name+'.'+name,points,col or self.p['ink'],sw,z)
        self.objects.append(obj);return obj
    def curve(self,name,commands,z=20,col=None,sw=2.1,parent=None):
        return self.path(name,commands,None,z,col or self.p['ink'],sw,parent)
    def tube(self,name,a,b,c,widths,fill,shadow,z,start_inset=0,shoulder_anchor=None):
        if start_inset:
            side='L' if name.endswith('.L') else 'R'
            contour,edges,cuff=_sleeve_edges(a,b,c,widths,side)
        else:
            contour,edges=_tube_edges(a,b,c,widths)
        back_z=z
        self.poly(name+'.fill',contour,fill,back_z)
        if start_inset:
            outside=0 if side=='L' else 1
            outer,inner=edges[outside],edges[1-outside]
            inset=[p.lerp(q,min(.22,6/max(1,(p-q).length))) for p,q in zip(outer,inner)]
            side_tone=outer+list(reversed(inset))
        else:
            _,inneredges=_tube_edges(a,b,c,tuple(w-7 for w in widths))
            side_tone=edges[0]+list(reversed(inneredges[0]))
        self.poly(name+'.side-tone',side_tone,shadow,back_z+.012)
        # Open only the physical shoulder socket: its top end is the lateral
        # crest and its bottom end is the armpit, never a line from the collar.
        outline=edges[0]+cuff+list(reversed(edges[1])) if start_inset else contour
        obj=F._draw(self.root,F.line,self.name+'.'+name+'.contour',outline,self.p['ink'],4.1,back_z+.025,not start_inset)
        self.objects.append(obj)
        B=Vector(b);u=(Vector(b)-Vector(a)).normalized();v=(Vector(c)-Vector(b)).normalized()
        n=Vector((-u.y,u.x))
        self.curve(name+'.crease',[tuple(B-u*7+n*4),('Q',*(B+n*7),*(B+v*8+n*3))],z+.03,shadow,2.1)
        return obj


def _local_group(name,parent,point,angle=0):
    group=F._joint(name,parent,point[0],point[1])
    group.rotation_euler.z=-angle
    return group


def _boot(A,side,ankle,degrees):
    g=_local_group(A.name+'.boot-root.'+side,A.root,ankle,math.radians(degrees));p=A.p
    outline=[(-25,-14),('Q',-25,-26,-9,-25),('L',9,-23),('Q',18,-20,22,-10),
             ('C',27,-5,50,-4,54,7),('Q',59,19,43,23),('L',-13,24),
             ('Q',-28,24,-28,12),('L',-25,-14)]
    A.path('boot.'+side,outline,p['boot'],20.25,p['ink'],4.1,g)
    A.path('boot.toe-light.'+side,[(9,-11),('Q',20,-8,26,-3),('C',37,-2,48,0,50,8),
           ('Q',33,13,14,7),('L',9,-11)],p['boot_light'],20.28,'',0,g)
    A.path('boot.sole.'+side,[(-27,13),('Q',5,20,54,11),('Q',56,21,43,23),
           ('L',-13,24),('Q',-27,24,-27,13)],p['sole'],20.29,p['ink'],2,g)
    A.curve('boot.collar.'+side,[(-23,-15),('Q',-8,-21,11,-18)],20.32,p['ink'],2,g)
    for i in range(3):
        yy=-12+i*6;A.line('boot.lace.'+side,[(-3,yy),(14,yy+2)],20.33,p['sole'],1.8,g)
    ang=math.radians(degrees)
    def transform(q):return (ankle[0]+q[0]*math.cos(ang)-q[1]*math.sin(ang),ankle[1]+q[0]*math.sin(ang)+q[1]*math.cos(ang))
    pts=[transform(q) for q in _path_points(outline)]
    bottom=max(y for _,y in pts)
    return dict(ankle=ankle,heel=transform((-18,22)),toe=transform((48,19)),
                sole=transform((14,24)),bottom=bottom,points=pts)


def _head(A,d,pose):
    p=A.p;g=_local_group(A.name+'.head-root',A.root,d['head'],d['tilt'])
    face=[(-48,-30),('C',-55,-5,-49,26,-34,44),('C',-23,59,2,65,21,55),
          ('C',43,44,54,14,51,-12),('C',49,-37,38,-55,16,-60),
          ('C',-6,-68,-39,-60,-48,-30)]
    A.path('face',face,p['skin'],22,p['ink'],3.8,g)
    A.path('brim.skin-shadow',[(-43,-32),('Q',0,-46,44,-30),('L',44,-22),
       ('Q',0,-34,-45,-22)],p['skin_shadow'],22.03,'',0,g)
    A.ellipse('ear',-48,3,9,12,p['skin_shadow'],22.05,p['ink'],2.8,g)
    A.curve('ear.fold',[(-51,-2),('Q',-40,3,-49,8)],22.06,p['hair'],1.6,g)
    A.path('hair',[(-48,-26),('L',-38,-41),('L',-29,-24),('L',-20,-37),
      ('L',-10,-26),('L',1,-36),('L',16,-27),('L',35,-36),('L',47,-24),
      ('L',45,-48),('L',-36,-51),('L',-48,-26)],p['hair'],22.07,'',0,g)
    for side,xx,yy in [('L',-16,-7),('R',17,-8)]:
        A.ellipse('eye.white.'+side,xx,yy,8.2,5.7,p['skin_light'],22.09,p['ink'],1.5,g)
        gaze_y=1.9 if pose in ('crouch','seated') else .3
        A.ellipse('iris.'+side,xx+2.1,yy+gaze_y,3.2,4.4,'#4B683C',22.10,parent=g)
        A.ellipse('pupil.'+side,xx+2.7,yy+gaze_y,1.7,3.2,p['ink'],22.11,parent=g)
        A.ellipse('eye.glint.'+side,xx+3.4,yy+gaze_y-1.8,.8,.9,'#FFF8DF',22.12,parent=g)
    if pose=='carry':
        brows=[(-26,-19,-17,-23,-7,-18),(8,-20,19,-24,28,-18)]
    elif pose=='explain':brows=[(-27,-22,-17,-27,-7,-23),(8,-20,18,-22,28,-18)]
    else:brows=[(-27,-19,-17,-22,-7,-19),(8,-20,18,-21,28,-17)]
    for i,(x0,y0,x1,y1,x2,y2) in enumerate(brows):A.curve('brow'+str(i),[(x0,y0),('Q',x1,y1,x2,y2)],22.13,p['ink'],2.1,g)
    A.path('nose',[(43,-2),('Q',59,3,48,10)],p['skin'],22.14,p['skin_shadow'],1.8,g)
    for xx,yy in [(9,13),(15,16),(5,18)]:A.ellipse('freckle',xx,yy,1.1,1.1,'#B79672',22.15,parent=g)
    A.path('cheek',[(30,16),('Q',40,13,43,20),('Q',37,25,30,21)],p['cheek'],22.16,'',0,g)
    if pose=='explain':
        A.path('smile',[(0,30),('Q',15,35,28,25),('Q',21,44,10,41),('Q',2,39,0,30)],'#71452F',22.18,p['ink'],1.9,g)
        A.path('teeth',[(3,31),('Q',15,35,24,29),('L',21,34),('Q',12,38,5,34)],p['skin_light'],22.19,'',0,g)
    else:
        A.curve('mouth',[(1,31),('Q',14,36 if pose!='carry' else 29,27,28)],22.18,p['ink'],2,g)
        A.curve('mouth.corner',[(25,27),('Q',29,28,29,31)],22.18,p['skin_shadow'],1.4,g)
    A.path('cap',[(-57,-33),('C',-56,-68,-34,-89,-2,-88),('C',31,-89,50,-66,53,-38),
      ('Q',0,-45,-57,-33)],p['cap'],22.21,p['ink'],3.8,g)
    A.path('cap.highlight',[(-34,-66),('Q',-7,-87,23,-72),('Q',-5,-77,-34,-66)],p['cap_light'],22.22,'',0,g)
    A.path('cap.band',[(-56,-43),('Q',-8,-56,54,-44),('L',54,-35),
      ('Q',0,-44,-57,-32)],p['cap_dark'],22.23,p['ink'],1.9,g)
    A.path('cap.visor',[(-7,-37),('Q',50,-49,72,-33),('Q',58,-23,43,-24),
      ('Q',14,-33,-7,-29)],p['cap'],22.24,p['ink'],3.2,g)
    A.ellipse('cap.button',-1,-89,4.2,3.2,p['cap_dark'],22.25,p['ink'],1.7,g)
    A.curve('cap.seam',[(-3,-84),('Q',-8,-69,-6,-49)],22.26,p['cap_dark'],1.7,g)
    return g


def _torso(A,d):
    p=A.p;N=Vector(d['neck']);SL,SR=Vector(d['shoulderL']),Vector(d['shoulderR']);P=Vector(d['pelvis'])
    NL,NR=N+Vector((-28,10)),N+Vector((28,10));WL,WR=P+Vector((-62,4)),P+Vector((65,4))
    _,AL=_arm_socket(SL,d['elbowL'],'L')
    _,AR=_arm_socket(SR,d['elbowR'],'R')
    T=Vector(d['head'])+Vector((0,49))
    A.path('neck',[(T.x-16,T.y-8),('Q',T.x,T.y-17,T.x+16,T.y-8),
       ('L',N.x+19,N.y+23),('Q',N.x,N.y+36,N.x-18,N.y+23)],p['skin_shadow'],19.7,p['ink'],2.6)
    outline=[tuple(NL),('C',NL.x-13,NL.y+1,SL.x-4,SL.y-6,SL.x-6,SL.y+5),
       ('Q',SL.x-14,SL.y+27,AL.x,AL.y),('C',AL.x+2,AL.y+45,WL.x-3,WL.y-35,WL.x,WL.y),
       ('Q',P.x,P.y+34,WR.x,WR.y),('C',WR.x+3,WR.y-35,AR.x-2,AR.y+45,AR.x,AR.y),
       ('Q',SR.x+14,SR.y+27,SR.x+7,SR.y+4),('C',SR.x+4,SR.y-7,NR.x+12,NR.y+2,NR.x,NR.y),
       ('Q',N.x,N.y+31,NL.x,NL.y)]
    A.path('hoodie.body',outline,p['hoodie'],20.5,p['ink'],4.1)
    A.path('hoodie.side-tone',[(SL.x+4,SL.y+20),('Q',AL.x+3,AL.y,WL.x+10,WL.y+3),
       ('L',WL.x+2,WL.y),('C',WL.x-2,WL.y-35,AL.x+2,AL.y+45,AL.x,AL.y),
       ('Q',SL.x-8,SL.y+26,SL.x+4,SL.y+20)],p['hoodie_dark'],20.52,'',0)
    A.path('hood.rim',[(NL.x-2,NL.y-2),('Q',N.x,N.y+20,NR.x+2,NR.y-2),
       ('L',NR.x+10,NR.y+10),('Q',N.x,N.y+47,NL.x-10,NL.y+10)],p['hoodie_dark'],20.55,p['ink'],2.2)
    A.curve('hood.highlight',[(NL.x+2,NL.y+5),('Q',N.x,N.y+29,NR.x-3,NR.y+5)],20.57,p['hoodie_light'],2.2)
    A.curve('drawstringL',[(N.x-14,N.y+26),('Q',N.x-15,N.y+65,N.x-19,N.y+91)],20.58,'#E4C89F',2.3)
    A.curve('drawstringR',[(N.x+15,N.y+25),('Q',N.x+17,N.y+62,N.x+16,N.y+84)],20.58,'#E4C89F',2.3)
    A.path('pocket',[(P.x-39,P.y-62),('Q',P.x,P.y-52,P.x+43,P.y-64),
       ('L',P.x+43,P.y-18),('Q',P.x+1,P.y-7,P.x-39,P.y-18)],p['hoodie_dark'],20.59,p['ink'],2.0)
    A.curve('pocket.edge',[(P.x-31,P.y-54),('Q',P.x,P.y-46,P.x+34,P.y-55)],20.60,p['hoodie_light'],1.7)
    for sign in (-1,1):
        A.curve('waist.fold'+str(sign),[(P.x+sign*48,P.y-21),('Q',P.x+sign*39,P.y-8,P.x+sign*24,P.y-4)],20.61,p['hoodie_dark'],2)


def _whole_arm(A, side, d, pose, prop_kind):
    """One editable arm: the cuff is derived from the hand's wrist inlet."""
    arm_root=_local_group(A.name+'.arm.'+side,A.root,(0,0))
    artist=_Artist(A.name,arm_root,A.p)
    wrist,elbow=d['wrist'+side],d['elbow'+side]
    angle=math.atan2(wrist[1]-elbow[1],wrist[0]-elbow[0])-math.pi/2
    if pose=='seated':
        hand=H.typing_hand(artist,side,(110 if side=='L' else 205,-298),elbow=elbow)
    elif pose=='carry':
        palm=(-58,-344) if side=='L' else (96,-344)
        hand=(H.board_hand if prop_kind=='board' else H.carry_hand)(artist,side,palm,elbow=elbow)
    elif pose=='crouch':
        hand=H.relaxed_hand(artist,side,wrist,angle) if side=='L' else H.grip_hand(artist,side,wrist)
    elif pose=='explain':
        hand=H.open_hand(artist,wrist,math.atan2(wrist[1]-elbow[1],wrist[0]-elbow[0])) if side=='L' else H.point_hand(artist,wrist)
    else:
        hand=H.relaxed_hand(artist,side,wrist,angle)
    # The sleeve ends at the exact inlet that created the hand. There is no
    # independent wrist translation or rotation after the arm is assembled.
    anchor=hand.get('wrist_anchor',hand['wrist'])
    d['wrist'+side]=anchor
    half_cuff=hand.get('inlet_width',28)/2+1
    z=21 if side=='L' else 21.2
    artist.tube('sleeve.'+side,d['shoulder'+side],elbow,anchor,(24,22,half_cuff),
                A.p['hoodie'],A.p['hoodie_dark'],z,start_inset=12)
    artist.line('cuff.'+side,hand.get('inlet',[]),z+.04,A.p['ink'],2) if hand.get('inlet') else None
    arm_root['chain']=json.dumps([d['shoulder'+side],elbow,anchor],ensure_ascii=False)
    arm_root['wrist_angle']=angle
    A.objects.extend(artist.objects)
    return hand,arm_root


def person(name,pose,x,floor_y,scale=1,facing='right',palette=None,prop_kind='box'):
    if pose not in PRESETS:raise ValueError('Choose walk, seated, crouch, carry or explain')
    if facing not in ('right','left'):raise ValueError('Facing is right or left')
    p=dict(PALETTE);p.update(palette or {})
    for base in ('hoodie','cap','jeans','boot'):
        if palette and base in palette:
            if base+'_light' not in palette:p[base+'_light']=_mix(p[base],'#F3E7CB',.22)
            if base+'_dark' not in palette:p[base+'_dark']=_mix(p[base],p['ink'],.3)
    d=dict(PRESETS[pose]);mirror=1 if facing=='right' else -1
    root=F.group(name,x,floor_y);root.scale=(scale*mirror,scale,1)
    A=_Artist(name,root,p)
    low=min(d['ankleL'][0],d['ankleR'][0]);high=max(d['ankleL'][0],d['ankleR'][0])
    A.ellipse('contact-shadow',(low+high)/2+12,2,(high-low)/2+62,9,p['shadow'],9)
    leg_width=(25,25,19) if pose=='seated' else (29,26,19)
    for side in ('L','R'):
        fill=p['jeans_dark' if side=='L' else 'jeans']
        leg_z=(20.2 if side=='L' else 19.8) if pose=='walk' else (20 if side=='L' else 20.1)
        A.tube('jeans.'+side,d['hip'+side],d['knee'+side],d['ankle'+side],leg_width,fill,p['jeans_dark'],leg_z)
    P=d['pelvis']
    A.path('jeans.waist',[(P[0]-53,P[1]-12),('Q',P[0],P[1]-24,P[0]+51,P[1]-12),
        ('L',P[0]+48,P[1]+20),('Q',P[0],P[1]+30,P[0]-51,P[1]+20)],p['jeans'],20.15,p['ink'],3.4)
    boots={side:_boot(A,side,d['ankle'+side],d['boot'+side]) for side in ('L','R')}
    _torso(A,d)
    head=_head(A,d,pose)
    hands,arms={},{}
    for side in ('L','R'):
        hands[side],arms[side]=_whole_arm(A,side,d,pose,prop_kind)
    transform=lambda q:(x+q[0]*scale*mirror,floor_y+q[1]*scale)
    def world_hand(hand):
        result={key:(transform(value) if isinstance(value,tuple) and len(value)==2 else [transform(q) for q in value] if key in ('fingertips','inlet','outline') else value) for key,value in hand.items()}
        result['palm_z']=hand.get('palm_z',hand.get('z',27));result['thumb_z']=hand.get('thumb_z',28.1);result['fingers']=result['fingertips']
        result['points_3d']=dict(palm=(*result['palm'],result['palm_z']),thumb=(*result['thumb'],result['thumb_z']),fingers=[(*q,hand.get('finger_z',28)) for q in result['fingertips']])
        return result
    world_hands={s:world_hand(hand) for s,hand in hands.items()}
    def world_rect(left,top,width,height):
        p0,p1=transform((left,top)),transform((left+width,top+height))
        return dict(x=min(p0[0],p1[0]),y=min(p0[1],p1[1]),w=width*scale,h=height*scale)
    contacts={}
    if pose=='seated':
        contacts.update(seat=transform((P[0]-1.5,P[1]+25)),seat_support=[transform((P[0]-30,-165)),transform((P[0]+45,-165))],
          chair_seat=world_rect(-102,-165,175,25),
          tabletop=[transform(hands[s]['support']) for s in ('L','R')])
    if pose=='crouch':contacts.update(handle_R=transform(hands['R']['grip']),knee_floor=transform((-89,0)))
    if pose=='carry':contacts.update(box=world_rect(-75,-505,190,155),
          box_support=[transform(hands[s]['palm']) for s in ('L','R')],box_thumb=[transform(hands[s]['thumb']) for s in ('L','R')])
    if pose=='explain':contacts['pointing_tip']=transform(hands['R']['pointing_tip'])
    feet={side:{key:(transform(value) if isinstance(value,tuple) else floor_y+value*scale if key=='bottom' else [transform(q) for q in value] if key=='points' else value) for key,value in foot.items()} for side,foot in boots.items()}
    if pose=='crouch':feet['L']['toe']=max(feet['L']['points'],key=lambda q:q[1])
    for foot in feet.values():foot['render_bottom']=foot['bottom']+2.05*scale
    contacts['heel']={side:feet[side]['heel'] for side in feet};contacts['toe']={side:feet[side]['toe'] for side in feet}
    contacts['sole']={side:feet[side]['sole'] for side in feet}
    contacts['hand_layers']=dict(body=20.5,left_sleeve=21,right_sleeve=21.2,head=22,prop=25,palm=27,thumb_fingers=28)
    contacts['hands']=world_hands
    root['pose']=pose;root['contact_positions']=json.dumps(contacts,ensure_ascii=False)
    F.bpy.context.view_layer.update()
    geometry=[o for o in A.objects if o.type in ('MESH','CURVE')]
    verts=[F._world_matrix(o)@Vector(q) for o in geometry for q in o.bound_box]
    bounds=(min(q.x for q in verts),F.H-max(q.y for q in verts),max(q.x for q in verts),F.H-min(q.y for q in verts))
    return dict(root=root,head=head,arms=arms,hands=world_hands,feet=feet,
                pelvis=transform(d['pelvis']),contacts=contacts,contact_positions=contacts,bounds=bounds,
                joints={key:transform(value) for key,value in d.items() if isinstance(value,tuple)},objects=geometry)


