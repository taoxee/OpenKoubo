#!/usr/bin/env python3
"""qc_check.py — 口播片段本地质检（Renoise→OM 替换版的回听替代）。

dashscope_asr 只吃公网 URL（本地文件不收），本地回听改用：
1. 能量门限 VAD：语音区间占比、起止点（是否吞头/拖尾）
2. 预期时长 vs 实际时长比对（按 5.4 字/秒估算）
3. （可选）dashscope_asr 传公网 URL 时做逐字比对

用法：python3 qc_check.py <video.mp4> [expected_text]
"""
import array, json, math, re, subprocess, sys, tempfile, wave
from pathlib import Path


def audio_rms_buckets(wav_path: str, bucket_sec: float = 0.25):
    w = wave.open(wav_path)
    n, rate = w.getnframes(), w.getframerate()
    data = array.array("h", w.readframes(n))
    dur = n / rate
    seg = int(rate * bucket_sec)
    buckets = []
    for i in range(0, n, seg):
        chunk = data[i : i + seg]
        rms = math.sqrt(sum(x * x for x in chunk) / max(1, len(chunk)))
        buckets.append((i / rate, rms))
    return buckets, dur


def vad(buckets, thresh=800):
    speech = [(t, r) for t, r in buckets if r > thresh]
    if not speech:
        return None, 0
    start = speech[0][0]
    end = speech[-1][0] + 0.25
    ratio = len(speech) / len(buckets)
    return (start, end), ratio


def main():
    video = Path(sys.argv[1])
    expected = sys.argv[2] if len(sys.argv) > 2 else None
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav = f.name
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-vn",
         "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", wav],
        check=True,
    )
    buckets, dur = audio_rms_buckets(wav)
    (span), ratio = vad(buckets)
    report = {
        "file": str(video),
        "duration_sec": round(dur, 2),
        "video_spec": subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height", "-of", "csv=p=0", str(video)],
            capture_output=True, text=True).stdout.strip(),
        "speech_span": [round(span[0], 2), round(span[1], 2)] if span else None,
        "speech_ratio": round(ratio, 2),
        "head_silence_sec": round(span[0], 2) if span else None,
        "tail_silence_sec": round(dur - span[1], 2) if span else None,
    }
    if expected:
        chars = len(re.sub(r"[\s，。、：；！？,.:;!?“”]", "", expected))
        est = chars / 5.4 + 1.0
        report["expected_chars"] = chars
        report["expected_dur_est"] = round(est, 2)
        report["dur_delta"] = round(dur - est, 2)
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
