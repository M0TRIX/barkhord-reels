"""Log of posts scheduled through Metricool (the free plan allows 20 a month).

python3 ledger.py count [YYYY-MM]                 -> posts that go out in this month (Tehran time) or the given one
python3 ledger.py add NETWORK NOTE                -> log one post going out today (NETWORK: instagram | youtube)
python3 ledger.py add NETWORK NOTE --on YYYY-MM-DD -> log one post scheduled for that date
Metricool counts a post in the month it is published, so every entry is dated by its publishing day.
"""
import datetime, json, os, sys

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posts_log.json")


def today():
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=3, minutes=30)).date()


def load():
    if os.path.exists(PATH):
        with open(PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return []


if __name__ == "__main__":
    log = load()
    if sys.argv[1] == "count":
        month = sys.argv[2] if len(sys.argv) > 2 else today().isoformat()[:7]
        print(sum(1 for e in log if e["date"].startswith(month)))
    elif sys.argv[1] == "add":
        args, day = sys.argv[3:], today().isoformat()
        if "--on" in args:
            i = args.index("--on")
            day = args[i + 1]
            args = args[:i] + args[i + 2:]
        log.append({"date": day, "network": sys.argv[2], "note": " ".join(args), "created": today().isoformat()})
        with open(PATH, "w", encoding="utf-8") as fh:
            json.dump(log, fh, ensure_ascii=False, indent=2)
        print(len(log))
