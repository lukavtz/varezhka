"""Native Blender vector interiors for five pose studies.

Call one scene_* function after blender_flat.setup(1920, 1080). All positions
are top-left screen-space pixels; layer z=0..9 is reserved for backgrounds.
"""
import math
import blender_flat as v
from support import resolve_font

P = {
    'ink': '#343A37', 'ink_light': '#59645E', 'cream': '#E8DFC7',
    'cream_light': '#F3EBD9', 'plaster': '#D4CFBC', 'olive': '#76836D',
    'olive_dark': '#526653', 'blue': '#758E91', 'blue_dark': '#4D6268',
    'wood': '#B37B54', 'wood_dark': '#805F49', 'orange': '#C67C4E',
    'metal': '#9CA8A0', 'paper': '#F3EBD8', 'floor': '#B7A88D',
}

def depth(name,z):
    if name == 'monitor power lead': return 4
    if name.startswith('chair '): return 12 if z < 6 else 13
    if name.startswith('desk leg '): return 12
    if name in ('desktop','desk apron'): return 24
    if name.startswith(('keyboard','desk mouse','desk paper')): return 25 if z < 9 else 26
    if name.startswith(('monitor ','desk lamp')): return 23 + max(0,z-7)
    if name.startswith('tool case'): return 25 + min(1, max(0,z-8))*.6
    if name.startswith('office sill plant'): return 8
    return z

def rect(name, x, y, width, height, fill, z=1, stroke=None, sw=3, radius=0):
    return v.rect(name,x,y,width,height,fill,stroke,sw,depth(name,z),radius)

def poly(name, points, fill, z=1, stroke=None, sw=3):
    return v.poly(name,points,fill,stroke,sw,depth(name,z))

def line(name, points, color=None, z=2, sw=3):
    return v.line(name,points,color or P['ink_light'],sw,depth(name,z))

def circle(name, x, y, rx, ry, fill, z=2, stroke=None, sw=3):
    return v.ellipse(name,x,y,rx,ry,fill,stroke,sw,depth(name,z))

def text(name, value, x, y, size=32, fill=None, z=7, align='CENTER'):
    return v.text(name,value,x,y,size,fill or P['ink'],align,z,font=resolve_font(bold=True))

def backing(name, wall, floor_y=810, floor=None, horizon_y=650):
    rect(name+' wall',0,0,1920,floor_y,wall,0)
    # Restrained architectural trim makes the wall a constructed surface.
    rect(name+' lower wall band',0,floor_y-225,1920,210,'#C5CBB9',.4)
    rect(name+' upper molding',0,32,1920,16,'#B3BBA9',.5)
    line(name+' upper molding edge',[(0,48),(1920,48)],'#EAE5D3',.6,3)
    line(name+' lower rail',[(0,floor_y-225),(1920,floor_y-225)],'#A7B2A2',.6,3)
    rect(name+' floor',0,floor_y,1920,1080-floor_y,floor or P['floor'],1)
    rect(name+' baseboard',0,floor_y-15,1920,15,P['blue_dark'],2)
    line(name+' wall floor seam',[(0,floor_y),(1920,floor_y)],P['ink_light'],3,3)
    for x in (-600,-200,200,600,1000,1400,1800,2200,2600):
        line(name+' floor perspective',[(960+(x-960)*.25,floor_y),(x,1080)],'#968E79',2,2)
    first=floor_y+(1080-floor_y)*.36
    second=floor_y+(1080-floor_y)*.72
    line(name+' floor course one',[(0,first),(1920,first)],'#A69A84',2,2)
    line(name+' floor course two',[(0,second),(1920,second)],'#A69A84',2,2)

def wall_seam(name,x,top=100,bottom=790):
    line(name+' panel joint',[(x,top),(x,bottom)],'#B2B7A9',2,2)

def wall_vent(name,x,y,w=130,h=60):
    rect(name+' vent frame',x,y,w,h,P['blue_dark'],3,P['ink'],2,5)
    for dx in (7,w-7):
        for dy in (7,h-7):circle(name+' vent fastener',x+dx,y+dy,2,2,P['paper'],5)
    for j in range(4):
        line(name+' vent slot',[(x+14,y+13+j*10),(x+w-14,y+13+j*10)],P['cream'],4,2)

def plant(name,x,y,scale=1):
    poly(name+' pot',[(x-30*scale,y),(x+30*scale,y),(x+22*scale,y+45*scale),(x-22*scale,y+45*scale)],P['wood'],5,P['ink'],3)
    for dx,dy in [(-36,-58),(-18,-85),(5,-100),(25,-74),(39,-45)]:
        line(name+' stem',[(x,y),(x+dx*scale,y+dy*scale)],P['olive_dark'],4,3)
        circle(name+' leaf',x+dx*scale,y+dy*scale,14*scale,25*scale,P['olive'],4,P['olive_dark'],2)

def scene_hall():
    backing('hall',P['cream'],915,'#B7AE99')
    rect('hall left wall reveal',0,0,110,915,P['blue_dark'],2)
    rect('hall right wall reveal',1810,0,110,915,P['blue_dark'],2)
    for x in (145,545,1375,1775):wall_seam('hall',x,100,899)
    for x in (210,1400):
        rect('hall door frame',x-14,75,340,840,P['blue_dark'],3,P['ink'],4)
        rect('hall door',x,91,312,824,'#97A69A',4,P['ink'],3)
        rect('hall upper door inset',x+29,130,254,350,'#B4C0AE',5,P['ink_light'],2)
        rect('hall lower door inset',x+29,520,254,305,'#A9B7AA',5,P['ink_light'],2)
        circle('door knob',x+255,600,9,9,P['wood_dark'],6,P['ink'],2)
        rect('door number plate',x+121,152,68,32,P['paper'],6,P['blue_dark'],2,3)
        for yy in (250,490,730):
            rect('door hinge',x-3,yy,8,34,P['wood_dark'],6,P['ink'],1,2)
            line('door hinge pin',[(x+1,yy+3),(x+1,yy+30)],P['paper'],7,1)
        rect('door closer',x+70,98,115,14,P['blue_dark'],6,P['ink'],2,3)
        line('door closer arm',[(x+180,105),(x+235,126),(x+260,115)],P['blue_dark'],7,4)
    text('room number left','204',365,156,23,P['blue_dark'])
    text('room number right','206',1555,156,23,P['blue_dark'])
    rect('corridor signs',720,93,480,70,P['blue_dark'],3,None,0,6)
    text('corridor sign text','К ВЫХОДУ',925,110,34,P['paper'],4)
    line('corridor sign arrow shaft',[(1095,128),(1145,128)],P['paper'],4,4)
    poly('corridor sign arrow head',[(1143,118),(1157,128),(1143,138)],P['paper'],4)
    circle('corridor clock',1787,140,54,54,P['paper'],4,P['blue_dark'],5)
    line('clock hand short',[(1787,140),(1787,111)],P['ink'],5,4)
    line('clock hand long',[(1787,140),(1810,151)],P['ink'],5,4)
    rect('switch plate',1270,533,54,76,P['paper'],4,P['blue_dark'],3,5)
    rect('switch',1287,552,20,36,P['metal'],5,P['ink'],2,2)
    wall_vent('hall',580,660,138,74)
    for x in (50,1850):
        line('hall corner metal',[(x,55),(x,900)],'#87958B',2,5)
        for y in (180,475,760):circle('hall corner rivet',x,y,3,3,P['paper'],3)
    return {'floor_y':915,'focus':(760,220,1280,940),'person':(1040,915),'direction':'right'}

def scene_office():
    backing('office',P['cream_light'],940,'#B8AA93')
    for x in (100,700,1250,1820):wall_seam('office',x,90,924)
    # Deep window reveal and sill: the view is outside, not a loose rectangle.
    rect('window reveal',132,138,546,458,P['blue_dark'],3,P['ink'],4)
    rect('window view',158,162,494,410,'#B8CECB',4)
    poly('distant trees',[(158,505),(220,445),(264,489),(333,400),(404,488),(474,429),(558,497),(652,438),(652,572),(158,572)],'#8BAA9A',5)
    line('window vertical mullion',[(405,162),(405,572)],P['cream'],6,10)
    line('window horizontal mullion',[(158,365),(652,365)],P['cream'],6,9)
    rect('window sill',119,572,570,30,P['wood'],7,P['ink'],3)
    plant('office sill plant',220,539,.65)
    # Radiator pipes meet the floor and panel below the actual window sill.
    rect('radiator body',155,695,490,175,'#E2E2D5',4,P['blue_dark'],3,12)
    for x in range(182,630,37):
        rect('radiator rib',x,708,23,148,'#EDECE0',5,P['metal'],2,8)
    line('radiator pipe left',[(165,860),(165,909),(210,909)],P['blue_dark'],4,5)
    line('radiator pipe right',[(630,858),(630,909),(586,909)],P['blue_dark'],4,5)
    rect('office socket',710,815,54,65,P['paper'],4,P['blue_dark'],2,5)
    for y in (832,862):circle('socket aperture',737,y,5,5,P['blue_dark'],5)
    line('monitor power lead',[(1510,600),(1520,727),(1380,738),(1380,885),(750,885),(750,847)],P['blue_dark'],4,3)
    rect('office books shelf',755,190,300,14,P['wood_dark'],4,P['ink'],2)
    for x,w,h,c in [(780,28,82,P['olive_dark']),(812,24,106,P['blue_dark']),(840,33,94,P['wood']),(879,22,73,P['orange']),(906,32,100,P['olive'])]:
        rect('office reference book',x,190-h,w,h,c,5,P['ink_light'],2)
        line('book spine stripe',[(x+5,190-h+15),(x+w-5,190-h+15)],P['paper'],6,2)
    # Chair is visible behind and around the sitting person.
    rect('chair back',800,540,180,235,P['olive_dark'],5,P['ink'],5,35)
    rect('chair back insert',822,557,136,185,P['olive'],6,None,0,22)
    rect('chair seat',850,775,240,35,P['olive_dark'],6,P['ink'],4,12)
    line('chair stem',[(965,810),(965,900)],P['ink'],6,9)
    line('chair feet',[(890,926),(965,900),(1040,926)],P['ink'],6,8)
    for x in (890,1040):circle('chair caster',x,930,10,10,P['blue_dark'],13,P['ink'],2)
    # Desk is a real top and open legs; no front panel covers knees/feet.
    poly('desktop',[(1045,610),(1760,610),(1780,670),(1045,670)],P['wood'],7,P['ink'],4)
    rect('desk apron',1045,670,735,40,P['wood_dark'],6,P['ink'],3)
    rect('desk leg left',1250,708,38,232,P['wood_dark'],6,P['ink'],3)
    rect('desk leg right',1710,708,38,232,P['wood_dark'],6,P['ink'],3)
    # Monitor rests on its stand; keyboard and paper rest on the desk.
    rect('monitor stem',1458,580,36,55,P['blue_dark'],7,P['ink'],3)
    rect('monitor foot',1412,631,130,13,P['blue_dark'],8,P['ink'],2,4)
    rect('monitor casing',1390,370,295,230,P['blue_dark'],7,P['ink'],4,8)
    rect('monitor screen',1408,387,259,193,'#A9C6BE',8)
    line('monitor line 1',[(1431,430),(1588,430)],'#6F9694',9,5)
    line('monitor line 2',[(1431,455),(1630,455)],'#6F9694',9,5)
    line('monitor line 3',[(1431,480),(1558,480)],'#6F9694',9,5)
    poly('keyboard',[(1098,619),(1278,619),(1290,647),(1090,647)],'#D8D9CC',8,P['ink_light'],2)
    for i in range(8):line('keyboard keys',[(1108+i*20,626),(1119+i*20,626)],P['blue_dark'],9,2)
    circle('desk mouse',1309,637,14,8,P['paper'],8,P['ink_light'],2)
    rect('desk paper',1515,616,95,26,P['paper'],8,P['ink_light'],1)
    line('desk lamp upright',[(1730,610),(1730,486),(1690,436)],P['blue_dark'],7,8)
    rect('desk lamp base',1687,606,89,13,P['blue_dark'],25,P['ink'],2,5)
    poly('desk lamp shade',[(1650,436),(1710,436),(1699,460),(1658,460)],P['olive_dark'],8,P['ink'],3)
    rect('office upper cabinet',1450,120,340,165,'#B9C2B4',3,P['ink_light'],3,6)
    line('cabinet split',[(1620,120),(1620,285)],P['ink_light'],4,2)
    circle('cabinet pull left',1600,205,4,8,P['wood_dark'],5)
    circle('cabinet pull right',1640,205,4,8,P['wood_dark'],5)
    circle('office chair floor shadow',965,937,100,6,'#928B7C',9)
    for x in (1269,1729):circle('office desk foot shadow',x,938,35,5,'#928B7C',9)
    return {'floor_y':940,'person':(960,940),'chair_seat':(850,775,1090),'chair_back':(800,540,980,775),'desk':(1045,610,1780,670),'hands':[(1070,650),(1165,650)]}

def scene_workshop():
    backing('workshop','#D9D8C8',930,'#AAA995')
    for x in (80,680,1300,1850):wall_seam('workshop',x,80,915)
    rect('electrical panel',280,250,370,350,'#A7B4AA',3,P['blue_dark'],5,6)
    rect('panel inset',300,270,330,310,'#CBD0BF',4,P['ink_light'],2)
    line('panel seam',[(460,270),(460,580)],P['ink_light'],5,2)
    circle('panel lock',607,426,7,7,P['wood_dark'],5,P['ink'],2)
    line('surface conduit',[(465,250),(465,160),(760,160),(760,245)],P['blue_dark'],3,6)
    for x in (520,630,740):
        rect('conduit retaining clip',x,153,13,15,P['metal'],4,P['ink_light'],2)
        circle('clip screw',x+6,160,2,2,P['ink'],5)
    wall_vent('workshop',160,680,150,64)
    rect('pegboard',1365,180,390,340,'#C3B7A0',3,P['wood_dark'],4)
    for x in (1390,1432,1474,1516,1558,1600,1642,1684,1726):
        for y in (205,250,295,340,385,430,475):circle('peg hole',x,y,2.5,2.5,P['wood_dark'],4)
    line('pegboard saw handle',[(1400,270),(1450,270),(1465,300)],P['blue_dark'],5,8)
    poly('pegboard saw blade',[(1450,270),(1570,315),(1456,313)],P['metal'],4,P['ink_light'],2)
    line('pegboard wrench',[(1640,245),(1640,340)],P['blue_dark'],5,10)
    circle('wrench ring',1640,245,15,15,P['blue_dark'],5)
    line('hammer wooden handle',[(1540,445),(1540,365)],P['wood_dark'],5,11)
    rect('hammer metal head',1503,351,72,20,P['blue_dark'],6,P['ink'],2,4)
    line('pliers left grip',[(1690,445),(1707,395),(1721,365)],P['blue_dark'],5,7)
    line('pliers right grip',[(1738,445),(1721,395),(1707,365)],P['blue_dark'],5,7)
    circle('pliers joint',1714,395,5,5,P['wood'],6,P['ink'],1)
    for x in (1588,1615):
        line('screwdriver metal shaft',[(x,370),(x,425)],P['metal'],5,5)
        rect('screwdriver handle',x-6,335,12,38,P['orange'],6,P['ink'],2,4)
    rect('workbench top',1345,616,460,48,P['wood'],6,P['ink'],4)
    rect('workbench apron',1360,664,430,38,P['wood_dark'],5,P['ink'],3)
    for x in (1380,1730):rect('workbench leg',x,700,42,230,P['wood_dark'],5,P['ink'],3)
    rect('workbench shelf',1400,820,325,20,P['wood'],5,P['ink'],2)
    rect('bench storage bin',1430,760,125,58,P['blue'],6,P['ink_light'],2)
    rect('bench vice base',1670,592,70,23,P['blue_dark'],7,P['ink'],2)
    rect('bench clamp jaw',1683,570,45,22,P['blue_dark'],7,P['ink'],2)
    line('clamp spindle',[(1728,582),(1758,582)],P['ink'],8,4)
    circle('workbench left foot shadow',1400,929,36,5,'#8F927F',9)
    circle('workbench right foot shadow',1751,929,36,5,'#8F927F',9)
    circle('tool case floor shadow',1200,930,112,6,'#8F927F',9)
    # A real closed tool case sits on the floor; hand can meet its handle.
    rect('tool case body',1105,800,190,130,P['blue_dark'],8,P['ink'],4,10)
    rect('tool case face',1117,813,166,100,P['blue'],9,P['ink_light'],2,6)
    line('tool case handle',[(1167,800),(1167,775),(1233,775),(1233,800)],P['ink'],9,7)
    for x in (1140,1250):rect('tool case latch',x,800,14,20,P['wood'],10,P['ink'],2,2)
    return {'floor_y':930,'person':(1000,930),'focus':(750,390,1220,930),'case':(1105,800,190,130),'handle':(1200,775)}

def cargo_box(x,y,w,h,z=25):
    """Box held by a character; all dimensions are screen-space pixels."""
    rect('cargo box',x,y,w,h,'#C99B6E',z,P['ink'],4)
    poly('cargo top flap',[(x,y),(x+20,y-18),(x+w+8,y-18),(x+w,y)],'#DAB187',z+.1,P['ink'],3)
    rect('cargo paper tape',x+w*.42,y,w*.16,h,'#E8CF9D',z+.3)
    line('cargo tape edge',[(x+w*.42,y),(x+w*.42,y+h)],'#B99066',z+.4,2)
    rect('cargo address label',x+w*.58,y+h*.25,w*.29,h*.22,P['paper'],z+.5,P['ink_light'],2)
    line('cargo label lines',[(x+w*.62,y+h*.33),(x+w*.83,y+h*.33)],P['blue_dark'],z+.6,2)
    return {'box':(x,y,w,h),'bottom':y+h}

def scene_storage():
    backing('storage','#DED9C7',915,'#B8AA90')
    for x in (80,680,1300,1840):wall_seam('storage',x,80,899)
    # Open racks stay on the edges; the carry pose has clear space in centre.
    for x in (110,1475):
        rect('rack shadow',x+12,180,300,735,'#A9A894',3,P['ink_light'],3)
        for yy in (360,535,710,884):rect('rack shelf',x,yy,325,17,P['wood_dark'],4,P['ink'],2)
        for xx in (x,x+300):rect('rack upright',xx,168,25,747,P['wood_dark'],5,P['ink'],3)
        for row,yy in enumerate((235,410,585,760)):
            for col in range(2):
                bx=x+28+col*128;bw=112
                ph=(100,118,92,108)[(row*2+col)%4];py=yy+118-ph
                rect('stored parcel',bx,py,bw,ph,'#C59972' if (row+col)%2 else '#D1B08A',5,P['ink_light'],2,3)
                rect('parcel label',bx+15,py+24,55,23,P['paper'],6,P['ink_light'],1)
                line('parcel tape',[(bx+80,py),(bx+80,py+ph)],'#B0845E',6,3)
                line('parcel folded edge',[(bx+5,py+ph-10),(bx+bw-5,py+ph-10)],'#B0845E',6,2)
                line('parcel label marks',[(bx+21,py+31),(bx+60,py+31)],P['blue_dark'],7,2)
    rect('storage door',725,157,460,758,'#C7CEBE',2,P['blue_dark'],4)
    rect('storage door inner',755,187,400,698,'#D6DBCA',3,P['ink_light'],2)
    for y in (280,525,760):rect('storage door hinge',726,y,12,38,P['blue_dark'],4,P['ink'],2,2)
    circle('storage door knob',1086,585,10,10,P['wood_dark'],5,P['ink'],2)
    rect('delivery sign',825,200,260,55,P['blue_dark'],4,None,0,4)
    text('delivery text','ПОЧТА',955,211,30,P['paper'],5)
    wall_vent('storage',1250,642,130,64)
    line('floor trolley boundary',[(470,970),(740,970)],'#9E907C',3,3)
    return {'floor_y':915,'person':(1050,915),'box':(975,410,190,155),'hands':[(992,571),(1146,571)]}

def scene_explain_hall():
    backing('explain','#DFDFCE',915,'#B8AC94')
    for x in (70,500,875,1350,1840):wall_seam('explain',x,95,899)
    rect('lift portal',126,146,358,769,P['blue_dark'],3,P['ink'],4)
    rect('lift doors',143,164,324,746,'#A7B5AC',4,P['ink'],3)
    line('lift seam',[(305,164),(305,910)],P['ink_light'],5,3)
    rect('lift floor display',240,180,130,47,P['blue_dark'],6,None,0,4)
    text('lift floor indicator','05',305,189,26,P['paper'],7)
    rect('lift call panel',500,470,72,160,P['blue_dark'],5,P['ink'],3,7)
    circle('lift call up',536,516,16,16,P['paper'],6,P['ink'],2)
    circle('lift call down',536,578,16,16,P['paper'],6,P['ink'],2)
    poly('lift call up arrow',[(536,508),(529,521),(543,521)],P['blue_dark'],7)
    poly('lift call down arrow',[(529,573),(543,573),(536,586)],P['blue_dark'],7)
    rect('blueprint frame',910,290,400,320,P['wood_dark'],4,P['ink'],4)
    rect('blueprint paper',927,306,366,288,'#C9D8D0',5)
    rect('blueprint floorplan',970,348,180,168,None if False else '#DCE5D8',6,P['blue_dark'],3)
    line('plan rooms vertical',[(1045,348),(1045,468),(1150,468)],P['blue_dark'],7,3)
    line('plan rooms horizontal',[(970,430),(1045,430)],P['blue_dark'],7,3)
    line('plan legend one',[(1170,364),(1260,364)],P['blue_dark'],7,4)
    line('plan legend two',[(1170,390),(1250,390)],P['blue_dark'],7,4)
    line('plan legend three',[(1170,416),(1265,416)],P['blue_dark'],7,4)
    wall_vent('hall upper',1470,145,210,75)
    rect('notice frame',1655,385,155,220,P['wood_dark'],4,P['ink'],3)
    rect('notice paper',1669,399,127,192,P['paper'],5)
    for yy in (430,455,480,505):line('notice writing',[(1685,yy),(1780,yy)],P['blue'],6,3)
    return {'floor_y':915,'first_person':(650,915),'second_person':(1450,915),'board':(910,290,400,320),'lift':(140,160,330,750)}
