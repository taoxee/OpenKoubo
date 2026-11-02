#!/usr/bin/env python3
"""transcribe_words.py — faster-whisper 词级时间轴（OM skill 验证过的 av 兼容修法：传数组不传路径）。

用法：/tmp/dh_captionenv/bin/python transcribe_words.py <video_or_audio> <out.json> [lang]
输出：{words: [{word, start, end}], text, language}
"""
import json, subprocess, sys, tempfile
from pathlib import Path

from faster_whisper import WhisperModel


def main():
    src = sys.argv[1]
    out = sys.argv[2]
    lang = sys.argv[3] if len(sys.argv) > 3 else "zh"
    wav = tempfile.mktemp(suffix=".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", wav],
        check=True,
    )
    import soundfile as sf

    audio, sr = sf.read(wav, dtype="float32")
    Path(wav).unlink(missing_ok=True)
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segs, info = model.transcribe(audio, language=lang, word_timestamps=True, vad_filter=True)
    words = []
    text_parts = []
    for seg in segs:
        text_parts.append(seg.text)
        for w in (seg.words or []):
            words.append({"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)})
    Path(out).write_text(
        json.dumps({"words": words, "text": "".join(text_parts).strip(), "language": lang}, ensure_ascii=False, indent=1)
    )
    print(f"words={len(words)} lang={info.language} text={''.join(text_parts).strip()[:60]}")


if __name__ == "__main__":
    main()
