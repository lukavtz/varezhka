"""Build brief SFX demos with licensed source clips and original synthesis.

No voice, music, network, or paid services are used. Source provenance is in
sources.json. Deterministic random seed keeps the synthetic parts reproducible.
"""
import json
import math
import subprocess
from pathlib import Path
import numpy as np
import wave

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'source'; DEMO=ROOT/'demos'; SYN=ROOT/'synthetic'
for p in (DEMO,SYN):p.mkdir(parents=True,exist_ok=True)
SR=48000
rng=np.random.default_rng(20261103)

def env(t,total,attack=.08,release=.3):
    return np.minimum(1,np.maximum(0,t/attack))*np.minimum(1,np.maximum(0,(total-t)/release))

def write(name,data):
    data=np.asarray(data,dtype=np.float32)
    if data.ndim==1:data=np.column_stack((data,data))
    peak=float(np.max(np.abs(data))) if len(data) else 0
    if peak>.91:data=data*(.91/peak)
    with wave.open(str(name),'wb') as f:
        f.setnchannels(2);f.setsampwidth(2);f.setframerate(SR)
        f.writeframes(np.asarray(data*32767,dtype='<i2').tobytes())

def load(path):
    raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-ar',str(SR),'-ac','2','-'])
    return np.frombuffer(raw,dtype='<f4').reshape(-1,2).copy()

def filtered_noise(n,window=450):
    # A moving average makes a soft low-frequency rumble without external audio.
    a=rng.standard_normal(n+window).astype(np.float32)
    cumulative=np.r_[0,np.cumsum(a,dtype=np.float64)]
    x=(cumulative[window:]-cumulative[:-window])[:n]
    return x/(np.max(np.abs(x))+1e-12)

def motor():
    dur=7.2;t=np.arange(round(dur*SR))/SR
    w=env(t,dur,.6,.9)
    return w*(.13*np.sin(2*np.pi*57*t)+.055*np.sin(2*np.pi*114*t)+.09*filtered_noise(len(t),300))*(.94+.06*np.sin(2*np.pi*.9*t))

def poweroff():
    dur=2.5;t=np.arange(round(dur*SR))/SR
    phase=2*np.pi*(140*t-44*t*t/2)
    fall=np.exp(-t*1.8)*np.minimum(1,t/.025)
    return fall*(.28*np.sin(phase)+.11*np.sin(2*phase)+.10*filtered_noise(len(t),40))

def creak():
    dur=2.4;t=np.arange(round(dur*SR))/SR
    phase=2*np.pi*(410*t+90*np.sin(2*np.pi*.22*t))
    return env(t,dur,.22,.45)*(.10*np.sin(phase)*(0.6+0.4*np.sin(2*np.pi*8*t))+.11*filtered_noise(len(t),32))

def tension():
    dur=7.4;t=np.arange(round(dur*SR))/SR
    rise=np.minimum(1,t/4.8)*env(t,dur,.5,.9)
    wave=np.sin(2*np.pi*48*t)+.4*np.sin(2*np.pi*49.1*t)+.3*np.sin(2*np.pi*71*t)
    return rise*(.10*wave+.09*filtered_noise(len(t),500))

originals={'motor-hum.wav':motor(),'power-down.wav':poweroff(),'metal-creak.wav':creak(),'low-tension.wav':tension()}
for name,data in originals.items():write(SYN/name,data)

def add(buf,clip,when,gain=1,limit=None):
    if clip.ndim==1:clip=np.column_stack((clip,clip))
    if limit:
        clip=clip[:round(limit*SR)].copy()
        tail=min(len(clip),round(.16*SR))
        clip[-tail:]*=np.linspace(1,0,tail,dtype=np.float32)[:,None]
    start=round(when*SR);n=min(len(clip),len(buf)-start)
    if n>0:buf[start:start+n]+=gain*clip[:n]

door=load(SRC/'elevator_door.wav')
ding=load(SRC/'elevatording.ogg')
click=load(SRC/'kenney-interface'/'click_001.ogg')
switch=load(SRC/'kenney-interface'/'switch_004.ogg')
glitch=load(SRC/'kenney-interface'/'glitch_004.ogg')

def new():return np.zeros((round(7.5*SR),2),dtype=np.float32)
e=new();add(e,click,.25,.65);add(e,door,.65,.45,2.1);add(e,originals['motor-hum.wav'],2.0,.75,4.4);add(e,ding,6.15,.62);write(DEMO/'01-elevator.wav',e)
p=new();add(p,originals['motor-hum.wav'],0,.6,3.1);add(p,switch,2.1,.5);add(p,glitch,2.18,.45);add(p,originals['power-down.wav'],2.2,.8);add(p,originals['low-tension.wav'],3.1,.42,4.2);write(DEMO/'02-power-out.wav',p)
t=new();add(t,originals['low-tension.wav'],0,.8);add(t,originals['metal-creak.wav'],2.3,.65);add(t,door,5.2,.18,1.3);write(DEMO/'03-tension.wav',t)

entries=[]
for filename,author,page,url in [
 ('elevator_door.wav','PagDev','https://opengameart.org/content/elevatordoor','https://opengameart.org/sites/default/files/elevator_door.wav'),
 ('elevatording.ogg','fvcalderan','https://opengameart.org/content/elevator-ding','https://opengameart.org/sites/default/files/elevatording_0.ogg')]:
 entries.append({'path':'source/'+filename,'creator':author,'source_page':page,'direct_download':url,'license':'CC0-1.0','acquisition':'downloaded direct'})
for path in sorted((SRC/'kenney-interface').glob('*.ogg')):
 entries.append({'path':'source/kenney-interface/'+path.name,'creator':'Kenney','source_page':'https://kenney.nl/assets/interface-sounds','direct_download':'https://kenney.nl/media/pages/assets/interface-sounds/fa43c1dd4d-1677589452/kenney_interface-sounds.zip','license':'CC0-1.0','acquisition':'copied from local installed brag skill; upstream ZIP request returned HTML'})
for name in originals:
 entries.append({'path':'synthetic/'+name,'creator':'Original procedural synthesis for this project','source_page':None,'direct_download':None,'license':'Original project asset','acquisition':'generated locally; no third-party recordings'})
meta={'license_reference':'https://creativecommons.org/publicdomain/zero/1.0/','note':'CC0 sources do not require attribution. Names and source links are retained for traceability. Demos combine these assets with original project synthesis. Do not treat synthesized motor, power and tension as field recordings.',
 'sources':entries,
 'recommended_packs':[{'creator':'Kenney','name':'Interface Sounds','page':'https://kenney.nl/assets/interface-sounds','license':'CC0-1.0','status':'10 selected local copies; upstream zip was not downloaded successfully'}, {'creator':'Kenney','name':'Sci-fi Sounds','page':'https://kenney.nl/assets/sci-fi-sounds','license':'CC0-1.0','status':'recommended; upstream zip was not downloaded successfully'}],
 'demos':[{'path':'demos/01-elevator.wav','duration_s':7.5,'elements':['click_001.ogg','elevator_door.wav','motor-hum.wav','elevatording.ogg']},{'path':'demos/02-power-out.wav','duration_s':7.5,'elements':['motor-hum.wav','switch_004.ogg','glitch_004.ogg','power-down.wav','low-tension.wav']},{'path':'demos/03-tension.wav','duration_s':7.5,'elements':['low-tension.wav','metal-creak.wav','elevator_door.wav']}]}
(ROOT/'sources.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
print('Built',len(entries),'documented source assets and 3 demos')
