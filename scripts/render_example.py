"""Run the portable examples through a user-selected local Blender executable."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
if hasattr(sys.stdout,'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')


def executable(explicit,environment,name):
    value=explicit or os.environ.get(environment) or shutil.which(name)
    if not value:
        raise FileNotFoundError(f'{name} was not found. Pass its path or set {environment}.')
    candidate=Path(value).expanduser()
    if candidate.is_dir():candidate=candidate/(name+'.exe' if os.name=='nt' else name)
    if not candidate.is_file():
        found=shutil.which(str(candidate))
        if not found:raise FileNotFoundError(f'Executable does not exist: {candidate}')
        candidate=Path(found)
    return candidate.resolve()


def blender_command(binary,script,arguments):
    return [str(binary),'--factory-startup','--background','--python-exit-code','1',
            '--python',str(ROOT/'studio'/script),'--',*map(str,arguments)]


def encode_command(ffmpeg,mode,out):
    cmd=[str(ffmpeg),'-hide_banner','-loglevel','error','-nostdin','-y']
    if mode=='camera':
        for number in (1,2,3):
            cmd+=['-framerate','30','-i',str(out/'camera'/f'shot-{number:02d}-frames'/'frame-%04d.png')]
        cmd+=['-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[v]','-map','[v]']
        target=out/'camera-study.mp4'
    else:
        cmd+=['-framerate','30','-i',str(out/'animation'/'frames'/'frame-%04d.png')]
        target=out/'moving-hold.mp4'
    cmd+=['-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
    return cmd,target


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('stills','camera','animation'),default='stills')
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--blender',help='Blender executable or its containing directory')
    parser.add_argument('--ffmpeg',help='FFmpeg executable; needed only with --encode')
    parser.add_argument('--percent',type=int,default=100)
    parser.add_argument('--only',type=int,nargs='*',help='Stills 1..5, or camera shots 1..3')
    parser.add_argument('--preview-only',action='store_true',help='Animation mode: five review frames, no video sequence')
    parser.add_argument('--encode',action='store_true',help='Encode rendered camera/animation PNG sequences to MP4')
    parser.add_argument('--dry-run',action='store_true',help='Print commands without launching them')
    args=parser.parse_args()
    if not 1<=args.percent<=100:parser.error('--percent must be between 1 and 100')
    if args.preview_only and args.mode!='animation':parser.error('--preview-only is for animation mode')
    if args.encode and (args.mode=='stills' or args.preview_only):parser.error('--encode needs camera mode or full animation mode')
    if args.only and args.mode=='animation':parser.error('--only is not used in animation mode')
    maximum=5 if args.mode=='stills' else 3
    if args.only and any(n<1 or n>maximum for n in args.only):parser.error(f'--only values must be 1..{maximum}')
    if args.encode and args.only:parser.error('--encode needs all camera shots; omit --only')
    binary=executable(args.blender,'BLENDER_PATH','blender')
    ffmpeg=executable(args.ffmpeg,'FFMPEG_PATH','ffmpeg') if args.encode else None
    out=args.output.expanduser().resolve()
    commands=[]
    percent=['--percent',str(args.percent)]
    if args.mode in ('stills','camera'):
        base=['--output',str(out),*percent]
        if args.mode=='stills' and args.only:base+=['--only',*map(str,args.only)]
        commands.append(blender_command(binary,'build_studies.py',base))
    if args.mode=='camera':
        camera=['--source',str(out/'scenes'),'--output',str(out/'camera'),*percent,'--mode','video']
        if args.only:camera+=['--only',*map(str,args.only)]
        commands.append(blender_command(binary,'camera_studies.py',camera))
    if args.mode=='animation':
        animation=['--output',str(out/'animation'),*percent]
        if args.preview_only:animation+=['--preview-only']
        commands.append(blender_command(binary,'build_animation.py',animation))
    target=None
    if args.encode:
        command,target=encode_command(ffmpeg,args.mode,out)
        commands.append(command)
    if args.dry_run:
        print(json.dumps({'dry_run':True,'commands':commands,'output':str(out)},ensure_ascii=False,indent=2))
        return
    out.mkdir(parents=True,exist_ok=True)
    for command in commands:
        subprocess.run(command,check=True,cwd=str(ROOT))
    print(json.dumps({'status':'complete','mode':args.mode,'output':str(out),
        'video':str(target) if target else None,'preview_only':args.preview_only},ensure_ascii=False))


if __name__=='__main__':
    try:main()
    except (OSError,subprocess.CalledProcessError,ValueError) as error:
        print(f'ERROR: {error}',file=sys.stderr)
        sys.exit(1)
