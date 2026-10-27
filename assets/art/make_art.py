import math, random, json, base64, io, os
from PIL import Image, ImageDraw
import os
OUT=os.path.dirname(os.path.abspath(__file__)) + '/'
S=2  # export scale
P={'.':None,'K':(26,16,48),'W':(243,236,220),'w':(190,180,165),'R':(255,77,61),'r':(170,40,45),
   'C':(95,227,255),'c':(40,140,180),'O':(255,138,61),'Y':(255,200,87),'V':(180,140,255),'v':(105,75,185),
   'L':(184,255,95),'l':(90,165,45),'B':(255,255,255),'G':(90,95,122),'g':(50,52,75),'D':(110,20,40)}
def rgba(k): c=P[k]; return (0,0,0,0) if c is None else c+(255,)
def from_rows(rows, mirror=False, odd=False):
    if mirror:
        rows=[r+(r[:-1] if odd else r)[::-1] for r in rows]
    w=len(rows[0]); assert all(len(r)==w for r in rows), [len(r) for r in rows]
    im=Image.new('RGBA',(w,len(rows)))
    for y,r in enumerate(rows):
        for x,ch in enumerate(r): im.putpixel((x,y),rgba(ch))
    return im
def outline(im, col='K'):
    o=im.copy(); w,h=im.size; px=im.load()
    for y in range(h):
        for x in range(w):
            if px[x,y][3]==0 and any(0<=x+dx<w and 0<=y+dy<h and px[x+dx,y+dy][3] and px[x+dx,y+dy][:3]!=P[col] for dx,dy in((1,0),(-1,0),(0,1),(0,-1))):
                o.putpixel((x,y),rgba(col))
    return o
F={}  # name -> 1x image
# ---- player (16x20), 2 exhaust frames
body=[".......K","......KW","......KW",".....KWC",".....KWC",".....KWc","....KWWW","...KRWWW",
      "..KRRWWW",".KRRRWWR","KRRRrWWR","KRRrKWWR","KRrK.KWR","KrK..KWW","KK...KwW",".....Kww"]
for i,fl in enumerate([["......KY","......OY","......RO",".......R"],["......KY","......YB","......OY","......RO"]]):
    F[f'player_{i}']=from_rows(body+fl,mirror=True)
# ---- enemy 1 violet dart (14x13)
F['e1']=from_rows(["KKKKKKK","KvVVVVV",".KvVVVV",".KvVWWW","..KvVWB","..KvVVV","...KvVV","...KvVV","....KvV","....KOV",".....KV",".....KK","......K"],mirror=True)
# ---- enemy 2 lime gunship (17x11)
F['e2']=from_rows(["......KKK","....KKLLL","..KKLLLLL","KKLLLLLLL","KLLlCCLLL","KLLlCBLLL","KLLLLLLLL","KlLLLLLLl","KlKllllll","KK.KlOlKK",".....KKK."],mirror=True,odd=True)
# ---- enemy 3 spinning disc (16x16), 4 frames
def disc(theta):
    im=Image.new('RGBA',(16,16)); px=im.load()
    for y in range(16):
        for x in range(16):
            dx,dy=x-7.5,y-7.5; d=math.hypot(dx,dy)
            if d<=7.6:
                k='O'
                if d>5.8 and (dx+dy)>4: k='r'
                elif d>5.8 and (dx+dy)<-6: k='Y'
                if d<4.2: k='c' if d>3.2 else 'C'
                if d<1.8: k='R'
                if d<0.9: k='B'
                px[x,y]=rgba(k)
    for j in range(4):
        a=theta+j*math.pi/2; x=round(7.5+6.3*math.cos(a)); y=round(7.5+6.3*math.sin(a))
        for xx,yy in((x,y),(x+1,y),(x,y+1),(x+1,y+1)):
            if 0<=xx<16 and 0<=yy<16 and px[xx,yy][3]: px[xx,yy]=rgba('K' if (xx,yy)!=(x,y) else 'Y')
    return outline(im)
for i in range(4): F[f'e3_{i}']=disc(i*math.pi/8)
# ---- boss (60x42): draw left half, mirror, shade, outline
def boss(flash=False):
    h=Image.new('RGBA',(30,42)); d=ImageDraw.Draw(h)
    d.polygon([(30,1),(18,6),(4,10),(1,18),(1,28),(6,30),(16,30),(30,30)],fill=rgba('R'))      # hull
    d.polygon([(1,28),(8,30),(14,40),(10,41),(4,34)],fill=rgba('r'))                       # left claw
    d.polygon([(16,30),(30,30),(30,34),(22,40),(18,40)],fill=rgba('r'))                     # inner fin
    d.rectangle([2,18,28,20],fill=rgba('r'))                                               # panel line
    d.rectangle([8,12,18,16],fill=rgba('W')); d.rectangle([9,13,12,14],fill=rgba('B'))     # eyes
    d.rectangle([24,14,30,26],fill=rgba('c')); d.rectangle([25,15,30,25],fill=rgba('C'))   # core
    d.rectangle([27,17,30,20],fill=rgba('B'))
    for x in (6,12,18): d.rectangle([x,23,x+2,27],fill=rgba('K'))                          # vents
    d.rectangle([5,30,8,32],fill=rgba('O')); d.point((6,33),fill=rgba('Y'))                 # guns
    d.line([(18,6),(4,10)],fill=rgba('Y'))
    full=Image.new('RGBA',(60,42)); full.paste(h,(0,0)); full.paste(h.transpose(Image.FLIP_LEFT_RIGHT),(30,0))
    if flash:
        px=full.load()
        for y in range(42):
            for x in range(60):
                if px[x,y][3]: px[x,y]=(255,255,255,255) if px[x,y][:3]!=P['K'] else px[x,y]
    return outline(full)
F['boss']=boss(); F['boss_hit']=boss(True)
# ---- bullets
F['shot']=from_rows(["BB","BB","CC","CC","CC","cc","cc"])
F['eshot']=from_rows([".OYO.","OYBYO","YBBBY","OYBYO",".OYO."])
F['eshot_boss']=from_rows([".rRr.","rROBr","ROBOR","rRORr",".rRr."])
# ---- power-ups (11x11)
F['p_gun']=from_rows([".KKKKKKKKK.","KBBYYYYYYYK","KBYYYKYYYOK","KYYYYKYYYOK","KYYYYKYYYOK","KYKKKKKKKOK","KYYYYKYYYOK","KYYYYKYYYOK","KYYYYKYYYOK","KYOOOOOOOOK",".KKKKKKKKK."])
F['p_shield']=from_rows(["...KKKKK...","..KCCCCCK..",".KCBBCCCCK.","KCBCCCCCCcK","KCCCcccCCcK","KCCcCBCcCcK","KCCCcccCCcK","KCCCCCCCCcK",".KCCCCCCcK.","..KcccccK..","...KKKKK..."])
F['p_life']=from_rows(["...........",".KKK...KKK.","KRBRK.KRRRK","KBRRRKRRRrK","KRRRRRRRRrK","KRRRRRRRRrK",".KRRRRRRrK.","..KRRRRrK..","...KRRrK...","....KrK....",".....K....."])
# ---- explosion (16x16) x6
rng=random.Random(7)
for i in range(6):
    im=Image.new('RGBA',(16,16)); px=im.load(); r=2.5+i*1.2
    for y in range(16):
        for x in range(16):
            d=math.hypot(x-7.5,y-7.5)+rng.uniform(-0.9,0.9)
            if d<r:
                t=d/r+i*0.17
                k='B' if t<0.35 else 'Y' if t<0.6 else 'O' if t<0.85 else 'R' if t<1.05 else 'G' if t<1.3 else 'g'
                if i>=3 and d<r*(i-2)/4: continue   # hollow centre as it fades
                if i==5 and rng.random()<0.45: continue
                px[x,y]=rgba(k)
    F[f'boom_{i}']=im
# ---- v2: Penyelam (type 4, 12x22 -> 24x44): idle, warn (blink before dive), dive (long tail)
P.update({'M':(255,80,190),'m':(150,30,115),'p':(255,170,225)})
pbody=["KK...K","KmK.KM","KmMKMM",".KmMMp",".KmMMp","..KmMM","..KMMW","..KMMB","...KMM","...KMM","....KM","....KM",".....K","......"]
ptail_idle=["......"]*4+[".....m",".....m",".....M",".....M"]
ptail_dive=[".....m",".....m",".....M","....mM",".....p","....mp",".....B","....MB"]
F['penyelam']=from_rows(ptail_idle+pbody,mirror=True)
F['penyelam_warn']=from_rows([r.translate(str.maketrans('Mmp','BpB')) for r in ptail_idle+pbody],mirror=True)
F['penyelam_dive']=from_rows(ptail_dive+pbody,mirror=True)
# ---- v2: ring-pattern boss bullet (10x10), violet so it reads apart from the fan shots
F['eshot_ring']=from_rows([".vVv.","vVBVv","VBBBV","vVBVv",".vVv."])
# ---- v2: boss rage frame (red tint), alternate with 'boss' every ~120 ms under 50% HP
def rage(im):
    o=im.copy(); px=o.load()
    for y in range(o.height):
        for x in range(o.width):
            r,g,b,a=px[x,y]
            if a and (r,g,b)!=P['K']: px[x,y]=(min(255,r//2+140),g//3,b//3,a)
    return o
F['boss_rage']=rage(F['boss'])
# ---- tiny particle and star
F['px']=from_rows(["BB","BB"]); F['star']=from_rows([".B.","BBB",".B."])
# ---- backgrounds (240x400 native -> 480x800)
BW,BH=240,400
bayer=[[0,8,2,10],[12,4,14,6],[3,11,1,9],[15,7,13,5]]
sky=Image.new('RGBA',(BW,BH)); px=sky.load()
stops=[(0,(11,13,31)),(0.55,(22,14,44)),(0.82,(70,18,46)),(1,(150,36,40))]
def lerp(a,b,t): return tuple(round(a[i]+(b[i]-a[i])*t) for i in range(3))
levels=[]
for i in range(len(stops)-1):
    for s in range(6): levels.append((stops[i][0]+(stops[i+1][0]-stops[i][0])*s/6, lerp(stops[i][1],stops[i+1][1],s/6)))
levels.append(stops[-1])
for y in range(BH):
    t=y/(BH-1)
    for x in range(BW):
        j=max(i for i,(p,_) in enumerate(levels) if p<=t); j2=min(j+1,len(levels)-1)
        span=(levels[j2][0]-levels[j][0]) or 1; f=(t-levels[j][0])/span
        px[x,y]=(levels[j2][1] if f*16>bayer[y%4][x%4]+0.5 else levels[j][1])+(255,)
F_bg={'bg_sky':sky}
st=Image.new('RGBA',(BW,BH)); px=st.load(); rng=random.Random(3)
# faint red nebula wisps, periodic in y so the layer tiles vertically
for y in range(BH):
    for x in range(BW):
        n=math.sin(x*0.045+math.sin(y*2*math.pi/BH*2)*2)+math.sin(y*2*math.pi/BH*3+x*0.02)*0.8+math.sin((x+y)*0.03)*0.0
        v=(n+1.8)/3.6
        if v>0.78 and (v-0.78)*60>bayer[y%4][x%4]: px[x,y]=(90,22,52,140)
        if v>0.9 and (v-0.9)*80>bayer[y%4][x%4]: px[x,y]=(150,40,60,170)
for _ in range(170):
    x,y=rng.randrange(BW),rng.randrange(BH); b=rng.choice([(120,130,170),(180,190,230),(243,236,220)])
    px[x,y]=b+(255,)
for _ in range(14):
    x,y=rng.randrange(1,BW-1),rng.randrange(BH); c=rng.choice([(255,255,255),(95,227,255),(255,200,87)])
    for dx,dy in((0,0),(1,0),(-1,0),(0,1),(0,-1)): px[x+dx,(y+dy)%BH]=c+(255 if (dx,dy)==(0,0) else 150,)
F_bg['bg_stars']=st
# ---- export individual PNGs
up=lambda im,s=S: im.resize((im.width*s,im.height*s),Image.NEAREST)
for n,im in {**F,**F_bg}.items(): up(im).save(OUT+'png/'+n+'.png')
# ---- pack atlas (simple shelf packer) at 2x, 2px padding
items=sorted(F.items(),key=lambda kv:-kv[1].height); W=256; x=y=shelf=0; pos={}; pad=2
for n,im in items:
    w,h=im.width*S,im.height*S
    if x+w>W: x=0; y+=shelf+pad; shelf=0
    pos[n]=(x,y,w,h); x+=w+pad; shelf=max(shelf,h)
H=y+shelf; H=1<<(H-1).bit_length()
sheet=Image.new('RGBA',(W,H))
for n,(x,y,w,h) in pos.items(): sheet.paste(up(F[n]),(x,y))
sheet.save(OUT+'sprites.png',optimize=True)
atlas={'frames':{n:{'frame':{'x':x,'y':y,'w':w,'h':h},'rotated':False,'trimmed':False,'spriteSourceSize':{'x':0,'y':0,'w':w,'h':h},'sourceSize':{'w':w,'h':h}} for n,(x,y,w,h) in pos.items()},
       'meta':{'app':'Langit Merah art','image':'sprites.png','format':'RGBA8888','size':{'w':W,'h':H},'scale':'1'}}
json.dump(atlas,open(OUT+'sprites.json','w'),indent=1)
# ---- embeddable JS for single-file artifact
def b64(p): return 'data:image/png;base64,'+base64.b64encode(open(p,'rb').read()).decode()
with open(OUT+'sprites-embed.js','w') as f:
    f.write('// Langit Merah art, embedded so the single-file game needs no extra requests.\n')
    f.write('window.LM_ART = '+json.dumps({'sheet':b64(OUT+'sprites.png'),'atlas':atlas,'bg_sky':b64(OUT+'png/bg_sky.png'),'bg_stars':b64(OUT+'png/bg_stars.png')})+';\n')
# ---- preview
pv=Image.new('RGBA',(960,820),(11,13,31,255)); pv.paste(up(sky),(0,10)); pv.alpha_composite(up(st),(0,10))
def put(n,x,y,s=3):
    im=up(F[n],s); pv.alpha_composite(im,(x-im.width//2,y-im.height//2))
put('boss',240,140,3); put('e1',110,330); put('e2',240,320); put('e3_0',370,330)
put('eshot_boss',200,250); put('eshot_boss',240,260); put('eshot_boss',280,250); put('eshot',300,400)
put('p_gun',120,520); put('p_shield',240,540); put('p_life',360,520)
put('penyelam_dive',420,620); put('player_1',240,700); put('shot',228,610); put('shot',252,610); put('boom_2',380,430)
# sheet on right
ox=510; d=ImageDraw.Draw(pv); d.rectangle([ox-10,0,960,820],fill=(20,22,42,255))
x,y=ox,20; shelf=0
for n in F:
    im=up(F[n],2 if F[n].width<40 else 1) if False else up(F[n],3 if F[n].width<30 else 2)
    if x+im.width>950: x=ox; y+=shelf+14; shelf=0
    pv.alpha_composite(im,(x,y)); x+=im.width+12; shelf=max(shelf,im.height)
pv.convert('RGB').save(OUT+'preview.png')
print(W,H,len(F),'frames')
