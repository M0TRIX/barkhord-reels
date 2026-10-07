"""Make today's reel for barkhord.tv, rotating between formats.

Usage: python3 make_reel.py [FORMAT]
FORMAT is one of derby, cities, colors, ring. Without it, a format is picked at
random (weighted), never repeating the one used for the most recent reel.
Writes reels/reel_<SEED>.mp4 and reels/reel_<SEED>.json and prints the json path.
"""
import glob, json, os, random, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
REELS = os.path.join(HERE, "reels")
os.makedirs(REELS, exist_ok=True)
WEIGHTS = {"derby": 0.35, "cities": 0.35, "colors": 0.15, "ring": 0.15}

def last_format():
    metas = sorted(glob.glob(os.path.join(REELS, "reel_*.json")),
                   key=lambda p: int(os.path.basename(p)[5:-5]) if os.path.basename(p)[5:-5].isdigit() else 0)
    if not metas:
        return None
    with open(metas[-1], encoding="utf-8") as fh:
        return json.load(fh).get("format", "ring")

seed = int(time.time())
fmt = sys.argv[1] if len(sys.argv) > 1 else None
if fmt is None:
    prev = last_format()
    options = {k: w for k, w in WEIGHTS.items() if k != prev}
    fmt = random.Random(seed).choices(list(options), weights=list(options.values()))[0]

out = os.path.join(REELS, f"reel_{seed}.mp4")
if fmt == "ring":
    cmd = [sys.executable, os.path.join(HERE, "reel_generator.py"), out, str(seed)]
else:
    cmd = [sys.executable, os.path.join(HERE, "battle.py"), out, str(seed), fmt]
subprocess.run(cmd, check=True)
meta_path = os.path.splitext(out)[0] + ".json"
with open(meta_path, encoding="utf-8") as fh:
    meta = json.load(fh)
meta.setdefault("format", fmt)
with open(meta_path, "w", encoding="utf-8") as fh:
    json.dump(meta, fh, ensure_ascii=False, indent=2)
print(meta_path)
