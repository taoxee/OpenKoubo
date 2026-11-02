#!/usr/bin/env python3
"""make_packaging.py — 包装层：钩子片头大标题 + AI 数字人标识角标（HyperFrames 透明层）。

用法：python3 make_packaging.py <out_dir> [--width 720 --height 1280] [--duration 9.2]
      --hook "标题" --sub "副标题" [--badge "内容由 AI 数字人演绎"]

产出：out_dir/index.html（data-no-timeline，HyperFrames 可渲染）
设计：竖屏口播包装——
- 钩子卡：前 1.8s，顶部大标题（两行内）+ 副标题，左对齐，白字+品牌色强调条，淡入上移
- AI 角标：全片右上角小胶囊，半透明黑底白字
- 结尾 CTA：最后 2s 底部「点赞关注」条（可选 --cta）
"""
import argparse
import html


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--height", type=int, default=1280)
    ap.add_argument("--duration", type=float, default=9.2)
    ap.add_argument("--hook", default="一张照片\n一句台词\n生成口播视频")
    ap.add_argument("--sub", default="数字人工作流 · 无需出镜")
    ap.add_argument("--badge", default="", help="已弃用：AI 角标按用户要求移除，发布时在平台勾选 AI 声明")
    args = ap.parse_args()

    hook_lines = [l for l in args.hook.split("\n") if l.strip()]
    hook_html = "".join(f'<div class="hk-line">{html.escape(l)}</div>' for l in hook_lines)

    doc = f'''<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>packaging</title>
<style>
  @font-face {{ font-family: "PingFang SC"; src: local("PingFang SC"); }}
  @font-face {{ font-family: "Hiragino Sans GB"; src: local("Hiragino Sans GB"); }}
  @font-face {{ font-family: "Microsoft YaHei"; src: local("Microsoft YaHei"); }}
  html, body {{
    margin: 0; padding: 0; background: transparent;
    width: {args.width}px; height: {args.height}px; overflow: hidden;
    font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  }}
  .stage {{
    position: relative; width: {args.width}px; height: {args.height}px;
    background: transparent;
  }}
  /* 钩子卡：前 1.8s（贴顶部，避开人脸中轴） */
  .hook-card {{
    position: absolute; left: 36px; top: {int(args.height * 0.055)}px;
    padding: 18px 26px 16px;
    background: linear-gradient(135deg, rgba(16,16,20,0.82), rgba(16,16,20,0.62));
    border-left: 6px solid #FF4D6A;
    border-radius: 14px;
    max-width: {int(args.width * 0.70)}px;
    box-shadow: 0 12px 40px rgba(0,0,0,0.45);
  }}
  .hk-line {{
    font-size: {int(args.width * 0.068)}px;
    font-weight: 900; color: #FFFFFF;
    line-height: 1.25; letter-spacing: 1px;
    text-shadow: 0 2px 12px rgba(0,0,0,0.6);
  }}
  .hk-sub {{
    margin-top: 10px;
    font-size: {int(args.width * 0.032)}px;
    font-weight: 600; color: rgba(255,255,255,0.85);
    letter-spacing: 2px;
  }}
  /* AI 角标已按用户要求移除（2026-11-02）：发布时在平台页勾选「AI 生成」声明即可 */
</style>
</head>
<body>
  <div class="stage" data-composition-id="packaging" data-no-timeline
       data-width="{args.width}" data-height="{args.height}"
       data-duration="{args.duration}" data-fps="30">

    <div class="clip" data-start="0.2" data-duration="1.6" data-track-index="1">
      <div class="hook-card">
        {hook_html}
        <div class="hk-sub">{html.escape(args.sub)}</div>
      </div>
    </div>

  </div>
</body>
</html>'''

    from pathlib import Path
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(doc)
    print(f"packaging comp -> {out}/index.html ({args.duration}s, hook {len(hook_lines)} lines)")


if __name__ == "__main__":
    main()
