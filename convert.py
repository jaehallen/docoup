import os
import contextlib
import subprocess
import shlex
import re
import time

DIR_CONVERTED_FILE = './converted'
def info(filename):
    isEval = lambda s : bool(re.match('(\d+[.\d]+)', s)) or bool(re.match('(\d+\/\d+)', s)) and not s.endswith('/0')
    ff = f"ffprobe -v error -select_streams v:0 -show_entries format=duration:stream=avg_frame_rate -of csv=nk=0:p=0 '{filename}'"
    o = subprocess.run(shlex.split(ff), stdout=subprocess.PIPE, encoding='UTF-8').stdout.strip()

    reFps = re.search('avg_frame_rate=(\d+\/\d+)',o)
    reDur = re.search('duration=(\d+[.\d]+)',o)
    fps = reFps.group(1) if reFps else ''
    dur = reDur.group(1) if reDur else ''

    return (eval(dur) if isEval(dur) else 0, eval(fps) if isEval(fps) else 0)

def _stdout(proc,dur,stream='stdout'):
    stream = getattr(proc, stream)
    with contextlib.closing(stream):
        while proc.poll() is None:
            line = stream.readline()

            if not line:
                break

            speed = re.search('(?<=speed=)[\s]*\d+(\.\d)?', line)
            ot = re.search('(\d+:)+\d+', line)
            out = ''

            if speed and ot:
                s = eval(speed.group(0).strip())
                cot = ot.group(0).strip()
                hr, min, sec = [int(i) for i in cot.split(':')]
                t = hr*3600 + min*60 + sec
                est = (dur - t)/s
                clock = time.strftime('%H:%M:%S', time.gmtime(est))

                out = f'Estimated Time: {clock}       Converted Duration: {cot}'

            yield out if out else line

def convert_file(filename, vres):
    dur, fps = info(filename)
    res = vres if vres.isnumeric() else 480
    ext = '.mp4' if fps > 1 and vres.isnumeric() else '.mp3'
    vOpt = f"-vf {'' if fps <= 24 else 'fps=fps=24,'}format=yuv420p,'scale=w=-2:h=trunc(min(ih\,{res})/2)*2' -c:v libx264 -crf 28 -c:a aac -b:a 64k -ac 1"
    aOpt = f"-ac 1 -codec:a libmp3lame -qscale:a 6"
    opt = vOpt if ext == '.mp4'  else aOpt

    outFilename = os.path.basename(filename).rsplit('.')[0] + ext
    outputFile = os.path.join(DIR_CONVERTED_FILE, outFilename)
    cmd = f"ffmpeg -loglevel error -stats -i '{filename}' {opt} -preset veryfast -y '{outputFile}'"

    if not os.path.exists(DIR_CONVERTED_FILE):
        os.mkdir(DIR_CONVERTED_FILE)

    print(f'Converting: {filename} -> {outputFile}' )
    if dur > 0:
        proc = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=False, encoding='UTF-8' )

        for line in _stdout(proc, dur):
            print('\r',line, end='')
        print('\n')
        return outputFile
    else:
        raise Exception('Failed to convert, not a media file')
