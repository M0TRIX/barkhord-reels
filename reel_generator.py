"""Daily bounce-reel generator.

Usage: python3 reel_generator.py OUT.mp4 [SEED]
Renders a 1080x1920 ~15s vertical clip: a ball bouncing inside a ring, growing on
every hit, playing an ascending note, until it fills the ring and bursts.
Every SEED gives different colors, motion and hook text. Writes OUT.json with
caption/title suggestions next to the video.
"""
import math, colorsys, wave, subprocess, sys, os, json, random, glob, shutil, tempfile
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "reel.mp4"
SEED = int(sys.argv[2]) if len(sys.argv) > 2 else random.randrange(10**9)
rng = random.Random(SEED)
WORK = tempfile.mkdtemp(prefix="reel_")

# ---------------- font (Vazirmatn, from npm) ----------------
FONT_DIR = os.path.expanduser("~/.cache/vazirmatn")
def font_path(weight):
    hits = glob.glob(f"{FONT_DIR}/**/UI-Farsi-Digits/fonts/ttf/Vazirmatn-UI-FD-{weight}.ttf", recursive=True)
    return hits[0] if hits else None
if not font_path("Black"):
    os.makedirs(FONT_DIR, exist_ok=True)
    subprocess.run(["npm", "pack", "vazirmatn", "--silent"], cwd=FONT_DIR, check=True)
    tgz = glob.glob(f"{FONT_DIR}/vazirmatn-*.tgz")[0]
    subprocess.run(["tar", "xzf", tgz], cwd=FONT_DIR, check=True)
FONT, FONT_MED = font_path("Black"), font_path("SemiBold")
RQ = ImageFont.Layout.RAQM

# ---------------- settings (randomized per seed) ----------------
W, H = 1080, 1920
FPS = 30
TARGET_FILL = rng.uniform(12.0, 13.0)     # seconds until the ball fills the ring
OUTRO = 2.2
SUB = 80
C = np.array([W / 2, H / 2 + 40.0])
R = 440.0
R0 = rng.uniform(22, 34)
G = np.array([0.0, rng.uniform(3800, 5600)])
MIN_SPEED = rng.uniform(1900, 2500)
HUE0 = rng.random()
HUE_STEP = rng.choice([0.03, 0.045, 0.06, 0.618034 / 6])
P0 = np.array([W / 2 + rng.uniform(-200, 200), H / 2 - rng.uniform(150, 260)])
V0 = np.array([rng.uniform(-650, 650), rng.uniform(-100, 250)])
BG_HUE = rng.random()

HOOKS = [
    "این توپ تا کجا بزرگ می‌شه؟",
    "تا آخر ببین چی می‌شه",
    "حدس بزن چندتا برخورد می‌خوره",
    "آخرش رو از دست نده",
    "صدا رو زیاد کن",
    "کی حلقه رو پر می‌کنه؟",
]
HOOK = rng.choice(HOOKS)
END_TEXT = rng.choice(["حدست درست بود؟", "چندتا حدس زده بودی؟", "عدد حدسیت رو کامنت کن"])
FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# ---------------- physics ----------------
def simulate(grow, record=False):
    p, v, r, t = P0.copy(), V0.copy(), R0, 0.0
    dt = 1.0 / (FPS * SUB)
    hits, frames = [], []
    hue = HUE0
    max_t = TARGET_FILL + 6
    while t < max_t:
        if record:
            frames.append((p.copy(), r, hue))
        for _ in range(SUB):
            v = v + G * dt
            p = p + v * dt
            t += dt
            d = p - C
            dist = np.linalg.norm(d)
            if dist + r >= R:
                n = d / dist
                vn = v @ n
                p = C + n * (R - r - 0.5)
                if vn > 0:
                    v = v - 2 * vn * n
                    sp = np.linalg.norm(v)
                    if sp < MIN_SPEED:
                        v *= MIN_SPEED / sp
                    r = r + grow
                    hue = (hue + HUE_STEP) % 1.0
                    hits.append((t, (C + n * R).copy(), hue))
                    if r >= R - 14:
                        return t, hits, frames, p, r, hue
    return None, hits, frames, p, r, hue

# fill time is chaotic in the growth rate, so scan and keep the closest match
best = None
for grow in np.linspace(1.5, 14, 60):
    tf, *_ = simulate(grow)
    if tf is not None and (best is None or abs(tf - TARGET_FILL) < abs(best[1] - TARGET_FILL)):
        best = (grow, tf)
        if abs(tf - TARGET_FILL) < 0.15:
            break
GROW = best[0]
T_FILL, HITS, FRAMES, P_END, R_END, HUE_END = simulate(GROW, record=True)
DUR = T_FILL + OUTRO
N = int(DUR * FPS)
print(f"seed={SEED} grow={GROW:.2f} hits={len(HITS)} fill={T_FILL:.2f}s dur={DUR:.2f}s")

# burst particles
prng = np.random.default_rng(SEED)
NP = 160
ang = prng.uniform(0, 2 * np.pi, NP)
spd = prng.uniform(500, 2200, NP)
PV = np.stack([np.cos(ang) * spd, np.sin(ang) * spd], 1)
PP = P_END + np.stack([np.cos(ang), np.sin(ang)], 1) * prng.uniform(0, R_END * 0.8, (NP, 1))
PS = prng.uniform(6, 20, NP)
PH = (HUE_END + prng.uniform(-0.12, 0.12, NP)) % 1

def rgb(h, s=0.75, l=0.6, a=255):
    rr, gg, bb = colorsys.hls_to_rgb(h, l, s)
    return (int(rr * 255), int(gg * 255), int(bb * 255), a)

# ---------------- audio ----------------
SR = 44100
audio = np.zeros(int(SR * (DUR + 2)))
pent = [0, 2, 4, 7, 9]
def midi_for(i):
    # climb two octaves, then keep climbing within a moving window so it never gets shrill
    step = i % 15
    octv, deg = divmod(step, 5)
    return 57 + 12 * octv + pent[deg]
def note(f0, L, decay):
    tt = np.arange(L) / SR
    env = np.minimum(tt / 0.004, 1) * np.exp(-tt * decay)
    return (np.sin(2 * np.pi * f0 * tt) + 0.35 * np.sin(2 * np.pi * 2 * f0 * tt) * np.exp(-tt * 9)
            + 0.18 * np.sin(2 * np.pi * 4 * f0 * tt) * np.exp(-tt * 22)) * env
for i, (ht, _, _) in enumerate(HITS):
    f0 = 440 * 2 ** ((midi_for(i) - 69) / 12)
    L = int(SR * 0.7)
    tt = np.arange(L) / SR
    snd = note(f0, L, 6.0) + np.sin(2 * np.pi * 90 * tt) * np.exp(-tt * 30) * 0.4
    s = int(ht * SR); seg = audio[s:s + L]; seg += snd[: len(seg)] * 0.8
# burst: low boom + bright chord
s = int(T_FILL * SR); L = int(SR * 2.0); tt = np.arange(L) / SR
boom = np.sin(2 * np.pi * 55 * tt * (1 - 0.3 * tt)) * np.exp(-tt * 3.5) * 1.6
noise = np.random.default_rng(SEED).normal(0, 1, L) * np.exp(-tt * 9) * 0.5
chord = sum(note(440 * 2 ** ((m - 69) / 12), L, 1.8) for m in (69, 73, 76, 81)) * 0.35
seg = audio[s:s + L]; seg += (boom + noise + chord)[: len(seg)]
d = int(0.11 * SR); wet = np.zeros_like(audio); wet[d:] = audio[:-d] * 0.28
d2 = int(0.23 * SR); wet[d2:] += audio[:-d2] * 0.12
audio = (audio + wet)[: int(SR * DUR)]
fade = int(0.3 * SR); audio[-fade:] *= np.linspace(1, 0, fade)
audio = audio / (np.abs(audio).max() + 1e-9) * 0.89
WAV = os.path.join(WORK, "audio.wav")
with wave.open(WAV, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((audio * 32767).astype(np.int16).tobytes())

# ---------------- background ----------------
yy = np.linspace(0, 1, H)[:, None]; xx = np.linspace(-1, 1, W)[None, :]
top = np.array(rgb(BG_HUE, 0.45, 0.05)[:3]); bot = np.array(rgb(BG_HUE, 0.5, 0.11)[:3])
grad = top + (bot - top) * yy[..., None]
BG = Image.fromarray(np.clip(grad * (1 - 0.35 * xx ** 2)[..., None], 0, 255).astype(np.uint8)).convert("RGBA")

font_hook = ImageFont.truetype(FONT, 76, layout_engine=RQ)
font_lbl = ImageFont.truetype(FONT_MED, 46, layout_engine=RQ)
font_end = ImageFont.truetype(FONT, 84, layout_engine=RQ)
cnt_fonts = {}
def cnt_font(sz):
    if sz not in cnt_fonts:
        cnt_fonts[sz] = ImageFont.truetype(FONT, sz, layout_engine=RQ)
    return cnt_fonts[sz]
def circ(dr, cx, cy, rad, s, **kw):
    dr.ellipse([(cx - rad) * s, (cy - rad) * s, (cx + rad) * s, (cy + rad) * s], **kw)

# ---------------- render ----------------
ff = subprocess.Popen([
    "ffmpeg", "-y", "-loglevel", "error",
    "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
    "-i", WAV, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT,
], stdin=subprocess.PIPE)

SS, TRAIL, gs = 2, 8, 0.5
total_hits = len(HITS)
for fi in range(N):
    tnow = fi / FPS
    burst = tnow >= T_FILL
    if not burst:
        pos, rad, hcur = FRAMES[min(fi, len(FRAMES) - 1)]
    else:
        pos, rad, hcur = P_END, R_END, HUE_END
    past = [h for h in HITS if h[0] <= tnow]
    count = len(past)
    since = tnow - past[-1][0] if past else 99
    flash = math.exp(-since * 9) if past else 0
    bt = tnow - T_FILL if burst else -1

    glow = Image.new("RGBA", (int(W * gs), int(H * gs)), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    ring_alpha = int(90 + 165 * flash) if not burst else int(255 * math.exp(-bt * 2))
    gd.ellipse([(C[0] - R - 8) * gs, (C[1] - R - 8) * gs, (C[0] + R + 8) * gs, (C[1] + R + 8) * gs],
               outline=rgb(hcur, 0.85, 0.6, ring_alpha), width=int((14 + 30 * flash) * gs))
    if not burst:
        circ(gd, pos[0], pos[1], rad * 1.15, gs, fill=rgb(hcur, 0.9, 0.6, 200))
    glow = glow.filter(ImageFilter.GaussianBlur(28 * gs)).resize((W, H), Image.BILINEAR)
    frame = BG.copy()
    frame.alpha_composite(glow)
    if burst and bt < 0.25:   # white flash
        fl = Image.new("RGBA", (W, H), (255, 255, 255, int(200 * (1 - bt / 0.25))))
        frame.alpha_composite(fl)

    crisp = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    cd = ImageDraw.Draw(crisp)
    ring_a = 255 if not burst else int(255 * math.exp(-bt * 2.5))
    cd.ellipse([(C[0] - R - 6) * SS, (C[1] - R - 6) * SS, (C[0] + R + 6) * SS, (C[1] + R + 6) * SS],
               outline=rgb(hcur, 0.8, 0.72 + 0.2 * flash, ring_a), width=int(10 * SS))
    for ht, cp, hh in past[-4:]:
        age = tnow - ht
        if age < 0.35:
            k = age / 0.35
            rr_ = 20 + 160 * (1 - (1 - k) ** 3)
            cd.ellipse([(cp[0] - rr_) * SS, (cp[1] - rr_) * SS, (cp[0] + rr_) * SS, (cp[1] + rr_) * SS],
                       outline=rgb(hh, 0.9, 0.75, int(230 * (1 - k))), width=int(max(2, 8 * (1 - k)) * SS))
    if not burst:
        for k in range(TRAIL, 0, -1):
            j = fi - k
            if j < 0:
                continue
            tp, trd, th = FRAMES[j]
            a = int(80 * (1 - k / TRAIL) ** 1.4)
            circ(cd, tp[0], tp[1], trd * (1 - 0.45 * k / TRAIL), SS, fill=rgb(th, 0.95, 0.66, a))
        circ(cd, pos[0], pos[1], rad, SS, fill=rgb(hcur, 0.85, 0.58))
        circ(cd, pos[0], pos[1], rad - 5, SS, outline=(255, 255, 255, 70), width=int(3 * SS))
        circ(cd, pos[0] - rad * 0.32, pos[1] - rad * 0.32, rad * 0.22, SS, fill=(255, 255, 255, 110))
    else:
        g = np.array([0, 1400.0])
        pp = PP + PV * bt * np.exp(-bt * 0.8) + 0.5 * g * bt ** 2
        a = max(0, 1 - bt / OUTRO)
        for q in range(NP):
            circ(cd, pp[q, 0], pp[q, 1], PS[q] * (1 - 0.5 * bt / OUTRO), SS,
                 fill=rgb(PH[q], 0.9, 0.65, int(255 * a)))
    frame.alpha_composite(crisp.resize((W, H), Image.LANCZOS))

    td = ImageDraw.Draw(frame)
    td.text((W / 2, 250), HOOK, font=font_hook, fill=(255, 255, 255, 255), anchor="mm", direction="rtl", language="fa")
    pop = 1 + 0.35 * flash if not burst else 1 + 0.6 * math.exp(-bt * 4)
    td.text((W / 2, H - 330), str(count).translate(FA), font=cnt_font(int(150 * pop)),
            fill=rgb(hcur, 0.85, 0.72), anchor="mm")
    td.text((W / 2, H - 205), "برخورد", font=font_lbl, fill=(255, 255, 255, 150), anchor="mm",
            direction="rtl", language="fa")
    if burst and bt > 0.35:
        a = int(255 * min(1, (bt - 0.35) / 0.3))
        td.text((W / 2, C[1]), END_TEXT, font=font_end, fill=(255, 255, 255, a), anchor="mm",
                direction="rtl", language="fa")
    ff.stdin.write(frame.convert("RGB").tobytes())
    if os.environ.get("PREVIEW") and fi in (N // 3, int(T_FILL * FPS) - 2, int((T_FILL + 0.8) * FPS)):
        frame.convert("RGB").save(f"{OUT}.preview_{fi:04d}.png")

ff.stdin.close(); ff.wait()
shutil.rmtree(WORK, ignore_errors=True)

meta = {
    "seed": SEED, "hits": total_hits, "duration": round(DUR, 2),
    "instagram_caption": f"{HOOK} 👀\nتو کامنت بنویس چندتا برخورد حدس زدی 👇\n\n#ریلز #لذت_بخش #فیزیک #satisfying #physics #oddlysatisfying #reels",
    "youtube_title": f"{HOOK} #shorts",
    "youtube_description": "تا آخر ببین 👀\n#shorts #satisfying #physics #oddlysatisfying",
}
with open(os.path.splitext(OUT)[0] + ".json", "w", encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=2)
print("done", OUT, json.dumps(meta, ensure_ascii=False))
