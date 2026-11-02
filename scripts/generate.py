#!/usr/bin/env python3
"""generate.py — 按任务清单批量生成口播片段（OM seedance_ark，断点续跑）。

用法：
  python3 generate.py tasks.json [--project dh-xxx] [--limit N]

规则：
- 每个任务 = 一次 seedance_ark.execute(text_to_video)，台词写进提示词驱动口型+原生配音
- 必带 cost guard：custom_price_cny_per_million_tokens（480p: mini=23 / fast=37）
- 输出落 <本仓库>/projects/<project>/assets/video/<id>.mp4，已存在则跳过（断点续跑）
"""
import json, os, subprocess, sys
from pathlib import Path

# OpenMontage 仓库位置：优先 OM_HOME 环境变量，默认本机约定路径
OM = Path(os.environ.get("OM_HOME") or os.path.expanduser("~/Documents/Projects/AIGC/OpenMontage"))
HERE = Path(__file__).resolve().parent.parent

INNER = '''
import json, os, sys, time
sys.path.insert(0, "@OM@")
import dotenv
dotenv.load_dotenv("@ENVF@")
from tools.tool_registry import registry
registry.discover()
tool = registry.get("seedance_ark")
todo = json.loads(open("@TARGETS@").read())
for t in todo:
    out = t["out"]
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if os.path.exists(out):
        print("skip", t["id"], flush=True)
        continue
    print("[gen]", t["id"], t["resolution"], t["variant"], str(t["duration"]) + "s", flush=True)
    try:
        result = tool.execute({
            "prompt": t["prompt"],
            "operation": "text_to_video",
            "duration": t["duration"],
            "aspect_ratio": "9:16",
            "resolution": t["resolution"],
            "generate_audio": True,
            "custom_price_cny_per_million_tokens": t["price"],
            "output_path": out,
            "timeout_seconds": 1200,
        })
        if result.success:
            actual_model = (result.data or {}).get("model", "?")
            print("[OK]", t["id"], "->", result.data.get("output_path", out), "| billed model:", actual_model, flush=True)
        else:
            print("[FAIL]", t["id"], ":", result.error, flush=True)
    except Exception as e:
        print("[FAIL]", t["id"], ":", e, flush=True)
print("ALL DONE")
'''


def main():
    tasks_path = Path(sys.argv[1])
    project = "dh-demo"
    if "--project" in sys.argv:
        project = sys.argv[sys.argv.index("--project") + 1]
    limit = int(sys.argv[sys.argv.index("--limit") + 1]) if "--limit" in sys.argv else None

    tasks = json.loads(tasks_path.read_text())
    todo = []
    for t in tasks:
        out = HERE / "projects" / project / "assets" / "video" / (t["id"] + ".mp4")
        if out.exists():
            print("skip (exists):", t["id"])
            continue
        price = 23 if t["variant"] == "mini" else 37
        todo.append({
            "id": t["id"], "out": str(out), "prompt": t["prompt"],
            "duration": t["duration"], "resolution": t["resolution"],
            "variant": t["variant"], "price": price,
        })
    if not todo:
        print("nothing to do")
        return
    if limit:
        todo = todo[:limit]

    targets_file = Path("/tmp/dh_targets.json")
    targets_file.write_text(json.dumps(todo, ensure_ascii=False))
    inner = Path("/tmp/dh_gen_inner.py")
    inner.write_text(INNER.replace("@OM@", str(OM)).replace("@ENVF@", str(OM / ".env")).replace("@TARGETS@", str(targets_file)))

    proc = subprocess.run(
        ["python3", str(inner)],
        capture_output=True, text=True, timeout=1700,
    )
    print(proc.stdout[-3000:])
    if proc.stderr.strip():
        print("STDERR:", proc.stderr[-1500:])
    sys.exit(proc.returncode)


if __name__ == "__main__":
    main()
