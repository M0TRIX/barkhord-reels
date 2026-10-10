"""Log of posts scheduled through Metricool (the free plan allows 20 a month).

python3 ledger.py count               -> posts logged this month (Tehran time)
python3 ledger.py add NETWORK NOTE    -> log one post today (NETWORK: instagram | youtube)
"""
import datetime, json, os, sys

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "posts_log.json")


def today():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=3, minutes=30)).date()


def load():
    if os.path.exists(PATH):
        with open(PATH, encoding="utf-8") as fh:
            return json.load(fh)
    return []


if __name__ == "__main__":
    log = load()
    if sys.argv[1] == "count":
        month = today().isoformat()[:7]
        print(sum(1 for e in log if e["date"].startswith(month)))
    elif sys.argv[1] == "add":
        log.append({"date": today().isoformat(), "network": sys.argv[2], "note": " ".join(sys.argv[3:])})
        with open(PATH, "w", encoding="utf-8") as fh:
            json.dump(log, fh, ensure_ascii=False, indent=2)
        print(len(log))
