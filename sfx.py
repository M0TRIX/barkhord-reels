"""Synthesized sound effects for barkhord.tv reels (no samples, so no copyright issues).

Every function returns a mono float numpy array at SR samples per second.
"""
import numpy as np
from scipy import signal

SR = 44100


def _t(sec):
    return np.arange(int(SR * sec)) / SR


def _noise(sec, seed=0):
    return np.random.default_rng(seed).normal(0, 1, int(SR * sec))


def _bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return signal.lfilter(b, a, x)


def _lowpass(x, f, order=2):
    b, a = signal.butter(order, f / (SR / 2), btype="low")
    return signal.lfilter(b, a, x)


def _highpass(x, f, order=2):
    b, a = signal.butter(order, f / (SR / 2), btype="high")
    return signal.lfilter(b, a, x)


def _norm(x, peak=1.0):
    return x / (np.abs(x).max() + 1e-9) * peak


def boom(sec=1.6, seed=1):
    """Deep explosion: falling sub sine plus a filtered noise blast."""
    t = _t(sec)
    sub = np.sin(2 * np.pi * (90 * t - 30 * t ** 2)) * np.exp(-t * 3.2)
    blast = _lowpass(_noise(sec, seed), 900) * np.exp(-t * 7)
    crack = _highpass(_noise(sec, seed + 1), 2500) * np.exp(-t * 40) * 0.6
    return _norm(sub * 1.2 + _norm(blast) * 0.8 + crack)


def whoosh(sec=0.55, seed=2, rising=True):
    """Rocket / wind whoosh: noise through a moving band."""
    t = _t(sec)
    n = _noise(sec, seed)
    out = np.zeros_like(n)
    steps = 12
    seg = len(n) // steps
    for k in range(steps):
        f = 300 + (2600 - 300) * ((k / steps) if rising else (1 - k / steps))
        part = _bandpass(n, f * 0.7, min(f * 1.3, SR / 2 - 100))
        out[k * seg:(k + 1) * seg] = part[k * seg:(k + 1) * seg]
    env = np.minimum(t / 0.05, 1) * np.minimum((sec - t) / 0.08, 1)
    return _norm(out * env)


def thunder(sec=1.2, seed=3):
    """Lightning: sharp crack then a low rumble."""
    t = _t(sec)
    crack = _highpass(_noise(sec, seed), 3000) * np.exp(-t * 55)
    rumble = _lowpass(_noise(sec, seed + 1), 180) * np.exp(-t * 2.5) * np.minimum(t / 0.05, 1)
    return _norm(_norm(crack) + _norm(rumble) * 0.9)


def pop(freq=700, sec=0.09):
    """Cartoon pop with a fast pitch drop."""
    t = _t(sec)
    f = freq * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-t * 35)


def rise(sec=0.6):
    """Power-up sweep."""
    t = _t(sec)
    return np.sin(2 * np.pi * (250 * t + 1100 * t ** 2)) * np.minimum(t / 0.02, 1) * np.exp(-t * 2.2)


def _formant_filter(x, formants):
    out = np.zeros_like(x)
    for fc, q, g in formants:
        b, a = signal.iirpeak(fc / (SR / 2), q)
        out += signal.lfilter(b, a, x) * g
    return out


def _voice_source(pitch, rng, rough=0.0):
    """Sawtooth-like glottal source following a pitch curve (Hz per sample)."""
    phase = 2 * np.pi * np.cumsum(pitch) / SR
    src = np.zeros_like(pitch)
    for n in range(1, 50):
        src += np.sin(n * phase) / n * (n * pitch < 5500)
    if rough:
        src *= 1 + rough * np.sin(phase / 2)           # sub-harmonic growl
    return src + rng.normal(0, 0.12, len(pitch))


def laugh(syllables=6, f0_start=105, f0_end=72, seed=4):
    """Deep evil laugh "MUA-HA-HA-HA-HA": voice source + /a/ formants, with a growl."""
    rng = np.random.default_rng(seed)
    pieces = []
    for k in range(syllables):
        frac = k / max(1, syllables - 1)
        f0 = f0_start + (f0_end - f0_start) * frac
        first = k == 0
        h_len = 0.03 if first else 0.07
        v_len = 0.34 if first else 0.15 + 0.02 * frac
        gap = 0.05 + 0.025 * frac
        nh = int(SR * h_len)
        h = rng.normal(0, 1, nh) * np.linspace(0.1, 0.9, nh)               # breathy "h"
        tv = _t(v_len)
        pitch = f0 * (1.12 - 0.22 * tv / v_len) * (1 + 0.015 * np.sin(2 * np.pi * 5.5 * tv))
        src = _voice_source(pitch, rng, rough=0.35)
        env = np.minimum(tv / 0.015, 1) * np.exp(-tv * (2.5 if first else 4.0))
        pieces.append(np.concatenate([h, src * env, np.zeros(int(SR * gap))]))
    x = np.concatenate(pieces)
    out = _formant_filter(x, ((720, 4.5, 1.0), (1150, 7, 0.6), (2500, 10, 0.25), (3400, 12, 0.08)))
    out = _lowpass(out, 4200) + 0.3 * _lowpass(x, 350)
    d1 = int(0.06 * SR)
    wet = np.zeros(len(out) + d1)
    wet[:len(out)] += out
    wet[d1:] += out * 0.2
    return _norm(np.tanh(_norm(wet) * 1.6))


def shout(seed=5, f0=165, sec=0.85):
    """Wrestler's "YEAAAH!": vowel glides from /e/ to /a/, pitch rises, gritty."""
    rng = np.random.default_rng(seed)
    t = _t(sec)
    pitch = f0 * (1 + 0.35 * np.minimum(t / 0.25, 1) - 0.12 * np.maximum(0, t - 0.5)) * (1 + 0.02 * np.sin(2 * np.pi * 7 * t))
    src = _voice_source(pitch, rng, rough=0.25)
    blk = int(0.02 * SR)
    out = np.zeros_like(src)
    zis = None
    for k0 in range(0, len(src), blk):
        f = min(1.0, (k0 / SR) / 0.22)
        F1, F2 = 420 + (760 - 420) * f, 2000 + (1200 - 2000) * f
        seg = src[k0:k0 + blk]
        acc = np.zeros_like(seg)
        coefs = [signal.iirpeak(F1 / (SR / 2), 4.5), signal.iirpeak(F2 / (SR / 2), 7), signal.iirpeak(2600 / (SR / 2), 10)]
        if zis is None:
            zis = [np.zeros(2) for _ in coefs]
        for i, ((b, a), g) in enumerate(zip(coefs, (1.0, 0.6, 0.25))):
            y, zis[i] = signal.lfilter(b, a, seg, zi=zis[i])
            acc += y * g
        out[k0:k0 + blk] = acc
    env = np.minimum(t / 0.03, 1) * np.minimum((sec - t) / 0.18, 1)
    out = np.tanh(_norm(out * env) * 2.2)
    return _norm(out)


def crowd(sec=3.0, seed=6):
    """Stadium roar: band-limited noise layers with wandering loudness."""
    rng = np.random.default_rng(seed)
    t = _t(sec)
    out = np.zeros(len(t))
    for lo, hi, g in ((200, 900, 1.0), (700, 2200, 0.7), (1800, 4000, 0.3)):
        n = _bandpass(rng.normal(0, 1, len(t)), lo, hi)
        am = 1 + 0.35 * np.sin(2 * np.pi * rng.uniform(1.5, 4) * t + rng.uniform(0, 6))
        out += _norm(n) * am * g
    swell = np.minimum(t / 0.6, 1) * np.minimum((sec - t) / 0.5, 1)
    return _norm(out * swell)


def bell(strikes=2):
    """Boxing ring bell: inharmonic partials, struck twice."""
    t = _t(1.6)
    one = sum(np.sin(2 * np.pi * 520 * m * t) * np.exp(-t * d) * g
              for m, d, g in ((1, 2.2, 1.0), (2.76, 3.5, 0.6), (5.4, 6, 0.35), (8.93, 9, 0.2)))
    out = np.zeros(int(SR * (1.6 + 0.3 * strikes)))
    for k in range(strikes):
        s0 = int(SR * 0.28 * k)
        out[s0:s0 + len(one)] += one
    return _norm(out)


def whistle(sec=0.7):
    """Referee whistle with a fast trill."""
    t = _t(sec)
    trill = 0.6 + 0.4 * np.sin(2 * np.pi * 28 * t)
    tone_ = (np.sin(2 * np.pi * 2900 * t) + 0.7 * np.sin(2 * np.pi * 3010 * t)) * trill
    breath = _bandpass(_noise(sec, 9), 2500, 4500) * 0.15
    env = np.minimum(t / 0.02, 1) * np.minimum((sec - t) / 0.06, 1)
    return _norm((tone_ + breath) * env)


def shatter(seed=10):
    """K.O. hit: crash plus glassy pings."""
    rng = np.random.default_rng(seed)
    t = _t(1.0)
    crash = _highpass(rng.normal(0, 1, len(t)), 2000) * np.exp(-t * 9)
    pings = np.zeros(len(t))
    for _ in range(14):
        s0 = int(rng.uniform(0, 0.25) * SR)
        f = rng.uniform(2500, 6500)
        L = int(0.25 * SR)
        tt = np.arange(L) / SR
        seg = pings[s0:s0 + L]
        seg += (np.sin(2 * np.pi * f * tt) * np.exp(-tt * 30))[: len(seg)] * rng.uniform(0.2, 0.5)
    return _norm(_norm(crash) + pings)


def sad_trombone():
    """"Wah wah wah waaah" for the loser."""
    notes = ((196, 0.32), (185, 0.32), (175, 0.32), (165, 1.0))
    out = []
    for k, (f, dur) in enumerate(notes):
        t = _t(dur)
        vib = 1 + (0.025 * np.sin(2 * np.pi * 6 * t) if k == 3 else 0)
        ph = 2 * np.pi * np.cumsum(f * vib * np.ones_like(t)) / SR
        saw = sum(np.sin(n * ph) / n for n in range(1, 25))
        wah = 0.4 + 0.6 * np.minimum(t / 0.12, 1)
        env = np.minimum(t / 0.03, 1) * np.minimum((dur - t) / 0.06, 1)
        out.append(_lowpass(saw * wah, 1600) * env)
    return _norm(np.concatenate(out))


def drum_loop(sec, bpm=128, frenzy_from=None, seed=15):
    """Simple driving beat (kick, clap, hats); hats double up from frenzy_from seconds."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(SR * (sec + 1)))
    beat = 60.0 / bpm
    kt = _t(0.25)
    kick = np.sin(2 * np.pi * np.cumsum(45 + 90 * np.exp(-kt * 30)) / SR) * np.exp(-kt * 12)
    hat = _highpass(rng.normal(0, 1, int(SR * 0.04)), 7000) * np.exp(-_t(0.04) * 90)
    clap = _bandpass(rng.normal(0, 1, int(SR * 0.12)), 900, 2500) * np.exp(-_t(0.12) * 35)
    def put(sig, t0, g):
        s0 = int(t0 * SR); seg = out[s0:s0 + len(sig)]; seg += sig[: len(seg)] * g
    t = 0.0
    k = 0
    while t < sec:
        put(kick, t, 1.0)
        if k % 2 == 1:
            put(_norm(clap), t, 0.45)
        fr = frenzy_from is not None and t >= frenzy_from
        for sub in ((0.0, 0.25, 0.5, 0.75) if fr else (0.5,)):
            put(_norm(hat), t + sub * beat, 0.35)
        t += beat
        k += 1
    return _norm(out[: int(SR * sec)])


def envelope(x, fps=30):
    """Loudness per video frame, 0..1 (to move a mouth in sync with a sound)."""
    hop = SR // fps
    n = len(x) // hop
    e = np.array([np.sqrt(np.mean(x[k * hop:(k + 1) * hop] ** 2)) for k in range(n)])
    return e / (e.max() + 1e-9)


if __name__ == "__main__":
    import sys, wave
    name = sys.argv[1]
    x = {"laugh": laugh, "boom": boom, "whoosh": whoosh, "thunder": thunder, "rise": rise, "shout": shout,
         "crowd": crowd, "bell": bell, "whistle": whistle, "shatter": shatter, "trombone": sad_trombone}[name]()
    with wave.open(sys.argv[2], "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((_norm(x, 0.9) * 32767).astype(np.int16).tobytes())


def clang(seed=16):
    """Giant hammer hit: heavy thud plus a ringing metal clang."""
    rng = np.random.default_rng(seed)
    t = _t(1.6)
    thud = np.sin(2 * np.pi * (70 * t - 18 * t ** 2)) * np.exp(-t * 5)
    ring = np.zeros(len(t))
    for f, g, dec in ((523, 1.0, 4.5), (1187, 0.6, 6), (1871, 0.45, 8), (2793, 0.3, 11), (3540, 0.2, 14)):
        ring += g * np.sin(2 * np.pi * f * rng.uniform(0.98, 1.02) * t) * np.exp(-t * dec)
    hit = _highpass(rng.normal(0, 1, len(t)), 1500) * np.exp(-t * 45)
    return _norm(_norm(thud) * 1.1 + _norm(ring) * 0.55 + _norm(hit) * 0.5)


def shield_up(sec=0.45):
    """Energy shield powering up: a fast rising shimmer."""
    t = _t(sec)
    f = 300 + 900 * (t / sec) ** 0.7
    ph = 2 * np.pi * np.cumsum(f) / SR
    tone = np.sin(ph) + 0.5 * np.sin(2.01 * ph) + 0.3 * np.sin(3.02 * ph)
    trem = 0.7 + 0.3 * np.sin(2 * np.pi * 28 * t)
    env = np.minimum(t / 0.03, 1) * np.minimum((sec - t) / 0.08, 1)
    return _norm(tone * trem * env)


def rain(sec=2.0, seed=17):
    """Steady rain: band-passed hiss with soft random drops, fading in and out."""
    rng = np.random.default_rng(seed)
    t = _t(sec)
    hiss = _bandpass(rng.normal(0, 1, len(t)), 1200, 7000)
    drops = np.zeros(len(t))
    for _ in range(int(sec * 60)):
        s0 = rng.integers(0, max(1, len(t) - 800))
        L = 600
        drops[s0:s0 + L] += np.sin(2 * np.pi * rng.uniform(2000, 4500) * np.arange(L) / SR) * np.exp(-np.arange(L) / SR * 220) * rng.uniform(0.2, 0.6)
    env = np.minimum(t / 0.25, 1) * np.minimum((sec - t) / 0.4, 1)
    return _norm((_norm(hiss) * 0.7 + _norm(drops) * 0.4) * env)


def thunderclap(sec=2.2, seed=18):
    """Close lightning strike: a crack, a boom and a long rolling rumble."""
    t = _t(sec)
    crack = _highpass(_noise(sec, seed), 2500) * np.exp(-t * 35)
    boom_ = np.sin(2 * np.pi * (60 * t - 12 * t ** 2)) * np.exp(-t * 4)
    roll = _lowpass(_noise(sec, seed + 1), 140) * (0.6 + 0.4 * np.sin(2 * np.pi * 3.3 * t)) * np.exp(-t * 1.4) * np.minimum(t / 0.08, 1)
    return _norm(_norm(crack) * 0.9 + _norm(boom_) * 0.8 + _norm(roll) * 1.0)
