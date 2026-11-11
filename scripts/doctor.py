#!/usr/bin/env python3
"""Read-only local tool check. Does not install, change config or reveal secrets."""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import socket
import subprocess
import sys


def executable(value):
    if not value:
        return None
    candidate=Path(value).expanduser()
    if candidate.is_file():
        return str(candidate.resolve())
    return shutil.which(value)


def find_blender(explicit=None):
    """An explicit selection is authoritative, even when invalid."""
    selected=explicit or os.environ.get('BLENDER_PATH')
    if selected:
        return executable(selected)
    found=shutil.which('blender')
    if found:
        return found
    candidates=[]
    if sys.platform=='win32':
        program_files=os.environ.get('ProgramFiles')
        if program_files:
            root=Path(program_files)/'Blender Foundation'
            candidates+=sorted(root.glob('Blender */blender.exe'),reverse=True)
    elif sys.platform=='darwin':
        candidates=[Path('/Applications/Blender.app/Contents/MacOS/Blender')]
    else:
        candidates=[Path('/usr/bin/blender'),Path('/usr/local/bin/blender')]
    return next((str(p) for p in candidates if p.is_file()),None)


def tool_status(path,version_args):
    if not path:
        return {'available':False,'path':None,'version':None}
    try:
        result=subprocess.run([path,*version_args],capture_output=True,text=True,
                              errors='replace',timeout=12,check=False)
        lines=(result.stdout+'\n'+result.stderr).strip().splitlines()
        return {'available':result.returncode==0,'path':path,
                'version':lines[0] if lines else None,'exit_code':result.returncode}
    except (OSError,subprocess.TimeoutExpired) as error:
        return {'available':False,'path':path,'version':None,
                'error':type(error).__name__}


def tcp_status(host,port):
    try:
        with socket.create_connection((host,port),timeout=3):
            pass
        return {'host':host,'port':port,'tcp_accepts':True,
                'note':'TCP alone does not verify the Blender MCP tool protocol.'}
    except OSError as error:
        return {'host':host,'port':port,'tcp_accepts':False,'error':type(error).__name__}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--blender',help='Blender executable; overrides BLENDER_PATH.')
    parser.add_argument('--ffmpeg',help='FFmpeg executable; otherwise PATH.')
    parser.add_argument('--ffprobe',help='ffprobe executable; otherwise PATH.')
    parser.add_argument('--json',action='store_true',help='Emit machine-readable report.')
    parser.add_argument('--probe-mcp',action='store_true',help='Optional TCP check, no scene changes.')
    parser.add_argument('--mcp-host',default='127.0.0.1')
    parser.add_argument('--mcp-port',type=int,default=9876)
    parser.add_argument('--probe-network',action='store_true',help='Optional TLS-port reachability only; no API request.')
    args=parser.parse_args(argv)
    if not 1<=args.mcp_port<=65535:
        parser.error('--mcp-port must be between 1 and 65535')
    tools={
        'blender':tool_status(find_blender(args.blender),['--version']),
        'ffmpeg':tool_status(executable(args.ffmpeg or 'ffmpeg'),['-version']),
        'ffprobe':tool_status(executable(args.ffprobe or 'ffprobe'),['-version']),
    }
    report={'python':platform.python_version(),'python_executable':sys.executable,
            'system':platform.system(),'tools':tools,
            'optional':{'uvx_found':bool(shutil.which('uvx')),
                        'codex_cli_found':bool(shutil.which('codex')),
                        'elevenlabs_key_configured':bool(os.environ.get('ELEVENLABS_API_KEY'))},
            'network':'not checked','mcp':'not checked'}
    if args.probe_mcp:
        report['mcp']=tcp_status(args.mcp_host,args.mcp_port)
    if args.probe_network:
        report['network']=tcp_status('api.elevenlabs.io',443)
    report['ready_for_stills']=tools['blender']['available']
    report['ready_for_video']=report['ready_for_stills'] and tools['ffmpeg']['available']
    report['ready_for_export_verification']=report['ready_for_video'] and tools['ffprobe']['available']
    # Compatibility alias: a local PNG render needs Blender, not FFmpeg.
    report['ready_for_local_render']=report['ready_for_stills']
    if args.json:
        print(json.dumps(report,ensure_ascii=False,indent=2))
    else:
        print('Local cartoon studio check')
        print('Python:',report['python'])
        for name,data in tools.items():
            print(name+':',data.get('version') or 'not found / not executable')
            if data['path']:
                print('  '+data['path'])
        print('ElevenLabs key:', 'configured (hidden)' if report['optional']['elevenlabs_key_configured'] else 'not configured; local renders still work')
        print('PNG/still rendering ready:',report['ready_for_stills'])
        print('Video encoding ready:',report['ready_for_video'])
        print('Export metadata verification ready:',report['ready_for_export_verification'])
        if args.probe_mcp:
            print('MCP TCP accepts:',report['mcp']['tcp_accepts'],'(protocol not verified)')
        if args.probe_network:
            print('ElevenLabs TCP reachable:',report['network']['tcp_accepts'],'(no paid API call)')
    return 0 if report['ready_for_stills'] else 1


if __name__=='__main__':
    raise SystemExit(main())
