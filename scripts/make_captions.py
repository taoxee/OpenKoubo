#!/usr/bin/env python3
"""make_captions.py — 原稿文本 + whisper 词级时间轴 → HyperFrames 透明字幕层。

做法（OM skill 验证配方）：
- 显示文本一律用 script.json 原稿（whisper 只给时间轴，不信任它的文本）
- cue = 一句（按标点切）；词时间戳从 words.json 线性对齐到原稿字符
- HyperFrames 根元素 data-composition-id data-width data-height data-duration data-fps
- 每句一个 .clip（data-start data-duration data-track-index），白粗字+多向 text-shadow 描边
- 竖屏 9:16：字号大（54px @720x1280），底部上方留 safe-area

用法：python3 make_captions.py <script.json> <words.json> <out_dir> [--width 720 --height 1280]
"""
import html
import json
import re
import sys
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text())


def split_sentences(text):
    parts = re.split(r"([。！？!?；;])", text)
    sents, cur = [], ""
    for p in parts:
        cur += p
        if p in "。！？!?；;":
            sents.append(cur)
            cur = ""
    if cur.strip():
        sents.append(cur)
    return [s.strip() for s in sents if s.strip()]


# 常见词组表（换行切点避开词组中间）
COMMON_WORDS = set("照片 视频 口播 数字 主播 大家 一句 一张 生成 这样 教程 时间 画面 声音 内容 学习 工具 方法 步骤 一条 一步 一款 一下 一种 我们 你们 他们 自己 现在 今天 开始 最后 简单 快速 轻松 口播视频 数字人 一张照片 一句话 大家好".split())


def _word_crosses_cut(text, pos):
    """切点 pos 是否把某个词组拦腰切开（text[:pos] 以 w 的真前缀结尾且剩余部分在后）。"""
    for w in COMMON_WORDS:
        for k in range(1, len(w)):
            if text[:pos].endswith(w[:k]) and text[pos : pos + len(w) - k] == w[k:]:
                return True
    return False


def wrap_no_word_split(chars, per_line):
    """每行 ≤ per_line 字：优先在标点处断；行满时回退避开词组中间。"""
    text = "".join(chars)
    lines, rest = [], text
    while len(rest) > per_line:
        cut = per_line
        puncts = [i for i, c in enumerate(rest[:cut]) if c in "，。、；！？"]
        if puncts and puncts[-1] >= max(4, cut - 7):
            cut = puncts[-1] + 1
        else:
            back = 0
            while back < 3 and _word_crosses_cut(rest, cut - back):
                back += 1
            cut -= back
        # 标点悬挂修正：若切点后紧跟标点，把它并进上一行（标点不能落在行首）
        while cut < len(rest) and rest[cut] in "，。、；！？":
            cut += 1
        lines.append(rest[:cut])
        rest = rest[cut:]
    if rest:
        lines.append(rest)
    return lines


def main():
    script = load(sys.argv[1])  # [{"id","t",...}]
    words_meta = load(sys.argv[2])  # {"words":[...], "text": ...}
    out_dir = Path(sys.argv[3])
    width = int(sys.argv[sys.argv.index("--width") + 1]) if "--width" in sys.argv else 720
    height = int(sys.argv[sys.argv.index("--height") + 1]) if "--height" in sys.argv else 1280

    words = words_meta["words"]
    total_dur = max(w["end"] for w in words) + 0.3

    # 原稿全文（按 script 段顺序）
    full_text = "".join(s["t"] for s in script)
    spoken_chars = len(re.sub(r"[\s，。、：；！？,.:;!?“”]", "", full_text))

    # whisper 词序列 → 字符时间轴：把每个词的字符摊到 [start,end]
    char_times = []
    for w in words:
        chars = re.sub(r"\s", "", w["word"])
        n = len(chars)
        if n == 0:
            continue
        span = max(0.01, w["end"] - w["start"])
        for i, c in enumerate(chars):
            t0 = w["start"] + span * i / n
            t1 = w["start"] + span * (i + 1) / n
            char_times.append((c, t0, t1))

    # 原稿字符序列（去标点空白）与 char_times 顺序对齐（一一对应；长度不等时按比例映射）
    src_chars = [c for c in full_text if c not in " \t\n，。、：；！？,.:;!?“”"]
    if len(char_times) != len(src_chars):
        # 按序号比例重采样 char_times 到 src_chars 长度（whisper 漏字/多字时兜底）
        n = len(src_chars)
        m = len(char_times)
        resampled = []
        for i in range(n):
            j = int(i * m / n)
            resampled.append(char_times[j])
        char_times = resampled

    # 句子 cue：句内字符的时间范围 + 逐词高亮时间
    cues = []
    char_idx = 0
    for s in script:
        for sent in split_sentences(s["t"]):
            sent_chars = [c for c in sent if c not in "，。、：；！？,.:;!?“” "]
            n = len(sent_chars)
            if n == 0:
                continue
            seg = char_times[char_idx : char_idx + n]
            char_idx += n
            if not seg:
                continue
            start = seg[0][1]
            end = seg[-1][2]
            word_karaoke = [(c, t0, t1) for (c, t0, t1) in seg]
            cues.append({
                "text": sent,
                "start": round(start, 3),
                "end": round(end + 0.15, 3),
                "karaoke": word_karaoke,
            })

    # 生成 HyperFrames HTML
    clips = []
    for i, cue in enumerate(cues):
        dur = round(cue["end"] - cue["start"], 3)
        # 换行：每行字数按实际可用宽度算（字号、padding 内缩），避免浏览器自动换行与 <br> 打架
        font_px = int(width * 0.075)
        avail_px = int(width * 0.92) - 52  # max-width 减左右 padding
        per_line = max(8, avail_px // font_px)
        chars = list(cue["text"])
        lines = wrap_no_word_split(chars, per_line)
        text_html = "<br>".join(html.escape(ln) for ln in lines)
        clips.append(f'''
      <div class="clip caption" data-start="{cue['start']}" data-duration="{dur}" data-track-index="1">
        <div class="cap-text">{text_html}</div>
      </div>''')

    html_doc = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>captions</title>
<style>
  html, body {{
    margin: 0;
    padding: 0;
    background: transparent;
    width: {width}px;
    height: {height}px;
    overflow: hidden;
    font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  }}
  .stage {{
    position: relative;
    width: {width}px;
    height: {height}px;
    background: transparent;
  }}
  .caption {{
    position: absolute;
    left: 0;
    right: 0;
    bottom: {int(height * 0.16)}px;
    display: flex;
    justify-content: center;
    align-items: center;
  }}
  .cap-text {{
    font-size: {int(width * 0.075)}px;
    font-weight: 800;
    color: #FFFFFF;
    text-align: center;
    line-height: 1.35;
    padding: 14px 26px;
    max-width: {int(width * 0.92)}px;
    background: rgba(0, 0, 0, 0.45);
    border-radius: 12px;
    text-shadow:
      2px 0 0 #000, -2px 0 0 #000, 0 2px 0 #000, 0 -2px 0 #000,
      2px 2px 0 #000, -2px 2px 0 #000, 2px -2px 0 #000, -2px -2px 0 #000,
      0 4px 10px rgba(0,0,0,0.5);
    box-decoration-break: clone;
    -webkit-box-decoration-break: clone;
  }}
  @font-face {{
    font-family: "PingFang SC";
    src: local("PingFang SC");
  }}
  @font-face {{
    font-family: "Hiragino Sans GB";
    src: local("Hiragino Sans GB");
  }}
  @font-face {{
    font-family: "Microsoft YaHei";
    src: local("Microsoft YaHei");
  }}
</style>
</head>
<body>
  <div class="stage" data-composition-id="captions" data-no-timeline
       data-width="{width}" data-height="{height}"
       data-duration="{round(total_dur, 2)}" data-fps="30">
{''.join(clips)}
  </div>
</body>
</html>'''

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html_doc)
    # 同时导出 SRT（发布用软字幕）
    srt = []
    for i, cue in enumerate(cues, 1):
        def ts(t):
            h = int(t // 3600); m = int(t % 3600 // 60); s = int(t % 60); ms = int((t % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        srt.append(f"{i}\n{ts(cue['start'])} --> {ts(cue['end'])}\n{cue['text']}\n")
    (out_dir.parent / "subtitles.srt").write_text("\n".join(srt))
    print(f" cues={len(cues)} total={total_dur:.2f}s -> {out_dir}/index.html + subtitles.srt")


if __name__ == "__main__":
    main()
