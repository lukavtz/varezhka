#!/usr/bin/env python3
"""ElevenLabs speech + character/word timing, using only Python's standard library.

The dry run never reads a key or opens a network connection. Live mode sends
one request, without automatic retries. API credentials are read from env only.
"""
from __future__ import annotations
import argparse
import base64
from datetime import datetime,timezone
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request


def word_timings(alignment):
    if not alignment:
        return []
    chars=alignment.get('characters',[])
    starts=alignment.get('character_start_times_seconds',[])
    ends=alignment.get('character_end_times_seconds',[])
    if not (len(chars)==len(starts)==len(ends)):
        raise ValueError('Alignment arrays have different lengths.')
    words=[];text=[];start=None;end=None
    for char,a,b in zip(chars,starts,ends):
        if not isinstance(char,str) or not isinstance(a,(int,float)) or not isinstance(b,(int,float)) or not math.isfinite(a) or not math.isfinite(b) or a<0 or b<a:
            raise ValueError('Invalid character timing data.')
        if char.isspace():
            if text:
                words.append({'text':''.join(text),'start':start,'end':end})
                text=[];start=None;end=None
        else:
            if start is None:
                start=a
            end=b;text.append(char)
    if text:
        words.append({'text':''.join(text),'start':start,'end':end})
    return words


def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp_name=None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent,prefix=path.name+'.',suffix='.tmp',delete=False) as temp:
            temp_name=temp.name
            temp.write(data)
        os.replace(temp_name,path)
    finally:
        if temp_name and Path(temp_name).exists():
            Path(temp_name).unlink()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--voice-id',required=True,help='Your own accessible ElevenLabs voice ID.')
    parser.add_argument('--model',default='eleven_multilingual_v2')
    parser.add_argument('--text-file',type=Path,required=True,help='UTF-8 spoken text for one character/clip.')
    parser.add_argument('--output',type=Path,required=True,help='Output .mp3 file.')
    parser.add_argument('--timings',type=Path,help='Alignment JSON; defaults beside output.')
    parser.add_argument('--key-env',default='ELEVENLABS_API_KEY',help='Name of key environment variable, never the key itself.')
    parser.add_argument('--dry-run',action='store_true',help='Validate locally; no network and no key read.')
    parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args(argv)
    try:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',args.key_env):
            raise ValueError('--key-env must be an environment variable name, not a secret value.')
        if not re.fullmatch(r'[A-Za-z0-9_-]+',args.voice_id) or args.voice_id.startswith('sk_'):
            raise ValueError('Use a voice ID in --voice-id, never an API key.')
        if not args.model.strip():
            raise ValueError('Model ID is empty.')
        text=args.text_file.read_text(encoding='utf-8-sig').strip()
        if not text:
            raise ValueError('Spoken text is empty.')
        if args.output.suffix.lower()!='.mp3':
            raise ValueError('--output must end with .mp3 (output format is mp3_44100_128).')
        timings=args.timings or args.output.with_suffix('.alignment.json')
        if args.output.resolve()==timings.resolve():
            raise ValueError('Audio and alignment need different output files.')
        if not args.overwrite and (args.output.exists() or timings.exists()):
            raise ValueError('An output file exists. Choose another name or use --overwrite.')
        url='https://api.elevenlabs.io/v1/text-to-speech/'+urllib.parse.quote(args.voice_id,safe='')+'/with-timestamps?output_format=mp3_44100_128'
        payload={'text':text,'model_id':args.model}
        if args.dry_run:
            print(json.dumps({'dry_run':True,'network_called':False,'key_read':False,
                'method':'POST','endpoint':url,'model':args.model,'text_characters':len(text),
                'output':str(args.output),'timings':str(timings),
                'request_fields':list(payload)},ensure_ascii=False,indent=2))
            return 0
        key=os.environ.get(args.key_env,'').strip()
        if not key:
            raise ValueError('API key environment variable is not set. Set it locally, then retry.')
        # Validate filesystem access before the single potentially billable call.
        args.output.parent.mkdir(parents=True,exist_ok=True)
        timings.parent.mkdir(parents=True,exist_ok=True)
        for directory in {args.output.parent,timings.parent}:
            with tempfile.NamedTemporaryFile(dir=directory,prefix='.voice-write-check-',delete=True):
                pass
        request=urllib.request.Request(url,data=json.dumps(payload,ensure_ascii=False).encode('utf8'),
            headers={'Content-Type':'application/json','xi-api-key':key},method='POST')
        with urllib.request.urlopen(request,timeout=90) as response:
            result=json.load(response)
        audio=base64.b64decode(result['audio_base64'],validate=True)
        if not audio:
            raise ValueError('The API returned empty audio.')
        basis='normalized_alignment' if result.get('normalized_alignment') else 'alignment'
        words=word_timings(result.get(basis))
        metadata={'provider':'ElevenLabs','model_id':args.model,'voice_id':args.voice_id,
                  'created_utc':datetime.now(timezone.utc).isoformat(),
                  'text_characters':len(text),'alignment_basis':basis,
                  'alignment':result.get('alignment'),
                  'normalized_alignment':result.get('normalized_alignment'),'words':words}
        atomic_write(args.output,audio)
        atomic_write(timings,json.dumps(metadata,ensure_ascii=False,indent=2).encode('utf8'))
        print(json.dumps({'audio':str(args.output),'timings':str(timings),
                          'word_count':len(words)},ensure_ascii=False))
        return 0
    except urllib.error.HTTPError as error:
        print('ElevenLabs HTTP error '+str(error.code)+'. Check voice access, model, credits and account settings. No automatic retry was made.',file=sys.stderr)
        return 2
    except (urllib.error.URLError,TimeoutError) as error:
        print('Network request did not complete. Its billing/result may be unknown; check account history before repeating. No automatic retry was made.',file=sys.stderr)
        return 3
    except (OSError,ValueError,KeyError,TypeError) as error:
        # These messages are local validation failures; never print request headers.
        print(str(error),file=sys.stderr)
        return 1


if __name__=='__main__':
    raise SystemExit(main())
