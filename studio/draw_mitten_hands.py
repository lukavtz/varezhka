"""Simple cartoon mitten silhouettes, without separate fingers or fine creases."""
import math
from draw_hands import _group, _skin, _meta, _inlet, REAR, FRONT


def relaxed_hand(A,side,wrist,angle=0):
    mirror=1 if side=='L' else -1
    g,tr=_group(A,'mitten-rest.'+side,wrist,angle,mirror)
    outline=[(-9,0),('C',-11,10,-12,23,-6,29),
      ('Q',3,35,11,28),('Q',16,23,14,16),
      ('Q',21,18,22,13),('Q',23,8,16,6),('L',9,0)]
    _skin(A,'mitten.relaxed.'+side,outline,g,FRONT,open_inlet=True)
    return _meta(g,tr,wrist=(0,0),palm=(2,15),thumb=(18,12),tips=[(4,30)],
      inlet=[(-9,0),(9,0)],outline=outline,style='mitten')


def carry_hand(A,side,palm,elbow=None):
    mirror=1 if side=='L' else -1
    g,tr=_group(A,'mitten-box.'+side,palm,mirror=mirror)
    wrist=(-24,-10);low,high,axis=_inlet(palm,mirror,wrist,elbow)
    outline=[low,('C',-30,1,-24,9,-13,10),
      ('C',-1,12,10,8,16,2),('Q',21,-3,15,-6),
      ('L',-7,-6),('Q',-15,-7,-18,-13),('L',*high)]
    _skin(A,'mitten.box-support.'+side,outline,g,REAR,open_inlet=True)
    # A short thumb rests on the front corner; the grouped mitten is below.
    thumb=[(-24,0),('Q',-21,-9,-14,-12),
      ('Q',-8,-15,-5,-10),('Q',-3,-6,-10,-2),
      ('L',-14,3),('Q',-18,7,-23,6)]
    _skin(A,'mitten.box-thumb.'+side,thumb,g,FRONT,open_inlet=True)
    return _meta(g,tr,wrist=wrist,palm=(-7,4),thumb=(-10,-8),tips=[(12,1)],
      inlet=[low,high],outline=outline,z=REAR,support=tr((3,-6)),
      cuff_axis=[mirror*axis[0],axis[1]],style='mitten')


def board_hand(A,side,palm,elbow=None):
    mirror=1 if side=='L' else -1
    g,tr=_group(A,'mitten-board.'+side,palm,mirror=mirror)
    wrist=(-37,5);low,high,axis=_inlet(palm,mirror,wrist,elbow)
    outline=[low,('C',-48,-1,-46,-18,-38,-24),
      ('Q',-31,-29,-24,-25),('L',-14,-20),
      ('Q',-8,-14,-16,-9),('L',-23,-5),
      ('Q',-27,2,-31,4),('L',*high)]
    _skin(A,'mitten.board-palm.'+side,outline,g,REAR,open_inlet=True)
    thumb=[(-34,-18),('Q',-25,-25,-15,-22),
      ('Q',-8,-20,-12,-15),('Q',-16,-11,-24,-10),('L',-33,-7)]
    _skin(A,'mitten.board-thumb.'+side,thumb,g,FRONT,open_inlet=True)
    return _meta(g,tr,wrist=wrist,palm=(-34,-12),thumb=(-15,-18),tips=[(-17,-15)],
      inlet=[low,high],outline=outline,z=REAR,grip=tr((-22,-16)),
      support=tr((-22,-16)),cuff_axis=[mirror*axis[0],axis[1]],style='mitten')


def open_hand(A,wrist,angle=None,side='L'):
    angle=math.atan2(30,76) if angle is None else angle
    g,tr=_group(A,'mitten-belly.'+side,wrist,angle)
    if side=='R':g.scale.y=-1
    def local(p):return tr((p[0],p[1] if side=='L' else -p[1]))
    outline=[(0,-8),('Q',8,-8,11,-13),('Q',16,-17,21,-12),
      ('L',25,-6),('Q',33,-7,36,1),('Q',41,12,31,17),
      ('Q',17,21,0,8)]
    _skin(A,'mitten.belly.'+side,outline,g,FRONT,open_inlet=True)
    return _meta(g,local,wrist=(0,0),palm=(18,5),thumb=(17,-10),tips=[(35,8)],
      inlet=[(0,-8),(0,8)],outline=outline,cuff_axis=[math.cos(angle),math.sin(angle)],style='mitten')


def grip_hand(A,side,wrist,angle=None):
    angle=(-math.atan2(49,77) if side=='R' else math.atan2(49,77)) if angle is None else angle
    g,tr=_group(A,'mitten-case.'+side,wrist)
    axis=(-math.sin(angle),math.cos(angle));normal=(-axis[1],axis[0])
    low=(normal[0]*9,normal[1]*9);high=(-normal[0]*9,-normal[1]*9)
    outline=[low,('C',-11,12,-17,16,-16,26),
      ('Q',-12,36,1,36),('Q',17,35,16,23),
      ('C',15,10,high[0]+axis[0]*8,high[1]+axis[1]*8,high[0],high[1])]
    _skin(A,'mitten.case-rear.'+side,outline,g,REAR,open_inlet=True)
    A.line('mitten.handle-contact.'+side,[(-24,26),(24,26)],25.6,A.p['ink'],7,g)
    fist=[(-14,26),('Q',-15,18,-4,19),('L',10,21),
      ('Q',20,24,16,33),('Q',12,40,0,38),
      ('L',-10,35),('Q',-17,32,-14,26)]
    _skin(A,'mitten.case-fist.'+side,fist,g,FRONT)
    thumb=[(9,16),('Q',19,16,18,22),('L',8,28),
      ('Q',2,31,-1,26),('Q',-1,23,5,21)]
    _skin(A,'mitten.case-thumb.'+side,thumb,g,FRONT+.05,open_inlet=True)
    return _meta(g,tr,wrist=(0,0),palm=(0,22),thumb=(9,22),tips=[(1,36)],
      inlet=[low,high],outline=outline,z=REAR,grip=tr((0,26)),
      support=tr((0,26)),cuff_axis=list(axis),style='mitten')


def point_hand(A,wrist,angle=0,side='R'):
    g,tr=_group(A,'mitten-point.'+side,wrist,angle)
    outline=[(0,-8),('C',12,-11,23,-10,29,-7),
      ('L',59,-9),('Q',67,-9,65,-3),('L',30,1),
      ('Q',36,10,27,15),('Q',14,21,7,15),('L',0,8)]
    _skin(A,'mitten.point.'+side,outline,g,FRONT,open_inlet=True)
    return _meta(g,tr,wrist=(0,0),palm=(17,4),thumb=(10,13),tips=[(65,-5)],
      inlet=[(0,-8),(0,8)],outline=outline,pointing_tip=tr((65,-5)),
      cuff_axis=[math.cos(angle),math.sin(angle)],style='mitten')


def typing_hand(A,side,palm,elbow=None):
    g,tr=_group(A,'mitten-type.'+side,palm)
    wrist=(-19,2);low,high,axis=_inlet(palm,1,wrist,elbow)
    outline=[low,('Q',-7,11,5,8),('L',19,8),
      ('Q',31,7,28,1),('C',23,-5,10,-8,-2,-7),('L',*high)]
    _skin(A,'mitten.typing.'+side,outline,g,FRONT,open_inlet=True)
    return _meta(g,tr,wrist=wrist,palm=(0,2),thumb=(-6,6),tips=[(26,5)],
      inlet=[low,high],outline=outline,support=tr((24,8)),cuff_axis=list(axis),style='mitten')
