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


def laugh(syllables=6, f0_start=118, f0_end=82, seed=4):
    """Deep, slow villain laugh ("HA... HA... HA..."), made with a voice source and vowel formants."""
    rng = np.random.default_rng(seed)
    pieces = []
    for k in range(syllables):
        frac = k / max(1, syllables - 1)
        f0 = f0_start + (f0_end - f0_start) * frac
        h_len, v_len = 0.05, 0.17 + 0.03 * frac
        gap = 0.07 + 0.03 * frac
        # aspiration "h"
        h = rng.normal(0, 1, int(SR * h_len)) * np.linspace(0.05, 0.35, int(SR * h_len))
        # voiced "a": sawtooth-like source with a falling pitch and a little jitter
        tv = _t(v_len)
        pitch = f0 * (1.08 - 0.16 * tv / v_len) * (1 + 0.012 * np.sin(2 * np.pi * 6 * tv))
        phase = 2 * np.pi * np.cumsum(pitch) / SR
        src = np.zeros_like(tv)
        for n in range(1, 45):
            src += np.sin(n * phase) / n * (n * f0 < 5000)
        src += rng.normal(0, 0.15, len(tv))                          # breathiness
        env = np.minimum(tv / 0.012, 1) * np.exp(-tv * 4.5)
        voiced = src * env
        syl = np.concatenate([h, voiced, np.zeros(int(SR * gap))])
        pieces.append(syl)
    x = np.concatenate(pieces)
    # vowel /a/ formants, a bit darker than usual for a deep voice
    out = np.zeros_like(x)
    for fc, q, g in ((620, 5.5, 1.0), (1050, 8, 0.55), (2400, 12, 0.22), (3300, 14, 0.08)):
        b, a = signal.iirpeak(fc / (SR / 2), q)
        out += signal.lfilter(b, a, x) * g
    out = _lowpass(out, 3800) + 0.25 * _lowpass(x, 400)      # body
    # small room
    d1, d2 = int(0.045 * SR), int(0.11 * SR)
    wet = np.zeros(len(out) + d2)
    wet[:len(out)] += out
    wet[d1:d1 + len(out)] += out * 0.35
    wet[d2:d2 + len(out)] += out * 0.18
    return _norm(wet)


if __name__ == "__main__":
    import sys, wave
    name = sys.argv[1]
    x = {"laugh": laugh, "boom": boom, "whoosh": whoosh, "thunder": thunder, "rise": rise}[name]()
    with wave.open(sys.argv[2], "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes((_norm(x, 0.9) * 32767).astype(np.int16).tobytes())
