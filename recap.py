"""Round recap reel: every result of a finished round, revealed one by one.

Usage: python3 recap.py OUT.mp4 SERIES ROUND      SERIES = cup | worldcup
Writes OUT.json with captions (same keys as battle.py).
"""
import glob, json, math, os, random, subprocess, sys, tempfile, wave, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sfx

OUT, SERIES, RD = sys.argv[1], sys.argv[2], int(sys.argv[3])
EN = SERIES == "worldcup"
if EN:
    import worldcup as S
else:
    import cup as S
state = S.load()
matches = state["rounds"][RD]
nxt = S.pending(state)
next_pair = state["rounds"][nxt[0]][nxt[1]][:2] if nxt else None
name = (lambda c: S.name(c)) if EN else (lambda c: c)

FONT_DIR = os.path.expanduser("~/.cache/vazirmatn")
if EN:
    FB = glob.glob(f"{FONT_DIR}/package/fonts/ttf/Vazirmatn-Black.ttf")[0]
else:
    FB = glob.glob(f"{FONT_DIR}/**/UI-Farsi-Digits/fonts/ttf/Vazirmatn-UI-FD-Black.ttf", recursive=True)[0]
FM = FB.replace("Black", "SemiBold")
_f = {}
def F(size, bold=True):
    k = (size, bold)
    if k not in _f:
        _f[k] = ImageFont.truetype(FB if bold else FM, size, layout_engine=ImageFont.Layout.RAQM)
    return _f[k]

W, H, FPS = 1080, 1920, 30
n = len(matches)
STEP = 0.45 if n <= 8 else 0.3
T0 = 0.9
REVEAL = [T0 + k * STEP for k in range(n)]
T_NEXT = REVEAL[-1] + 0.8
DUR = T_NEXT + 3.0
GOLD, DIM, WHITE = (255, 210, 63), (110, 110, 140), (255, 255, 255)

def text(d, xy, s, size, col, bold=True, anchor="mm"):
    latin = not any("؀" <= ch <= "ۿ" for ch in s)
    d.text(xy, s, font=F(size, bold), fill=col, anchor=anchor,
           direction="ltr" if (EN or latin) else "rtl", language="en" if (EN or latin) else "fa")

flags = {}
def flag(code, w, h):
    k = (code, w, h)
    if k not in flags:
        flags[k] = Image.open(S.flag_path(code)).convert("RGBA").resize((w, h), Image.LANCZOS)
    return flags[k]

BG = Image.new("RGBA", (W, H))
bd = ImageDraw.Draw(BG)
for y in range(H):
    k = y / H
    bd.line([(0, y), (W, y)], fill=(int(14 + 24 * k), int(12 + 6 * k), int(30 + 36 * k), 255))

title = "World Cup of Countries" if EN else "جام شهرها"
sub = f"{S.ROUND_NAMES[RD]} results" if EN else f"نتایج {S.ROUND_NAMES[RD]}"
top, bottom = 330, 1500
row_h = min(120, (bottom - top) / n)
fs = int(min(46, row_h * 0.5))

def frame(t):
    img = BG.copy()
    d = ImageDraw.Draw(img)
    text(d, (W / 2, 150), title, 84, GOLD)
    text(d, (W / 2, 240), sub, 46, WHITE, bold=False)
    for k, (a, b, w) in enumerate(matches):
        y = top + row_h * (k + 0.5)
        shown = t >= REVEAL[k]
        age = t - REVEAL[k]
        pop = 1 + 0.15 * max(0, 1 - age / 0.15) if shown else 1
        d.rounded_rectangle([70, y - row_h / 2 + 5, W - 70, y + row_h / 2 - 5], 18,
                            fill=(48, 40, 86, 255) if shown else (32, 28, 58, 255))
        # first team on the reading-start side
        left, right = (a, b) if EN else (b, a)
        for code, x in ((left, 300), (right, W - 300)):
            won = shown and code == w
            lost = shown and code != w
            col = GOLD if won else (DIM if lost else WHITE)
            size = int(fs * (pop if won else 1))
            if EN:
                fw, fh = int(row_h * 0.62), int(row_h * 0.46)
                fx = 95 if x < W / 2 else W - 95 - fw
                img.alpha_composite(flag(code, fw, fh), (int(fx), int(y - fh / 2)))
            text(d, (x, y), name(code), size, col)
            if lost:
                tw = d.textlength(name(code), font=F(size))
                d.line([x - tw / 2 - 6, y + 2, x + tw / 2 + 6, y + 2], fill=(230, 70, 70, 255), width=5)
        text(d, (W / 2, y), "VS" if not shown else "✓" if False else "–", int(fs * 0.8), DIM)
    if t >= T_NEXT:
        k = min(1, (t - T_NEXT) / 0.35)
        yb = H - 330 + (1 - (1 - (1 - k) ** 3)) * 400
        d.rounded_rectangle([70, yb - 90, W - 70, yb + 90], 34, fill=(255, 210, 63, 255))
        if next_pair:
            line1 = "NEXT MATCH" if EN else "بازی بعد"
            pair = f"{name(next_pair[0])} vs {name(next_pair[1])}" if EN else f"{name(next_pair[0])} و {name(next_pair[1])}"
        else:
            line1, pair = ("CHAMPION", name(state.get("champion") or "")) if EN else ("قهرمان", state.get("champion") or "")
        text(d, (W / 2, yb - 38), line1, 40, (60, 30, 10), bold=False)
        text(d, (W / 2, yb + 22), pair, 60, (40, 20, 10))
        text(d, (W / 2, yb + 150), "Subscribe so you don't miss it" if EN else "فالو کن که از دستت نره", 40, WHITE, bold=False)
    d.text((W / 2, H - 70), "BARKHORD" if EN else "@barkhord.tv", font=F(34, False), fill=(255, 255, 255, 110), anchor="mm")
    return img

# audio: light beat, a pop per reveal, cheer at the end
SR = sfx.SR
audio = np.zeros(int(SR * (DUR + 2)))
def add(sig, t0, g):
    s0 = int(t0 * SR); seg = audio[s0:s0 + len(sig)]; seg += sig[: len(seg)] * g
add(sfx.drum_loop(DUR, 120), 0, 0.25)
for k, t in enumerate(REVEAL):
    add(sfx.pop(500 + 40 * k), t, 0.7)
add(sfx.bell(1), T_NEXT, 0.4)
add(sfx.crowd(2.6, seed=21), T_NEXT, 0.35)
audio = audio[: int(SR * DUR)]
fade = int(0.4 * SR); audio[-fade:] *= np.linspace(1, 0, fade)
audio = audio / (np.abs(audio).max() + 1e-9) * 0.89
work = tempfile.mkdtemp(prefix="recap_")
wav = os.path.join(work, "a.wav")
with wave.open(wav, "wb") as wf:
    wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((audio * 32767).astype(np.int16).tobytes())
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT],
                      stdin=subprocess.PIPE)
for fi in range(int(DUR * FPS)):
    img = frame(fi / FPS)
    ff.stdin.write(img.convert("RGB").tobytes())
    if os.environ.get("PREVIEW") and fi in (int(T0 * FPS) + 20, int((T_NEXT + 1.0) * FPS)):
        img.convert("RGB").save(f"{OUT}.preview_{fi:04d}.png")
ff.stdin.close(); ff.wait()
shutil.rmtree(work, ignore_errors=True)

# captions
winners = [name(w) for _, _, w in matches]
if EN:
    rn = S.ROUND_NAMES[RD]
    np_txt = f"Next: {name(next_pair[0])} vs {name(next_pair[1])}" if next_pair else ""
    caption = (f"🌍 World Cup of Countries — {rn} results!\nThrough: {', '.join(winners)}\n{np_txt}\n\n"
               f"Is your country still alive? 👇\n\n#worldcup #countries #simulation #shorts")
    first = "Which country takes the cup? 👇"
    yt_title = f"{rn} results 🏆 World Cup of Countries #shorts"[:100]
    yt_tags = ["world cup of countries", "country battle", "results", "simulation", "shorts"]
else:
    rn = S.ROUND_NAMES[RD]
    np_txt = f"🔜 بازی بعد: {next_pair[0]} و {next_pair[1]}" if next_pair else ""
    caption = (f"نتایج {rn} جام شهرها 🏆\nرفتن بالا: {'، '.join(winners)}\n{np_txt}\n\n"
               f"شهر تو هنوز تو جامه؟ 👇\n\n#جام_شهرها #ایران")
    first = "به نظرتون کدوم شهر قهرمان میشه؟ 👇"
    yt_title = f"نتایج {rn} جام شهرها 🏆 #shorts"[:100]
    yt_tags = ["جام شهرها", "نتایج", "ایران", "shorts"]
meta = {"format": "recap", "series": SERIES, "round": RD, "duration": round(DUR, 2),
        "instagram_caption": caption, "first_comment": first, "cover_ms": int((T_NEXT + 0.5) * 1000),
        "youtube_title": yt_title, "youtube_tags": yt_tags}
with open(os.path.splitext(OUT)[0] + ".json", "w", encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=2)
print("done", OUT)
