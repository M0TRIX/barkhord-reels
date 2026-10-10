"""Each city's catchphrases in its own dialect, shown as speech bubbles.

city: (shout in the intro, taunt after winning). Keep them friendly local pride,
never jokes that mock a city or an ethnic group. A city that is not listed
simply gets no bubble. The owner checks every line before it goes out.
"""
LINES = {
    "تبریز": ("یاشاسین تبریز!", "قارداش، گؤردون؟"),
    "تهران": ("بچه طهرون باخت نمیده!", "داداش، کم آوردی؟"),
    "شیراز": ("کاکو، بیا جلو!", "کاکو، دیدی چه کردیم؟"),
    "مشهد": ("ها، مو آمدُم!", "ها والا، بُردُم!"),
    # plain colloquial Persian until the owner sends real Nahavandi lines
    "نهاوند": ("نهاوند اومده!", "دیدی نهاوند چیکار کرد؟"),
    "زنجان": ("یاشاسین زنجان!", "قارداش، گؤردون؟"),
    "اصفهان": ("اصفهون نصف جهونه!", "نصف جهون مال ما شد!"),
    # plain colloquial Persian until the owner sends real Lori / Bakhtiari lines
    "خرم‌آباد": ("خرم‌آباد اومده!", "دیدی خرم‌آباد چیکار کرد؟"),
    "بروجن": ("بروجن اومده!", "دیدی بروجن چیکار کرد؟"),
}


def lines(city):
    return LINES.get(city)
