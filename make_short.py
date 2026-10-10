"""Make today's YouTube Short: the next World Cup of Countries match (English).

Usage: python3 make_short.py
Writes shorts/short_<SEED>.mp4 and shorts/short_<SEED>.json (youtube_title,
instagram_caption = YouTube description, first_comment, youtube_tags) and prints
the json path as its last line. Updates wcup.json.
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
SHORTS = os.path.join(HERE, "shorts")
os.makedirs(SHORTS, exist_ok=True)
seed = int(time.time())
out = os.path.join(SHORTS, f"short_{seed}.mp4")
subprocess.run([sys.executable, os.path.join(HERE, "battle.py"), out, str(seed), "worldcup"], check=True)
print(os.path.splitext(out)[0] + ".json")
