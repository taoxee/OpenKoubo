#!/usr/bin/env bash
# finalize.sh — 三层合成 + BGM 混音出终版（包装出片主脚本）
set -e
cd "$(dirname "$0")"

# 1. 重建包装层（钩子卡上移避脸版；标题手动两行断句，避免「生成」被自动换行拆开）
python3 ../../scripts/make_packaging.py assets/packaging/comp --duration 9.27 \
  --hook $'一张照片 一句台词\n生成口播视频' --sub "数字人工作流 · 无需出镜"
(cd assets/packaging/comp && npx hyperframes render . --format mov -o ../packaging_overlay.mov --quiet)

# 2. 画面三层叠加：底片(带字幕) + 包装层
ffmpeg -y -v error -i assets/成片_带字幕.mp4 -i assets/packaging/packaging_overlay.mov \
  -filter_complex "[0:v][1:v]overlay=0:0:format=auto" \
  -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -an assets/成片_三层画面.mp4

# 3. 混音：人声(原片) + BGM(-20dB 淡入淡出) → -16 LUFS
ffmpeg -y -v error -i assets/成片_三层画面.mp4 -i assets/audio/bgm.mp3 -i assets/成片_完整版.mp4 \
  -filter_complex "[1:a]volume=-20dB,afade=t=in:st=0:d=0.5,afade=t=out:st=7.7:d=1.4[bgm];[2:a][bgm]amix=inputs=2:duration=first:dropout_transition=3,volume=1.6,loudnorm=I=-16:TP=-1.5:LRA=11[aout]" \
  -map 0:v -map "[aout]" -c:v copy -c:a aac -b:a 192k assets/成片_终版.mp4

# 4. 抽帧终检素材
ffmpeg -y -v error -i assets/成片_终版.mp4 -vf "select='eq(n,30)+eq(n,110)+eq(n,200)'" -fps_mode vfr /tmp/final_v2_%d.jpg
echo "FINALIZED: assets/成片_终版.mp4"
ffprobe -v error -show_entries format=duration,size -of csv=p=0 assets/成片_终版.mp4
