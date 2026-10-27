"""Generator audio Langit Merah (chiptune). Jalankan: python3 make_audio.py
Butuh numpy + ffmpeg (libvorbis, libmp3lame). Menulis musik dan SFX ke folder ini."""
import numpy as np, subprocess, os, wave

SR = 44100
OUT = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7)

def hz(n):  # nama nada -> frekuensi, mis. 'A4', 'C#5'
    names = {'C':0,'C#':1,'D':2,'D#':3,'E':4,'F':5,'F#':6,'G':7,'G#':8,'A':9,'A#':10,'B':11}
    return 440 * 2 ** ((names[n[:-1]] + 12 * (int(n[-1]) + 1) - 69) / 12)

def pulse(freq, n, duty=0.5, phase0=0.0):
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    ph = (phase0 + np.cumsum(f) / SR) % 1.0
    return np.where(ph < duty, 1.0, -1.0)

def tri(freq, n):
    f = np.broadcast_to(np.asarray(freq, float), (n,))
    ph = (0.25 + np.cumsum(f) / SR) % 1.0   # mulai dari 0, tanpa klik
    return 4 * np.abs(ph - 0.5) - 1  # 4-bit-ish triangle
def quant(x, steps=16): return np.round(x * steps / 2) / (steps / 2)

def noise(n, rate=SR, short=False):
    # noise NES-like: nilai acak ditahan selama SR/rate sampel
    hold = max(1, int(SR / rate))
    vals = rng.choice([-1.0, 1.0], size=n // hold + 2)
    if short: vals = np.tile(vals[:93], len(vals) // 93 + 1)[:len(vals)]
    return np.repeat(vals, hold)[:n]

def env(n, a=0.002, d=0.0, s=1.0, r=0.02, hold=None):
    t = np.arange(n) / SR
    e = np.ones(n)
    ai = int(a * SR); 
    if ai: e[:ai] = np.linspace(0, 1, ai)
    if d:
        di = int(d * SR); seg = slice(ai, min(n, ai + di))
        e[seg] = np.linspace(1, s, di)[:seg.stop - seg.start]; e[ai + di:] = s
    ri = int(r * SR)
    if ri and ri < n: e[-ri:] *= np.linspace(1, 0, ri)
    return e

# ---------------------------------------------------------------- MUSIK
BPM = 144
STEP = 60 / BPM / 4            # satu not 1/16
BAR = 16
def sec(steps): return int(round(steps * STEP * SR))

# Progresi (A minor): tiap bar satu akor
CH = {'Am':['A','C','E'], 'F':['F','A','C'], 'C':['C','E','G'], 'G':['G','B','D'],
      'Dm':['D','F','A'], 'E':['E','G#','B']}
ROOT = {'Am':'A2','F':'F2','C':'C3','G':'G2','Dm':'D3','E':'E2'}
prog_intro = ['Am','F','C','G']
prog_a = ['Am','F','C','G','Am','F','G','E']
prog_b = ['F','G','Am','Am','F','G','E','E']
prog = prog_intro + prog_a + prog_a + prog_b + prog_intro   # 32 bar
NBARS = len(prog)

# Melodi: daftar (nada|'-' sambung|'.' diam) per 1/16, ditulis per bar
def bars(s): return [b.split() for b in s.strip().split('|')]
mel_a = bars("""
A4 - - - C5 - E5 - D5 - C5 - B4 - A4 - |
F4 - - - A4 - C5 - D5 - E5 - F5 - - - |
E5 - - - D5 - C5 - G4 - - - C5 - D5 - |
D5 - - - B4 - G4 - B4 - D5 - G5 - F5 - |
E5 - - - A5 - - - G5 - E5 - C5 - E5 - |
F5 - - - E5 - D5 - C5 - A4 - C5 - - - |
D5 - - - E5 - F5 - G5 - - - F5 - D5 - |
E5 - - - - - - - G#4 - B4 - E5 - - - """)
mel_a2 = [list(b) for b in mel_a]
mel_a2[7] = "E5 - D5 - C5 - B4 - G#4 - - - E4 - - -".split()
mel_b = bars("""
A5 - G5 - F5 - - - C5 - F5 - A5 - - - |
B5 - A5 - G5 - - - D5 - G5 - B5 - - - |
C6 - - - B5 - A5 - E5 - - - A5 - - - |
C6 - B5 - A5 - G5 - E5 - D5 - C5 - B4 - |
A4 - C5 - F5 - - - A5 - - - F5 - C5 - |
B4 - D5 - G5 - - - B5 - - - G5 - D5 - |
G#5 - - - - - - - E5 - - - B4 - - - |
E5 - - - D5 - - - C5 - - - B4 - - - """)
melody = [['.']*16]*4 + mel_a + mel_a2 + mel_b + [['.']*16]*4
assert len(melody) == NBARS and all(len(b) == 16 for b in melody)

N = sec(NBARS * BAR)
TAIL = sec(16)
mix_lead = np.zeros(N + TAIL); mix_arp = np.zeros(N + TAIL)
mix_bass = np.zeros(N + TAIL); mix_drum = np.zeros(N + TAIL)

def place(buf, start, sig): buf[start:start + len(sig)] += sig

# Lead: pulse 25% dengan vibrato tunda
for bi, bar in enumerate(melody):
    i = 0
    while i < 16:
        nt = bar[i]
        if nt in '.-': i += 1; continue
        ln = 1
        while i + ln < 16 and bar[i + ln] == '-': ln += 1
        n = sec(ln) - 40
        t = np.arange(n) / SR
        vib = 1 + 0.006 * np.sin(2 * np.pi * 5.5 * t) * np.clip((t - 0.15) * 5, 0, 1)
        s = pulse(hz(nt) * vib, n, 0.25) * env(n, 0.003, 0.12, 0.65, 0.03)
        place(mix_lead, sec(bi * BAR + i), s)
        # gema sederhana (echo channel ala NES)
        place(mix_lead, sec(bi * BAR + i + 3), 0.3 * s)
        i += ln

# Arpeggio: pulse 12.5%, nada akor bergantian tiap 1/16, oktaf 4/5
for bi, c in enumerate(prog):
    notes = [f"{c_}{4}" for c_ in CH[c]] + [f"{CH[c][0]}5"]
    vol = 0.55 if bi < 4 or bi >= NBARS - 4 else 0.4
    for st in range(16):
        n = sec(1) - 30
        s = pulse(hz(notes[st % 4]), n, 0.125) * env(n, 0.001, 0.05, 0.4, 0.01) * vol
        place(mix_arp, sec(bi * BAR + st), s)

# Bass: segitiga, pola oktaf 1/8
for bi, c in enumerate(prog):
    r = ROOT[c]; up = r[:-1] + str(int(r[-1]) + 1)
    pat = [r, r, up, r, r, up, r, up]
    for k, nt in enumerate(pat):
        n = sec(2) - 60
        s = quant(tri(hz(nt), n)) * env(n, 0.002, 0, 1, 0.02)
        place(mix_bass, sec(bi * BAR + 2 * k), s)

# Drum: kick (pitch drop), snare (noise), hat (noise pendek)
def kick():
    n = int(0.12 * SR); t = np.arange(n) / SR
    f = 150 * np.exp(-t * 30) + 45
    return quant(tri(f, n)) * np.exp(-t * 22)
def snare():
    n = int(0.14 * SR); t = np.arange(n) / SR
    return noise(n, 12000) * np.exp(-t * 26) * 0.8 + quant(tri(190 * np.exp(-t * 10), n)) * np.exp(-t * 40) * 0.4
def hat(open_=False):
    n = int((0.09 if open_ else 0.03) * SR); t = np.arange(n) / SR
    return noise(n, 30000, short=True) * np.exp(-t * (30 if open_ else 110)) * 0.35
K, S, H, HO = kick(), snare(), hat(), hat(True)
for bi in range(NBARS):
    intro = bi < 2
    for st in range(16):
        p = sec(bi * BAR + st)
        if st in (0, 6, 10) and not (intro and st != 0): place(mix_drum, p, K)
        if st in (4, 12) and not intro: place(mix_drum, p, S)
        if st % 2 == 0: place(mix_drum, p, HO if st == 14 else H)
    if bi in (11, 19, 27, 31):           # fill di akhir frase
        for st in (13, 14, 15): place(mix_drum, sec(bi * BAR + st), S * 0.8)

music = 0.20 * mix_lead + 0.10 * mix_arp + 0.32 * mix_bass + 0.30 * mix_drum
music[:TAIL] += music[N:N + TAIL]          # bungkus ekor ke awal: loop mulus
music = music[:N]
music /= np.max(np.abs(music)) / 0.85

def write(name, x, mono=True):
    path = os.path.join(OUT, name + '.wav')
    pcm = (np.clip(x, -1, 1) * 32767).astype('<i2')
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
    return path

def encode(name, x, kbps=96):
    wav = write(name, x)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-c:a', 'libvorbis', '-q:a', '1',
                    os.path.join(OUT, name + '.ogg')], check=True)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav, '-c:a', 'libmp3lame', '-b:a', f'{kbps}k',
                    os.path.join(OUT, name + '.mp3')], check=True)
    os.remove(wav)

os.makedirs(os.path.join(OUT, 'sfx'), exist_ok=True)
encode('music_loop', music, kbps=64)

# ---------------------------------------------------------------- SFX
def sweep(f0, f1, dur, duty=0.5, curve='exp'):
    n = int(dur * SR); t = np.linspace(0, 1, n)
    f = f0 * (f1 / f0) ** t if curve == 'exp' else f0 + (f1 - f0) * t
    return pulse(f, n, duty)

def seq(notes, step, duty=0.5, decay=8, gap=0.0):
    out = []
    for nt in notes:
        n = int(step * SR); t = np.arange(n) / SR
        out.append(pulse(hz(nt), n, duty) * np.exp(-t * decay) * env(n, 0.002, r=0.01))
        if gap: out.append(np.zeros(int(gap * SR)))
    return np.concatenate(out)

def fade(x, r=0.01): return x * env(len(x), 0.001, r=r)
sfx = {}

# shoot: pew pendek, nada turun cepat (sering dipanggil -> pelan & singkat)
n = int(0.07 * SR); t = np.arange(n) / SR
sfx['shoot'] = fade(sweep(1400, 500, 0.07, 0.25) * np.exp(-t * 30)) * 0.5

# enemy_hit: tik metalik (musuh kena tapi belum hancur)
n = int(0.06 * SR); t = np.arange(n) / SR
sfx['enemy_hit'] = fade(sweep(900, 700, 0.06, 0.5) * np.exp(-t * 50) * 0.5 + noise(n, 20000) * np.exp(-t * 70) * 0.4) * 0.7

# explosion: musuh hancur, noise yang turun
n = int(0.35 * SR); t = np.arange(n) / SR
rate = np.linspace(9000, 1500, n)
ex = np.repeat(rng.choice([-1., 1.], n // 2 + 1), 2)[:n]
ex = np.concatenate([noise(int(n * k / 8), 9000 - k * 900)[:int(n / 8)] for k in range(8)])[:n]
ex = np.pad(ex, (0, n - len(ex)))
sfx['explosion'] = fade(ex * np.exp(-t * 9) + quant(tri(120 * np.exp(-t * 6), n)) * np.exp(-t * 12) * 0.6) * 0.85

# explosion_big: boss hancur, lebih panjang dan berlapis
n = int(1.4 * SR); t = np.arange(n) / SR
big = np.concatenate([noise(int(n / 14), 7000 - k * 450) for k in range(14)])
big = np.pad(big, (0, n - len(big)))[:n]
boom2 = np.zeros(n); boom2[int(0.25 * SR):] = big[:n - int(0.25 * SR)] * 0.7
sfx['explosion_big'] = fade((big * np.exp(-t * 3) + boom2 * np.exp(-t * 3.5) + quant(tri(80 * np.exp(-t * 2), n)) * np.exp(-t * 3) * 0.7), 0.1) * 0.9

# powerup: arpeggio naik ceria
sfx['powerup'] = fade(np.concatenate([seq(['C5','E5','G5','C6'], 0.05, 0.5, 6),
                                      seq(['E6'], 0.15, 0.5, 10)])) * 0.6

# player_hit: buzz kasar turun + noise
n = int(0.45 * SR); t = np.arange(n) / SR
f = 420 * np.exp(-t * 4)
sfx['player_hit'] = fade(pulse(f + 40 * (np.arange(n) // 700 % 2), n, 0.5) * np.exp(-t * 4) * 0.5
                         + noise(n, 6000) * np.exp(-t * 8) * 0.5, 0.05) * 0.85

# boss_warning: sirene dua nada, 3x
w = []
for k in range(3):
    for fr in (440, 330):
        m = int(0.22 * SR); tt = np.arange(m) / SR
        w.append(pulse(fr, m, 0.5) * env(m, 0.005, r=0.03) * (0.9 if fr == 440 else 0.75))
sfx['boss_warning'] = fade(np.concatenate(w), 0.08) * 0.55

# wave_clear: fanfare pendek (SEKTOR BERSIH / SEMPURNA)
sfx['wave_clear'] = fade(np.concatenate([seq(['G4','C5','E5'], 0.09, 0.25, 4),
                                         seq(['G5'], 0.12, 0.25, 3), seq(['E5'], 0.09, 0.25, 5),
                                         seq(['G5'], 0.45, 0.25, 2.5)]), 0.1) * 0.6

# combo_up: "ding" dua nada naik (x2/x3/x4)
sfx['combo_up'] = fade(np.concatenate([seq(['B5'], 0.06, 0.125, 10), seq(['E6'], 0.22, 0.125, 9)])) * 0.55

# game_over: melodi turun pelan
sfx['game_over'] = fade(np.concatenate([seq(['E5','D5','C5'], 0.22, 0.5, 3), seq(['A4'], 0.8, 0.5, 2)]), 0.2) * 0.55

for k, v in sfx.items():
    v = v / max(1e-9, np.max(np.abs(v))) * min(0.95, np.max(np.abs(v)) * 1.2)
    encode(os.path.join('sfx', k), np.concatenate([v, np.zeros(int(0.01 * SR))]), kbps=64)
print('selesai:', len(music) / SR, 'detik musik,', len(sfx), 'sfx')

# ---------------------------------------------------------------- EMBED
# Game adalah satu file HTML, jadi semua MP3 juga disediakan sebagai data URI (window.LM_AUDIO).
import base64, json
emb = {'music_loop': 'data:audio/mpeg;base64,' + base64.b64encode(open(os.path.join(OUT, 'music_loop.mp3'), 'rb').read()).decode()}
for k in sfx:
    emb[k] = 'data:audio/mpeg;base64,' + base64.b64encode(open(os.path.join(OUT, 'sfx', k + '.mp3'), 'rb').read()).decode()
with open(os.path.join(OUT, 'audio-embed.js'), 'w') as f:
    f.write('// Dibuat oleh make_audio.py. Jangan edit manual.\nwindow.LM_AUDIO = ' + json.dumps(emb) + ';\n')
