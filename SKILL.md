---
name: OpenKoubo
description: OpenKoubo——数字人口播视频的本地全流程（OpenMontage 原生，无 Renoise）。一张照片一句台词→口播成片：形象图（openai_image）→ 分段口播（seedance_ark T2V 台词驱动口型+原生配音）→ 拼接（ffmpeg 音画等长）→ 词级字幕（faster-whisper + HyperFrames）→ 包装出片（钩子卡+BGM+响度规范）。触发：数字人口播、OpenKoubo、koubo、用数字人讲这段、口播视频、digital human talking head。
---

# OpenKoubo · 数字人口播

**照片 + 台词 → 口播成片**。OpenMontage 家族成员（同 OpenShorts），Renoise 零依赖——原 `andyhuo520/digital-human-koubo` 工作流全部映射到本机已验证的 OM 工具链；原仓库完整保留在 `reference-repo/`（Remotion 模板、48 包装组件库是后续移植素材）。

## 与原版的映射（核心）

| 环节 | 原（Renoise） | 本版（OpenMontage） |
|---|---|---|
| 形象图 | GPT Image 2.5 + material id | `openai_image`（gpt-image-2）→ `assets/avatar_ref.jpg` |
| 口播分段生成 | Grok Video 1.5 参考图模式（17 credits/s） | `seedance_ark` T2V：台词写进提示词驱动口型，`generate_audio=True` 原生配音 |
| 费用护栏 | credits 报价等确认 | OM cost guard：`custom_price_cny_per_million_tokens`（480p mini=23 / fast=37）必传，先报价再生成 |
| 场景合成 | 人物进直播间（GPT Image） | `openai_image` 合成场景参考图（i2v 审核风险高，已知 4/5 被拦，走 T2V 文本锚定） |
| 分片下载 | Renoise CDN rangedl 6 段并发 | 不需要——OM 工具直接落盘本地 |
| 回听校验 | whisper.cpp 逐段比对 | 同思路：whisper/faster-whisper 转写比对（OM transcriber） |
| 拼接 | assemble.py（音频补齐到画面等长） | `scripts/assemble.py`（从原仓库移植，本地 ffmpeg） |
| 剪辑出片 | Remotion 模板（huazi-916 等） | OM `video_compose`（Remotion 引擎，词级卡拉OK字幕、BGM、字幕烧录一体） |
| 封面+首帧 | make_cover + cover_first | `openai_image` 出封面 + ffmpeg 首帧拼接（后续迭代） |
| 文字在人身后 | Vision personmask 抠像 | 原 `personmask.swift` 可直接复用（本地能力，不依赖 Renoise） |
| 念错字补丁 | MiMo 克隆换句 | `dashscope_tts` 合成替换句 + ffmpeg 时长对齐（后续迭代） |

## 红线（继承原版）

- **先报价后生成**：`build_tasks.py` 打印段数·秒数·预估 CNY，用户在对话里明确同意才跑 `generate.py`。先拍第 1 段给用户确认音色/口型，再批量。
- 成片画面不压 AI 声明角标（用户 2026-11-02 要求移除）；公开发布时在平台发布页勾选「AI 生成」声明即可。
- 只用本人或有明确授权的形象与声音。
- 念错字当场修（dashscope_tts 换句保口型思路），不交给用户去听。

## 流程

### 0. 准备（每次新对话第一次用）
1. 检查 OM 仓库与 `.env`（ARK_API_KEY / OPENAI_API_KEY / DASHSCOPE_API_KEY）。
2. 形象图 `assets/avatar_ref.jpg` 存在即用；没有则用 `persona.json → avatar.prompt` 生成一张（用户授权的照片或纯生成形象）。

### 1. 写稿 → script.json
按 persona.json 的 segment_rule 切段（每段 ≤12 秒 ≈ 65 字，一句或两句）。字段：`[{id, shot(full|pip|vlog|depth), t, host, lang}]`。

### 2. 切段+报价
```
python3 scripts/build_tasks.py script.json tasks.json --purpose "..." --project <pid>
```
→ 打印段数·秒数·预估费用。**报给用户等确认。**

### 3. 生成
```
python3 scripts/generate.py tasks.json --project <pid> [--limit 1]   # 先拍第 1 恨
```
先 `--limit 1` 拍第 1 段，用户确认口型/音色后去掉 limit 批量。断点续跑（已存在跳过）。模型选择遵守 OM 策略：草稿/social ≤720p → mini；定稿 720p → fast（同 seed bake-off 后）。

### 4. 校验
- `ffprobe` 每段时长/分辨率（9:16 → 720×1280 或 480×832 竖屏规格）。
- 抽帧 vision 检查（口型开合、无烧字幕、无手部畸变）。
- whisper 回听比对文稿（数字归一化误报注意：九百九十九→999 属正常）。

### 5. 拼接
`scripts/assemble.py`（移植自原仓库）：每段音频补齐到画面等长 → concat → loudnorm。**拼接后必须检查画面/声音时长一致**（几十段累积漂移是原项目实测过的坑）。

### 6. 字幕/包装/出片
走 OM `video_compose`：`edit_decisions` + `renderer_family: "cinematic-trailer"` 路径，`captions`（词级卡拉OK，faster-whisper word_timestamps 取时间）+ `music`/`soundtrack`。注意 OM 已知坑：CinematicRenderer 会给视频场景套色调渐晕（白底 endcard 会发灰 → 尾部另拼 HyperFrames 干净卡）；音频偏轻 → 后置 `loudnorm=I=-15:TP=-1.0:LRA=11` 重混。

### 7. 封面+首帧（默认做）
`openai_image` 生成封面（钩子标题≤8字+红色强调句+副标题+证据卡布局）→ ffmpeg 0.5s 首帧拼接（后续迭代补 make_cover/cover_first 移植）。

## 已验证（2026-11-02）

- seedance_ark T2V 台词驱动口型+中文配音：xianxia 剑仙 spot 端到端验证过（OM skill 记录）。
- 480p mini 单段 10s ≈ 数毛级 CNY 成本，先 mini 后 fast 的分档策略已 codify。
- 本项目最小验证：1 段 8s 口播（见 projects/dh-demo/）。

## 后续迭代方向

1. 移植原仓库 Remotion 模板（huazi-916 花字三档、lin-169 小林式 13 场景）到 OM atelier 工作流。
2. 48 包装组件移植：pack 数组规范 → OM HyperFrames/Remotion 组件。
3. 声音统一（voicefx/unify 频谱匹配+房间混响）本地化。
4. 文字在人身后：personmask.swift 抠像 + 3 层合成（全本地）。
5. 念错字补丁：dashscope_tts 换句保口型。
