"""Instagram captions and first comments for barkhord.tv reels.

Kept short and conversational on purpose: one or two lines, one question,
a few hashtags. Edit the lists below to change the tone; every reel picks
one line from each list at random.
"""

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa(n):
    return str(n).translate(FA_DIGITS)


def join_fa(names):
    """['تهران', 'مشهد', 'اصفهان'] -> 'تهران، مشهد و اصفهان'"""
    if len(names) == 1:
        return names[0]
    return "، ".join(names[:-1]) + " و " + names[-1]


def or_fa(names):
    """['قرمز', 'آبی'] -> 'قرمز یا آبی'"""
    if len(names) == 1:
        return names[0]
    return "، ".join(names[:-1]) + " یا " + names[-1]


def tag(word):
    return "#" + word.replace(" ", "_").replace("‌", "_")


def derby(rng, names, winner):
    first_line = rng.choice([
        "پرسپولیسی‌ها کجان؟ 🔴\nاستقلالی‌ها؟ 🔵",
        "دربی این دفعه یه جور دیگه‌ست 😅",
        "قبل از اینکه تموم شه بگو کی می‌بره 👀",
        "سرخابی‌ها بیاین ببینیم 😂",
        "این دفعه کی می‌بره؟ 🔴🔵",
    ])
    second_line = rng.choice([
        "تیمتو کامنت کن ببینیم کدوما بیشترن 👇",
        "تا آخرش ببین، بعد بگو کی برد 👇",
        "تیمتو بنویس 👇",
    ])
    caption = f"{first_line}\n\n{second_line}\n\n#پرسپولیس #استقلال #دربی"
    first = rng.choice([
        "🔴 پرسپولیسی‌ها لایک کنن\n🔵 استقلالی‌ها ریپلای بزنن\nببینیم کدوم بیشتره 😏",
        "دفعه بعد کی می‌بره؟ 👇",
    ])
    return caption, first


def cities(rng, names, winner):
    first_line = rng.choice([
        f"{or_fa(names)}؟ 🏙️",
        f"امروز نوبت {join_fa(names)}ه 🔥",
        "کدوم شهر می‌بره؟ 👀",
    ])
    second_line = rng.choice([
        "شهرت نیست؟ کامنت کن، دفعه بعد میاریمش 👇",
        "شهر خودتو بنویس تا بعدی اون باشه 👇",
        "شهرت تو لیست نبود؟ بگو تا بیاریمش 👇",
    ])
    caption = f"{first_line}\n\n{second_line}\n\n#ایران " + " ".join(tag(n) for n in names[:3])
    first = rng.choice([
        "شهرتونو اینجا بنویسید، بعدی‌ها از همینا انتخاب میشن 👇",
        f"{winner} برد 🏆 شهر تو کدومه؟",
    ])
    return caption, first


def colors(rng, names, winner):
    first_line = rng.choice([
        "قبل از اینکه ببینی یه رنگ انتخاب کن 👀",
        f"{or_fa(names)}؟ زود انتخاب کن 😁",
        "رنگتو انتخاب کردی؟ حالا تا آخرش ببین 👀",
    ])
    caption = f"{first_line}\n\nبعد بگو برد یا نه 👇\n\n#ریلز #satisfying #oddlysatisfying"
    first = f"{winner} برد 🏆\nتو کدومو انتخاب کرده بودی؟"
    return caption, first


def ring(rng, hits):
    first_line = rng.choice([
        "صدا رو زیاد کن 🔊",
        "تا آخرش ببین 👀",
        "اینو نمیشه نصفه ول کرد 😅",
        "حدس بزن چندبار می‌خوره به حلقه 🤔",
    ])
    second_line = rng.choice([
        "قبل از آخرش عددتو کامنت کن 👇",
        "بفرستش واسه کسی که حوصله‌ش سر رفته 😁",
        "سیوش کن واسه وقتایی که کلافه‌ای 📌",
    ])
    caption = f"{first_line}\n\n{second_line}\n\n#satisfying #oddlysatisfying #ریلز"
    first = f"جواب: {fa(hits)} بار 😁 حدست چند بود؟"
    return caption, first


def cup(rng, names, winner, round_name, info):
    a, b = names
    first_line = rng.choice([
        f"جام شهرها 🏆 {round_name}\n{a} یا {b}؟",
        f"{a} یا {b}؟ 🔥\nجام شهرها، {round_name}",
    ])
    second_line = rng.choice([
        "شهرت تو جدوله؟ فالو کن که بازیش از دستت نره 👇",
        "طرفدار کدومی؟ کامنت کن 👇",
        "شهرت نیست؟ کامنت کن، فصل بعد میاد 👇",
    ])
    caption = f"{first_line}\n\n{second_line}\n\n#جام_شهرها {tag(a)} {tag(b)} #ایران"
    if info["champion"]:
        first = f"🏆 {winner} قهرمان شد!\nفصل بعد کدوم شهرها باشن؟ کامنت کنید 👇"
    else:
        na, nb = info["next"]
        first = f"✅ {winner} رفت {info['advanced_to']}\n🔜 بازی بعد: {na} و {nb}\nشهر تو کجای جدوله؟ 👇"
    return caption, first


BASE_TAGS = ["ایران", "شبیه سازی", "simulation", "satisfying", "shorts"]


def youtube(fmt, names, round_name=None):
    """(title, tags) for the YouTube Short of a battle reel."""
    if fmt == "cup":
        title = f"{names[0]} یا {names[1]}؟ 🔥 جام شهرها | {round_name} #shorts"
        tags = ["جام شهرها"] + names
    elif fmt == "derby":
        title = "پرسپولیس یا استقلال؟ 🔴🔵 دربی توپ‌ها #shorts"
        tags = ["پرسپولیس", "استقلال", "دربی"]
    elif fmt == "cities":
        title = f"{or_fa(names)}؟ 🏙️ نبرد شهرها #shorts"
        tags = ["نبرد شهرها"] + names
    else:
        title = f"{or_fa(names)}؟ کدوم رنگ می‌بره؟ 🎨 #shorts"
        tags = ["رنگ"] + names
    return title[:100], tags + BASE_TAGS


# ---------------- English, for the YouTube World Cup of Countries ----------------
def _en_tag(name):
    return "#" + name.replace(" ", "")


def worldcup(rng, names, winner, round_name, info, next_names):
    """(description, pinned-comment idea) for a World Cup of Countries Short."""
    a, b = names
    hook = rng.choice([
        f"🌍 World Cup of Countries — {round_name}\n{a} vs {b}. Who takes it?",
        f"{a} or {b}? 🔥 World Cup of Countries, {round_name}",
        f"32 countries, one champion 🏆 Today: {a} vs {b}",
    ])
    ask = rng.choice([
        "Which country should win it all? Comment below 👇",
        "Is your country still in the cup? Tell me in the comments 👇",
        "Who are you cheering for? 👇",
    ])
    description = (f"{hook}\n\n{ask}\nSubscribe so you don't miss your country's next match!\n\n"
                   f"#worldcup #countries {_en_tag(a)} {_en_tag(b)} #simulation #satisfying #shorts")
    if info["champion"]:
        comment = f"🏆 {winner} are the champions! Which countries should be in next season?"
    else:
        comment = f"✅ {winner} advance to the {info['advanced_to']}\n🔜 Next: {next_names[0]} vs {next_names[1]}"
    return description, comment


def youtube_worldcup(rng, names, round_name):
    a, b = names
    title = rng.choice([
        f"{a} vs {b} 🔥 World Cup of Countries | {round_name} #shorts",
        f"{a} or {b}? Who wins? 🌍 {round_name} #shorts",
    ])
    tags = [a, b, "world cup of countries", "country battle", "countryballs", "which country wins",
            "simulation", "satisfying", "shorts"]
    return title[:100], tags
