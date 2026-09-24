"""落ち着いたニュース／ビジネス系BGMを自前で合成する（権利フリー・毎回同じ音）。

  python3 -m tools.akari_news.bgm OUT.wav [--sec 64]

構成：柔らかいパッド（maj9系の和音）＋控えめなピアノ風アルペジオ＋ごく小さい低音。
テンポ 80、4小節で1周（ループ可能）。ドラムなし、主張しない音量。
本番で既製のライブラリ曲を使う場合は video.py --bgm にそのファイルを渡せばよい。
"""
import argparse
import subprocess
import wave

import numpy as np

SR = 48000
BPM = 80
BEAT = 60 / BPM
# C maj9 → A m9 → F maj9 → G6(9)
CHORDS = [
    [48, 55, 59, 62, 64],
    [45, 52, 55, 59, 60],
    [41, 48, 52, 55, 57],
    [43, 50, 52, 55, 57],
]


def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def pad(freqs, sec, rng):
    t = np.arange(int(SR * sec)) / SR
    out = np.zeros((len(t), 2))
    for f in freqs:
        for det, pan in ((-0.004, 0.3), (0.004, 0.7)):
            ph = rng.uniform(0, 2 * np.pi)
            w = np.sin(2 * np.pi * f * (1 + det) * t + ph) + 0.18 * np.sin(2 * np.pi * 2 * f * (1 + det) * t + ph)
            out[:, 0] += w * (1 - pan)
            out[:, 1] += w * pan
    env = np.minimum(1, t / 1.2) * np.minimum(1, (sec - t) / 1.0)
    return out * env[:, None] / len(freqs)


def pluck(f, sec):
    t = np.arange(int(SR * sec)) / SR
    env = np.exp(-t * 3.5) * np.minimum(1, t / 0.005)
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.1 * np.sin(2 * np.pi * 3 * f * t)) * env


def lowpass(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.zeros_like(x)
    acc = np.zeros(x.shape[1])
    for i in range(len(x)):  # 1次のローパス（こもらせて柔らかくする）
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def render(sec=64.0, seed=7):
    rng = np.random.default_rng(seed)
    bar = BEAT * 4
    n = int(SR * sec)
    out = np.zeros((n, 2))
    i = 0
    t0 = 0.0
    while t0 < sec:
        ch = CHORDS[i % len(CHORDS)]
        seg = pad([hz(m + 12) for m in ch[1:]], bar * 1.15, rng) * 0.55
        s0 = int(SR * t0)
        e0 = min(n, s0 + len(seg))
        out[s0:e0] += seg[: e0 - s0]
        # 低音（ルート、ごく小さく）
        bass = pad([hz(ch[0])], bar * 1.1, rng) * 0.35
        e1 = min(n, s0 + len(bass))
        out[s0:e1] += bass[: e1 - s0]
        # アルペジオ（8分音符、ところどころ休む）
        notes = [ch[1] + 24, ch[2] + 24, ch[3] + 24, ch[4] + 24, ch[3] + 24, ch[2] + 24, ch[4] + 24, ch[3] + 24]
        for k, m in enumerate(notes):
            if rng.random() < 0.25:
                continue
            st = int(SR * (t0 + k * BEAT / 2))
            p = pluck(hz(m), 1.2) * (0.16 + 0.04 * rng.random())
            e = min(n, st + len(p))
            if st < n:
                pan = 0.35 + 0.3 * rng.random()
                out[st:e, 0] += p[: e - st] * (1 - pan)
                out[st:e, 1] += p[: e - st] * pan
        t0 += bar
        i += 1
    out = lowpass(out, 3500)
    fade = int(SR * 2.0)
    out[:fade] *= np.linspace(0, 1, fade)[:, None]
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return out / (np.abs(out).max() + 1e-9) * 0.7


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--sec", type=float, default=64.0)
    a = ap.parse_args(argv)
    x = render(a.sec)
    tmp = a.out + ".raw.wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    from .video import ffmpeg
    # ラウドネスを -16 LUFS に揃える（video.py 側で声の下にさらに下げる）
    subprocess.run([ffmpeg(), "-y", "-hide_banner", "-loglevel", "error", "-i", tmp, "-af",
                    "loudnorm=I=-16:TP=-2:LRA=7", "-ar", str(SR), a.out], check=True)
    import os
    os.remove(tmp)
    print("wrote", a.out)


if __name__ == "__main__":
    main()
