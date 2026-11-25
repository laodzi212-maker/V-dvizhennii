#!/usr/bin/env python3
"""Карта-картинка маршрута (PNG). Факты из facts.json. Схема, не навигация.
python3 build_map.py  -> map_story.png (1080x1920), map_post.png (1080x1350)"""
import json, subprocess, sys
from pathlib import Path
here=Path(__file__).resolve().parent
F=json.loads((here.parent/"facts"/"facts.json").read_text(encoding="utf-8"))
t=next(x for x in F["trips"] if x["id"]=="kullu")
months={"10":"октября"}
d1,d2=t["dates"]; dates=f'{int(d1[:2])}–{int(d2[:2])} {months[d2[3:]]} 2027'
# только долина Куллу (Спити, Кей, Данкар не ездим)
pts=[("Куллу",31.96,77.11,"l"),("Наггар",32.12,77.17,"r"),("Маникаран",32.03,77.35,"r"),("Биджли Махадев",31.89,77.15,"r")]
lat0,lat1,lon0,lon1=31.80,32.20,76.95,77.50
def xy(a,b,W,H): return ((b-lon0)/(lon1-lon0)*W,(lat1-a)/(lat1-lat0)*H)
def page(W,H,mapH,top):
    P=[xy(a,b,W-240,mapH) for _,a,b,_ in pts]; P=[(x+120,y) for x,y in P]
    order=[0,1,2,3] ; 
    d="M"+" L".join(f"{P[i][0]:.0f},{P[i][1]:.0f}" for i in order)
    dots="".join(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="13" fill="#F2E9D8" stroke="#C8553D" stroke-width="5"/>' for x,y in P)
    lab="".join(f'<text x="{x+(28 if s=="r" else -28):.0f}" y="{y+10:.0f}" text-anchor="{"start" if s=="r" else "end"}">{n}</text>' for (n,_,_,s),(x,y) in zip(pts,P))
    return f'''<!doctype html><meta charset=utf-8><style>
*{{margin:0;box-sizing:border-box}}body{{width:{W}px;height:{H}px;background:linear-gradient(180deg,#26333D,#17202A);color:#F2E9D8;font-family:Montserrat,sans-serif;position:relative;overflow:hidden}}
.k{{position:absolute;left:90px;top:{top}px;font-size:30px;letter-spacing:.26em;text-transform:uppercase;color:#C9A66B}}
h1{{position:absolute;left:90px;top:{top+50}px;width:900px;font:600 104px/1.05 Lora,serif}}
svg{{position:absolute;left:0;top:{top+330}px}}svg text{{font-size:36px;fill:#F2E9D8;font-weight:500}}
.e{{position:absolute;left:90px;bottom:{ 150 if H>1500 else 70}px;width:900px}}.e .a{{font:600 64px/1.1 Lora,serif}}.e .b{{font-size:38px;color:#C9A66B;margin-top:16px}}.e .c{{font-size:36px;margin-top:8px}}
</style><div class=k>Гималаи в движении</div><h1>Осень в долине Куллу</h1>
<svg width="{W}" height="{mapH+40}" viewBox="0 0 {W} {mapH+40}">
<path d="M0,{mapH-60} L150,{mapH-170} L290,{mapH-110} L420,{mapH-260} L560,{mapH-170} L700,{mapH-320} L840,{mapH-190} L960,{mapH-280} L{W},{mapH-200} L{W},{mapH+40} L0,{mapH+40}Z" fill="#2E3E4A" opacity=".6"/>
<path d="M0,{mapH-10} L180,{mapH-90} L330,{mapH-40} L500,{mapH-130} L660,{mapH-60} L820,{mapH-140} L{W},{mapH-70} L{W},{mapH+40} L0,{mapH+40}Z" fill="#364A58" opacity=".7"/>
<path d="{d}" fill="none" stroke="#C8553D" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="2 18"/>
{dots}{lab}</svg>
<div class=e><div class=a>Долина Куллу</div><div class=b>{dates}</div><div class=c>{t["link"]} · кодовое слово {t["code"]}</div></div>'''
for name,W,H,mh,top in (("map_story",1080,1920,820,260),("map_post",1080,1350,560,120)):
    h=here/f"{name}.html"; h.write_text(page(W,H,mh,top),encoding="utf-8")
    subprocess.run(["google-chrome","--headless","--no-sandbox","--disable-gpu",f"--window-size={W},{H}",f"--screenshot={here/name}.png",f"file://{h}"],capture_output=True,timeout=60)
print("ok",dates)
