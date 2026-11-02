#!/usr/bin/env python3
"""build_tasks.py — 口播稿 script.json → Seedance 分段任务清单 + 费用预估（Renoise→OM 替换版）。

不再产出 Renoise create_tasks 数组，而是产出直接可执行的 OM seedance_ark 任务清单：
  [{id, shot, text, duration, resolution, prompt}, ...]
费用按 OM cost guard 规则预估（480p: mini=23 / fast=37 CNY/M-token；720p fast $0.13/s）。

用法：
  python3 build_tasks.py script.json out_tasks.json [--purpose "..."] [--all-720p] [--host me]
"""
import json, math, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
P = json.loads((HERE / "persona" / "persona.json").read_text())

def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default

def estimate(duration, resolution, variant="mini"):
    """粗估费用：480p 按 CNY/M-token 参考价，720p fast 按 $0.13/s。"""
    if resolution == "480p":
        # 480p 参考价（CNY / M-token）：mini 23, fast 37 → 按经验每秒约 4M token 粗估
        per_sec = (23 if variant == "mini" else 37) / 1.0
        return duration * per_sec / 4.0
    else:
        return duration * 0.13 * 7.2  # $0.13/s → CNY（≈7.2 汇率粗估）

def main():
    src, dst = sys.argv[1], sys.argv[2]
    purpose = arg("--purpose", "explaining clearly")
    all720 = "--all-720p" in sys.argv
    S = json.loads(Path(src).read_text())
    tasks, total = [], 0.0
    for s in S:
        lang = s.get("lang", "Mandarin Chinese")
        if lang.startswith("Mandarin") or lang == "Chinese":
            d = math.ceil(len(re.sub(r"[\s，。、：；！？,.:;!?“”]", "", s["t"])) / P["voice"]["speed_cps"] + 1.0)
        elif re.search(r"[\u3040-\u30ff\uac00-\ud7af]", s["t"]):
            d = math.ceil(len(re.sub(r"\s", "", s["t"])) / 7 + 1.0)
        else:
            d = math.ceil(len(s["t"].split()) / 2.6 + 1.0)
        if d > P["model"]["max_seconds"]:
            sys.exit(f"{s['id']} 约 {d} 秒，超过 {P['model']['max_seconds']} 秒上限：先拆成两段再跑")
        d = max(4, d)
        shot = s.get("shot", "full")
        res = P["model"]["final_resolution"] if (all720 or shot != "pip") else P["model"]["draft_resolution"]
        variant = "fast" if res == "720p" else "mini"
        est = estimate(d, res, variant)
        total += est
        act = P["acts"].get(shot, P["acts"]["full"])
        age = "young" if "年轻" in P["look"] else "mid-30s"
        sex = "female" if "女性" in P["look"] else "male"
        scene = "a clean plain indoor setting with soft natural light" if shot in ("full", "vlog") else "a modern workspace"
        prompt = P["prompt_template"].format(
            age=age, sex=sex, scene=scene, purpose=purpose, act=act,
            voice=P["voice"]["desc"], line=s["t"]
        ).replace("Mandarin Chinese", lang)
        tasks.append({
            "id": s["id"], "shot": shot, "text": s["t"], "lang": lang,
            "duration": d, "resolution": res, "variant": variant,
            "cost_estimate_cny": round(est, 2),
            "output_path": f"projects/{arg('--project', 'dh')}/assets/video/{s['id']}.mp4",
            "prompt": prompt,
        })
    Path(dst).write_text(json.dumps(tasks, ensure_ascii=False, indent=1))
    secs = sum(t["duration"] for t in tasks)
    print(f"{len(tasks)} 段 · 口播约 {secs} 秒 · 预估 {total:.1f} CNY（粗估，实际以网关计费为准）")
    print(f"任务清单已写入 {dst}")

if __name__ == "__main__":
    main()
