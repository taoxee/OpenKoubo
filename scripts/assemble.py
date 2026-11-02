#!/usr/bin/env python3
"""assemble.py — 拼接口播片段（简化移植自原仓库 assemble.py，去 whisper 依赖）。

替换说明：
- 原版回听用 whisper.cpp + medium 模型；本机无模型文件，回听改走 qc_check.py 的
  VAD 时长校验（dashscope_asr 只收公网 URL，本地文件不适用；要逐字比对时把视频
  传公网后用 OM dashscope_asr）。
- 核心保留：拼接前每段「音频补齐到画面等长」（PCM .mov 中转），防几十段累积
  音画漂移（原项目实测 44 段漂 0.38s 的坑）+ loudnorm -16。

用法：
  python3 assemble.py script.json <视频目录> --out 成片.mp4
  script.json: [{"id","t",...}]；视频目录里放 <id>.mp4
"""
import json, re, subprocess, sys
from pathlib import Path

a = sys.argv[1:]
if len(a) < 2:
    sys.exit(__doc__)
S = json.loads(Path(a[0]).read_text())
vdir = Path(a[1])
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
out_name = opt("--out", "成片_完整版.mp4")

cut = vdir.parent / "cut"
cut.mkdir(exist_ok=True)
concat_list = cut / "list.txt"
concat_lines = []

for s in S:
    sid = s["id"]
    src = vdir / f"{sid}.mp4"
    if not src.exists():
        sys.exit(f"缺片段: {src}")
    # 1) 音频补齐到画面等长（PCM 中转，防累积漂移）
    tmp_mov = cut / f"{sid}_pad.mov"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(src),
         "-c:v", "copy", "-c:a", "pcm_s16le", "-af", "apad",
         "-shortest", str(tmp_mov)],
        check=True,
    )
    # 2) 统一规格 30fps 48k 立体声
    seg = cut / f"{sid}.mp4"
    subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(tmp_mov),
         "-vf", "fps=30,format=yuv420p",
         "-af", "aresample=48000", "-ac", "2",
         "-c:v", "libx264", "-crf", "17", "-preset", "medium",
         "-c:a", "aac", "-b:a", "192k", str(seg)],
        check=True,
    )
    # 3) 验证音画等长（核心质检）
    vd = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=duration", "-of", "csv=p=0", str(seg)],
        capture_output=True, text=True).stdout)
    ad = float(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=duration", "-of", "csv=p=0", str(seg)],
        capture_output=True, text=True).stdout)
    drift = abs(vd - ad)
    flag = "⚠" if drift > 0.05 else " "
    print(f"{flag}{sid:5s} 画面 {vd:.2f}s / 声音 {ad:.2f}s (Δ{drift*1000:.0f}ms)")
    concat_lines.append(f"file '{seg.resolve()}'")
    tmp_mov.unlink(missing_ok=True)

concat_list.write_text("\n".join(concat_lines) + "\n")
out = vdir.parent / out_name
subprocess.run(
    ["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0",
     "-i", str(concat_list), "-c:v", "libx264", "-crf", "17", "-preset", "medium",
     "-c:a", "aac", "-b:a", "192k", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
     str(out)],
    check=True,
)
dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
    "-of", "csv=p=0", str(out)], capture_output=True, text=True).stdout.strip()
print(f"拼接完成: {out} ({float(dur):.1f}s, -16 LUFS)")
