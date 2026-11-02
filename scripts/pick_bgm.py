#!/usr/bin/env python3
"""pick_bgm.py — Pixabay 曲库挑一段 BGM 并下载（OM PixabayMusic 封装）。

用法：python3 pick_bgm.py <out.mp3> [--q "light upbeat"] 
"""
import os
import sys

# OpenMontage 仓库位置：优先 OM_HOME 环境变量，默认本机约定路径
OM = os.environ.get("OM_HOME") or os.path.expanduser("~/Documents/Projects/AIGC/OpenMontage")


def main():
    out = sys.argv[1]
    q = sys.argv[sys.argv.index("--q") + 1] if "--q" in sys.argv else "light upbeat technology background"
    sys.path.insert(0, OM)
    import dotenv
    dotenv.load_dotenv(f"{OM}/.env")
    from tools.tool_registry import registry
    registry.discover()
    tool = registry.get("pixabay_music")
    r = tool.execute({"query": q, "min_duration": 12, "max_duration": 60, "output_path": out})
    if not r.success:
        sys.exit(f"search failed: {r.error}")
    d = r.data or {}
    print("picked:", d.get("track_title"), "|", d.get("artist"), "|", d.get("duration_seconds"), "s |", d.get("license"))
    print("saved:", d.get("output"))


if __name__ == "__main__":
    main()
