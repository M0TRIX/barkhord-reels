"""Make today's YouTube Short: the next World Cup of Countries match (English).

Usage: python3 make_short.py   (the day after a round finishes, it makes that round's recap instead)
Writes shorts/short_<SEED>.mp4 and shorts/short_<SEED>.json (youtube_title,
instagram_caption = YouTube description, first_comment, youtube_tags) and prints
the json path as its last line. Updates wcup.json.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SHORTS = os.path.join(HERE, "shorts")
os.makedirs(SHORTS, exist_ok=True)
sys.path.insert(0, HERE)
import worldcup as wc

seed = int(time.time())
out = os.path.join(SHORTS, f"short_{seed}.mp4")
rd = wc.round_to_recap(wc.load())
if rd is not None:      # a round just finished: today's Short is its recap
    subprocess.run([sys.executable, os.path.join(HERE, "recap.py"), out, "worldcup", str(rd)], check=True)
    st = wc.load()
    st.setdefault("recaps_done", []).append(rd)
    wc.save(st)
else:
    subprocess.run([sys.executable, os.path.join(HERE, "battle.py"), out, str(seed), "worldcup"], check=True)
print(os.path.splitext(out)[0] + ".json")
