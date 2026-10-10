"""Make the oldest viewer-requested match in requests.json.

Usage: python3 make_request.py            -> renders it, prints the .json path last
       python3 make_request.py add A B    -> queues "A vs B" (Persian city names)
Prints "none" when the queue is empty. Writes reels/request_<SEED>.mp4 + .json
(same keys as every reel: instagram_caption, first_comment, youtube_title, youtube_tags).
"""
import datetime, json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "requests.json")


def load():
    with open(PATH, encoding="utf-8") as fh:
        return json.load(fh)


def save(q):
    with open(PATH, "w", encoding="utf-8") as fh:
        json.dump(q, fh, ensure_ascii=False, indent=2)


def today():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3, minutes=30)).date().isoformat()


q = load()
if len(sys.argv) == 4 and sys.argv[1] == "add":
    q["pending"].append({"teams": [sys.argv[2], sys.argv[3]], "added": today(), "from": "viewer comment"})
    save(q)
    print("queued", sys.argv[2], "vs", sys.argv[3])
    sys.exit()
if not q["pending"]:
    print("none")
    sys.exit()
req = q["pending"][0]
seed = int(time.time())
out = os.path.join(HERE, "reels", f"request_{seed}.mp4")
os.makedirs(os.path.dirname(out), exist_ok=True)
env = dict(os.environ, MATCH=",".join(req["teams"]))
subprocess.run([sys.executable, os.path.join(HERE, "battle.py"), out, str(seed), "request"], check=True, env=env)
meta_path = os.path.splitext(out)[0] + ".json"
with open(meta_path, encoding="utf-8") as fh:
    winner = json.load(fh)["winner"]
q = load()                                  # re-read: nothing else should have changed it, but be safe
q["pending"] = [r for r in q["pending"] if r["teams"] != req["teams"]]
q["done"].append({"teams": req["teams"], "made": today(), "file": os.path.relpath(out, HERE), "winner": winner})
save(q)
print(meta_path)
