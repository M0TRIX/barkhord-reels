"""Silent animated City Cup table, made to carry a trending Instagram sound added in the app.

Usage: CUP_STATE=season/state_001.json python3 table_reel.py OUT.mp4 ["next match line"]
Rows pop in one by one (a beat every 0.45 s), winners turn gold, then the table holds.
The video has a silent audio track: the owner picks the trending sound when posting,
which is the licensed way to use it (copying a song into the file would get muted or flagged).
"""
import glob, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cup

OUT = sys.argv[1]
NEXT_LINE = sys.argv[2] if len(sys.argv) > 2 else ""
W, H, FPS, DUR = 1080, 1920, 30, 15.0
state = cup.load()
cup._fill_next_rounds(state)

font_dir = os.path.expanduser("~/.cache/vazirmatn")
BLACK = glob.glob(f"{font_dir}/**/UI-Farsi-Digits/fonts/ttf/Vazirmatn-UI-FD-Black.ttf", recursive=True)[0]
SEMI = BLACK.replace("Black", "SemiBold")
_f = {}
def F(size, bold=True):
    k = (size, bold)
    if k not in _f:
        _f[k] = ImageFont.truetype(BLACK if bold else SEMI, size, layout_engine=ImageFont.Layout.RAQM)
    return _f[k]

def text(d, xy, s, size, fill, bold=True):
    d.text(xy, s, font=F(size, bold), fill=fill, anchor="mm", direction="rtl", language="fa")

GOLD, DIM, WHITE, ROW, ROW_ON = (255, 210, 63), (120, 120, 150), (255, 255, 255), (34, 30, 64), (52, 44, 96)
BG = Image.new("RGB", (W, H))
bd = ImageDraw.Draw(BG)
for y in range(H):
    k = y / H
    bd.line([(0, y), (W, y)], fill=(int(14 + 22 * k), int(12 + 6 * k), int(30 + 34 * k)))

# layout: every row of the bracket with its y position and reveal time
rows, labels = [], []
y, t = 330, 0.6
sizes = [8, 4, 2, 1]
for r in range(4):
    labels.append((r, y, t))
    y += 58
    row_h = 64 if r == 0 else 70
    for m in range(sizes[r]):
        a, b, w = state["rounds"][r][m] if m < len(state["rounds"][r]) else ("؟", "؟", None)
        rows.append({"y": y, "h": row_h, "a": a, "b": b, "w": w, "t": t})
        t += 0.45
        y += row_h
    y += 24
END_T = t + 0.3

def ease(k):
    k = max(0.0, min(1.0, k))
    return 1 - (1 - k) ** 3

def frame(tm):
    img = BG.copy()
    d = ImageDraw.Draw(img)
    pop = 1 + 0.25 * max(0, 1 - tm / 0.3)
    text(d, (W / 2, 140), "جدول جام شهرها", int(92 * pop), GOLD)
    text(d, (W / 2, 230), "تا امروز", 46, WHITE, bold=False)
    for r, ly, lt in labels:
        if tm >= lt - 0.2:
            text(d, (W / 2, ly), cup.ROUND_NAMES[r], 40, (180, 200, 255))
    for row in rows:
        k = (tm - row["t"]) / 0.25
        if k <= 0:
            continue
        e = ease(k)
        off = (1 - e) * 120
        yc, h = row["y"], row["h"]
        played = row["w"] is not None
        d.rounded_rectangle([90 + off, yc - h / 2 + 6, 990 + off, yc + h / 2 - 6], 18, fill=ROW_ON if played else ROW)
        hl = played and tm >= row["t"] + 0.2           # winner turns gold just after the row lands
        ca = GOLD if hl and row["w"] == row["a"] else (DIM if hl else WHITE)
        cb = GOLD if hl and row["w"] == row["b"] else (DIM if hl else WHITE)
        text(d, (735 + off, yc), row["a"], 38, ca)
        text(d, (540 + off, yc), "–", 34, DIM)
        text(d, (345 + off, yc), row["b"], 38, cb)
        if hl:                                         # strike through the loser
            loser_x = 345 if row["w"] == row["a"] else 735
            name = row["b"] if row["w"] == row["a"] else row["a"]
            tw = d.textlength(name, font=F(38), direction="rtl", language="fa")
            d.line([loser_x + off - tw / 2 - 6, yc + 3, loser_x + off + tw / 2 + 6, yc + 3], fill=(230, 70, 70), width=5)
    if tm >= END_T:
        k = ease((tm - END_T) / 0.4)
        if NEXT_LINE:
            yb = H - 230 + (1 - k) * 300
            d.rounded_rectangle([90, yb - 62, 990, yb + 62], 30, fill=GOLD)
            text(d, (W / 2, yb), NEXT_LINE, 50, (40, 20, 10))
        text(d, (W / 2, H - 100 + (1 - k) * 200), "شهر تو هنوز تو جامه؟ کامنت کن", 40, WHITE, bold=False)
    return img

ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
                       "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
                       "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
for fi in range(int(DUR * FPS)):
    ff.stdin.write(frame(fi / FPS).tobytes())
ff.stdin.close(); ff.wait()
print("done", OUT, f"rows end at {END_T:.1f}s")
