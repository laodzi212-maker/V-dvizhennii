#!/usr/bin/env python3
"""Русская речь -> слова с таймингами -> SRT (до 6 слов в реплике) + ASS (безопасные зоны Instagram).
Офлайн: sherpa-onnx + GigaAM v2. Пример: python3 transcribe.py voice.wav out/name"""
import sys, re, wave, numpy as np, sherpa_onnx
M="/home/claude/work/models/sherpa-onnx-nemo-ctc-giga-am-v2-russian-2025-04-19/"
wav, out = sys.argv[1], sys.argv[2]
MAXW=6
w=wave.open(wav); sr=w.getframerate(); ch=w.getnchannels()
x=np.frombuffer(w.readframes(w.getnframes()),dtype=np.int16).astype(np.float32)/32768
if ch>1: x=x.reshape(-1,ch).mean(1)
if sr!=16000:
    import numpy as np
    n=int(len(x)*16000/sr); x=np.interp(np.linspace(0,len(x)-1,n),np.arange(len(x)),x).astype(np.float32); sr=16000
rec=sherpa_onnx.OfflineRecognizer.from_nemo_ctc(model=M+"model.int8.onnx",tokens=M+"tokens.txt",num_threads=2)
words=[]
def run(seg,off):
    s=rec.create_stream(); s.accept_waveform(sr,seg); rec.decode_stream(s); r=s.result
    toks,ts=list(r.tokens),list(r.timestamps)
    cur,start,last=None,None,0
    for t,tm in zip(toks,ts):
        if t==" ":
            if cur: words.append((cur,start+off,tm+off)); cur=None
            continue
        if cur is None: cur,start=t,tm
        else: cur+=t
        last=tm
    if cur: words.append((cur,start+off,last+0.3+off))
# разбиваем по паузам по 30 с (для длинных файлов; для рилсов обычно один кусок)
CH=30*sr
for i in range(0,len(x),CH): run(x[i:i+CH], i/sr)
# глоссарий: исправляем имена и места (ASR их коверкает)
import difflib, json, pathlib
G=json.loads((pathlib.Path(__file__).resolve().parent/"glossary.json").read_text(encoding="utf-8"))
def norm(t): return t.lower().replace(" ","")
alias={k:v for k,v in G["alias"].items()}
terms=G["terms"]
fixed=[];i=0
while i<len(words):
    done=False
    for n in (3,2,1):
        if i+n>len(words): continue
        chunk=" ".join(w[0] for w in words[i:i+n])
        if chunk in alias: rep=alias[chunk]
        else:
            best=max(terms,key=lambda t:difflib.SequenceMatcher(None,norm(chunk),norm(t)).ratio())
            rep=best if difflib.SequenceMatcher(None,norm(chunk),norm(best)).ratio()>=0.78 and len(norm(chunk))>=4 else None
        if rep:
            fixed.append((rep,words[i][1],words[i+n-1][2])); i+=n; done=True; break
    if not done: fixed.append(words[i]); i+=1
words=fixed
# реплики: <=6 слов, разрыв по знакам и паузам >0.5 с
cues=[];cur=[]
for wd in words:
    if cur and (len(" ".join(w[0] for w in cur).split())+len(wd[0].split())>MAXW or wd[1]-cur[-1][2]>0.5): cues.append(cur);cur=[]
    cur.append(wd)
if cur: cues.append(cur)
def ts_srt(t): h=int(t//3600);m=int(t%3600//60);s=t%60; return f"{h:02}:{m:02}:{int(s):02},{int(s%1*1000):03}"
def ts_ass(t): h=int(t//3600);m=int(t%3600//60);s=t%60; return f"{h}:{m:02}:{s:05.2f}"
srt=[];ass=[]
for i,c in enumerate(cues,1):
    st,en=c[0][1],c[-1][2]+0.15
    if i<len(cues): en=min(en,cues[i][0][1]-0.02)
    txt=" ".join(w[0] for w in c)
    srt.append(f"{i}\n{ts_srt(st)} --> {ts_srt(en)}\n{txt}\n")
    ass.append(f"Dialogue: 0,{ts_ass(st)},{ts_ass(en)},Reels,,0,0,0,,{txt}")
open(out+".srt","w",encoding="utf-8").write("\n".join(srt))
hdr="""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Reels,Roboto,58,&H00D8E9F2,&H00D8E9F2,&H00332A1F,&H80000000,1,0,0,0,100,100,0,0,1,4,0,2,90,90,440,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
open(out+".ass","w",encoding="utf-8").write(hdr+"\n".join(ass)+"\n")
print(" ".join(w[0] for w in words)); print(len(cues),"реплик")
