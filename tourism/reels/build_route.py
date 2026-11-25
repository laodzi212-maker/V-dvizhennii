#!/usr/bin/env python3
"""Генератор анимации маршрута: берёт поездку из facts.json, пишет route/index.html"""
import json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
facts = json.loads((here.parent/"facts"/"facts.json").read_text(encoding="utf-8"))
trip = next(t for t in facts["trips"] if t["id"]=="kullu")
d1,d2 = trip["dates"]
price = f'{trip["price_rub"]:,}'.replace(","," ")
pts = [("Куллу",31.96,77.11,"l"),("Наггар",32.12,77.17,"r"),("Чандра Тал",32.48,77.61,"r"),
       ("Кей",32.23,78.01,"r"),("Данкар",32.10,78.22,"l"),("Маникаран",32.03,77.35,"l"),("Биджли Махадев",31.89,77.15,"r")]
W,H=640,700; lat0,lat1,lon0,lon1=31.75,32.65,76.95,78.35
import math
def xy(lat,lon):
    return ( 150+(lon-lon0)/(lon1-lon0)*W , (lat1-lat)/(lat1-lat0)*H )
P=[xy(a,b) for _,a,b,_ in pts]
# сглаженный путь (Catmull-Rom -> Bezier)
def path(P):
    d=f"M{P[0][0]:.1f},{P[0][1]:.1f}"
    for i in range(len(P)-1):
        p0=P[max(i-1,0)];p1=P[i];p2=P[i+1];p3=P[min(i+2,len(P)-1)]
        c1=(p1[0]+(p2[0]-p0[0])/8,p1[1]+(p2[1]-p0[1])/8)
        c2=(p2[0]-(p3[0]-p1[0])/8,p2[1]-(p3[1]-p1[1])/8)
        d+=f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d
D=path(P)
months={"04":"апреля","05":"мая","10":"октября","07":"июля","09":"сентября","12":"декабря"}
def human(a,b):
    da,ma=a.split(".");db,mb=b.split(".")
    return f"{int(da)}–{int(db)} {months[mb]}" if ma==mb else f"{int(da)} {months[ma]} — {int(db)} {months[mb]}"
dates=human(d1,d2)+" 2027"
dots="";labels="";tl=""
n=len(pts); t0=1.2; span=6.6
for i,((name,_,_,side),(x,y)) in enumerate(zip(pts,P)):
    t=t0+span*(i/(n-1))
    dots+=f'<circle id="d{i}" cx="{x:.1f}" cy="{y:.1f}" r="11" fill="#F2E9D8" stroke="#C8553D" stroke-width="4" opacity="0"/>\n'
    anchor="start" if side=="r" else "end"; dx=24 if side=="r" else -24
    labels+=f'<text id="t{i}" x="{x+dx:.1f}" y="{y+8:.1f}" text-anchor="{anchor}" opacity="0">{name}</text>\n'
    tl+=f'tl.to("#d{i}",{{opacity:1,attr:{{r:11}},duration:.25,ease:"back.out(3)"}},{t:.2f});tl.to("#t{i}",{{opacity:1,duration:.3}},{t+.05:.2f});\n'
html=f'''<!doctype html><html lang="ru" data-resolution="portrait"><head><meta charset="UTF-8"/>
<meta name="viewport" content="width=1080, height=1920"/>
<script src="vendor/gsap.min.js"></script>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:1080px;height:1920px;overflow:hidden;background:#1F2A33}}
#root{{position:relative;width:1080px;height:1920px;background:linear-gradient(180deg,#26333D 0%,#1F2A33 55%,#17202A 100%);font-family:"Roboto","DejaVu Sans",sans-serif;color:#F2E9D8}}
.kick{{position:absolute;left:90px;top:300px;font-size:34px;letter-spacing:.28em;text-transform:uppercase;color:#C9A66B}}
.h1{{position:absolute;left:90px;top:360px;width:900px;font-family:"Cormorant Garamond","DejaVu Serif",serif;font-size:112px;line-height:1.05;font-weight:600}}
svg{{position:absolute;left:90px;top:640px}}
svg text{{font-size:38px;fill:#F2E9D8;font-weight:500}}
.end{{position:absolute;left:90px;top:1420px;width:900px}}
.end .a{{font-family:"Cormorant Garamond","DejaVu Serif",serif;font-size:76px;font-weight:600;line-height:1.05}}
.end .b{{font-size:40px;margin-top:22px;color:#C9A66B}}
.end .c{{font-size:40px;margin-top:10px}}
</style></head><body>
<div id="root" data-composition-id="root" data-start="0" data-duration="12" data-width="1080" data-height="1920">
<div class="kick clip" data-start="0" data-duration="12" data-track-index="1" id="kick">Гималаи в движении</div>
<div class="h1 clip" data-start="0" data-duration="12" data-track-index="2" id="h1">Дорога к озеру Чандра Тал</div>
<svg class="clip" data-start="0" data-duration="12" data-track-index="3" width="900" height="700" viewBox="0 0 900 700">
<path d="M0,620 L120,520 L230,560 L330,430 L430,500 L540,360 L650,450 L760,330 L900,430 L900,700 L0,700Z" fill="#2E3E4A" opacity=".55"/>
<path d="M0,670 L150,590 L280,640 L420,560 L560,620 L700,520 L820,600 L900,560 L900,700 L0,700Z" fill="#364A58" opacity=".6"/>
<path id="route" d="{D}" fill="none" stroke="#C8553D" stroke-width="7" stroke-linecap="round" stroke-linejoin="round" />
{dots}{labels}
</svg>
<div class="end clip" data-start="0" data-duration="12" data-track-index="4" id="end" style="opacity:0">
<div class="a">Куллу и Лахаул</div><div class="b">{dates}</div>
<div class="c">{trip["link"]} · код {trip["code"]}</div></div>
</div>
<script>
window.__timelines=window.__timelines||{{}};
const R=document.getElementById("route");const L=R.getTotalLength();R.style.strokeDasharray=L;R.style.strokeDashoffset=L;
const tl=gsap.timeline({{paused:true}});
tl.from("#kick",{{opacity:0,y:20,duration:.6,ease:"power2.out"}},0.1);
tl.from("#h1",{{opacity:0,y:30,duration:.8,ease:"power3.out"}},0.3);
tl.to("#route",{{strokeDashoffset:0,duration:{span},ease:"none"}},{t0});
{tl}
tl.to("#end",{{opacity:1,duration:.7,ease:"power2.out"}},9.0);
window.__timelines["root"]=tl;
</script></body></html>'''
(here/"route"/"index.html").write_text(html,encoding="utf-8")
print("ok",dates,price,trip["link"],trip["code"])
