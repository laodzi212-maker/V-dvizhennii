#!/usr/bin/env python3
"""Голос Никиты -> готовый рилс 9:16 с субтитрами и финальной карточкой.
Пример: python3 make_reel.py kullu ~/voice_kullu.m4a [фон.jpg]
Шаги: звук -> wav -> субтитры (GigaAM) -> проверка фактов по тексту -> фон -> сборка mp4.
Если проверка фактов нашла ошибку (код 1), видео не собирается."""
import sys, os, json, subprocess, pathlib, textwrap
H=pathlib.Path(__file__).resolve().parent
KIT=H.parent
trip_id, audio = sys.argv[1], sys.argv[2]
bg = sys.argv[3] if len(sys.argv)>3 else None
facts=json.load(open(KIT/"facts/facts.json",encoding="utf-8"))
trip=next(t for t in facts["trips"] if t["id"]==trip_id)
out=H/"out"; out.mkdir(exist_ok=True)
base=str(out/trip_id)
def sh(*a,**k): subprocess.run(a,check=True,**k)
# 1. звук
sh("ffmpeg","-y","-loglevel","error","-i",audio,"-ac","1","-ar","16000",base+".wav")
# 2. субтитры
sh("python3",str(KIT/"subs/transcribe.py"),base+".wav",base)
# 3. проверка фактов по тому, что реально сказано
txt=" ".join(l for l in open(base+".srt",encoding="utf-8").read().splitlines() if l and not l.strip().isdigit() and "-->" not in l)
open(base+".txt","w",encoding="utf-8").write(txt)
r=subprocess.run(["python3",str(KIT/"facts/check_facts.py"),base+".txt"])
if r.returncode==1: sys.exit("СТОП: в голосе факт расходится с таблицей. Видео не собрано.")
dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",audio]).decode())
END=2.5; total=dur+END
# 4. фон
d=trip.get("dates"); dates=f"{d[0]}–{d[1]}" if d else ""
card=base+"_end.png"
html=f"""<html><body style="margin:0;width:1080px;height:1920px;background:#1F2A33;color:#F2E9D8;font-family:Georgia,serif;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center">
<div style="font-size:56px;color:#C9A66B;letter-spacing:.12em">{facts['brand']['name'].upper()}</div>
<div style="font-size:84px;width:900px;margin:60px 0 30px;line-height:1.1">{trip['name']}</div>
<div style="font-size:60px">{dates}</div>
<div style="font-size:54px;margin-top:80px;color:#C9A66B">кодовое слово {trip.get('code','')}</div>
<div style="font-size:50px;margin-top:20px">{trip.get('link', facts['brand']['site'])}</div></body></html>"""
open(base+"_end.html","w",encoding="utf-8").write(html)
sh("google-chrome","--headless","--no-sandbox","--disable-gpu","--hide-scrollbars","--window-size=1080,1920",f"--screenshot={card}","file://"+base+"_end.html",stderr=subprocess.DEVNULL)
if not bg: bg=card
# фон под голосом: медленный наезд
sh("ffmpeg","-y","-loglevel","error","-loop","1","-t",str(dur),"-i",bg,"-vf",
   f"scale=1188:2112:force_original_aspect_ratio=increase,crop=1188:2112,zoompan=z='min(zoom+0.0006,1.1)':d=1:s=1080x1920:fps=30,format=yuv420p",base+"_a.mp4")
sh("ffmpeg","-y","-loglevel","error","-loop","1","-t",str(END),"-i",card,"-vf","scale=1080:1920,fps=30,format=yuv420p",base+"_b.mp4")
open(base+"_list.txt","w").write(f"file '{base}_a.mp4'\nfile '{base}_b.mp4'\n")
sh("ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",base+"_list.txt","-c","copy",base+"_silent.mp4")
# 5. субтитры вшиты, звук добавлен
sh("ffmpeg","-y","-loglevel","error","-i",base+"_silent.mp4","-i",audio,"-vf",f"ass={base}.ass","-map","0:v","-map","1:a","-c:v","libx264","-preset","veryfast","-crf","21","-c:a","aac","-b:a","160k","-shortest",base+"_reel.mp4")
print("ГОТОВО:",base+"_reel.mp4",f"{total:.1f} с")
