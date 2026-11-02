# OpenKoubo

**One photo + one script → a talking-head video with an AI digital human. A fully local pipeline — zero third-party MCP dependency.**

[![OpenKoubo demo](docs/demo-thumb.jpg)](https://github.com/taoxee/OpenKoubo/releases/download/v0.1.0/openkoubo-demo.mp4)

**▶ Click the image to watch the demo** — the presenter is an AI-generated digital human. Everything in this clip (voice, lip-synced delivery, captions, hook card, BGM mix) was produced end-to-end by this pipeline from a single line of script.

OpenKoubo is an open re-implementation of the original digital-human-koubo workflow, rebuilt so that **every generation step runs through tools you control on your own machine** — no third-party MCP credits required.

## One-command install (for your AI agent)

If you use an AI agent that can run shell commands (Claude Code, Codex, Hermes, Cursor, etc.), just paste this prompt — the agent will clone the repo, read `SKILL.md`, and drive the whole pipeline for you:

```
git clone https://github.com/taoxee/OpenKoubo.git ~/OpenKoubo && read ~/OpenKoubo/SKILL.md and follow it. Ask me for one line of script, show me the cost estimate, wait for my approval, then make me a talking-head video.
```

For humans: see [Quick start](#quick-start) below. `SKILL.md` is the agent-facing workflow contract; this README is yours.

## What it does

- **Digital human from one prompt** — a fixed presenter (face, outfit, voice, framing) defined in `persona/persona.json`, so every video is the same person.
- **Dialogue-driven lip-sync** — each script segment is generated with Seedance text-to-video: the spoken line is embedded in the prompt, driving mouth movements and a native Mandarin voice.
- **Cost-guarded generation** — every paid call passes an explicit price guard; the pipeline prints a segment count, duration, and cost estimate before spending anything. Batch generation is resumable (skip-if-exists).
- **Word-level captions** — faster-whisper word timestamps aligned back to the *original* script text (never trusting whisper's transcript), rendered as a styled burned-in caption layer with Chinese-aware line breaking (no split words, no line-leading punctuation).
- **Packaging** — hook card intro (auto-positioned to keep the presenter's face clear), Pixabay BGM ducked ~20 dB under the voice, loudness normalized to −16 LUFS.
- **Honest QC** — per-segment duration/VAD checks, audio-padded-to-video assembly (prevents cumulative A/V drift across dozens of segments), and frame-level visual inspection.

## How it works

```
script.json ──► 1. build_tasks.py     segment (≤12 s each) + cost estimate → you approve
               2. generate.py         Seedance T2V, dialogue-in-prompt lip-sync + native audio
               3. qc_check.py         duration / speech-span / spec verification
               4. assemble.py         pad audio to video length → concat → loudnorm
               5. transcribe_words.py faster-whisper word timestamps
               6. make_captions.py    transparent caption layer (ProRes 4444 alpha)
               7. make_packaging.py   hook card overlay ──► finalize.sh composites + mixes BGM
```

## The substitution map (why no third-party MCP)

| Original (MCP credits) | OpenKoubo (local tools) |
|---|---|
| GPT Image 2.5 + `material:` id | image tool (gpt-image-2) → `assets/avatar_ref.jpg` |
| Grok Video 1.5 reference-image talking clips | Seedance T2V with the spoken line in the prompt |
| Credit balance quoting | Explicit cost-guard parameter on every paid call |
| CDN ranged downloads | Not needed — tools write straight to local disk |
| whisper.cpp back-check | faster-whisper word timings + VAD duration QC |
| Remotion edit templates | HyperFrames transparent overlays + ffmpeg composition |
| MiMo voice-clone patching | Roadmap (TTS same-length sentence patch) |

## Prerequisites

- An OpenMontage-compatible tool layer checked out locally, with `.env` containing `ARK_API_KEY`, `OPENAI_API_KEY`, `DASHSCOPE_API_KEY` (optional `PIXABAY_API_KEY` for BGM). Set `OM_HOME` if it doesn't live at `~/Documents/Projects/AIGC/OpenMontage`.
- `python3` (3.9+), `ffmpeg` (any build — captions never use `libass`/`drawtext`), Node 18+ (`npx hyperframes`).
- A throwaway venv for transcription: `uv venv /tmp/dh_captionenv --python 3.12 && uv pip install --python /tmp/dh_captionenv/bin/python faster-whisper soundfile`

## Quick start

```bash
git clone https://github.com/taoxee/OpenKoubo.git
cd OpenKoubo

# 1. Write your script (each segment ≤ 12 s ≈ 65 Chinese chars)
cp -R projects/dh-demo projects/my-video
$EDITOR projects/my-video/script.json

# 2. Segment + cost estimate — review before generating
python3 scripts/build_tasks.py projects/my-video/script.json projects/my-video/tasks.json --project my-video

# 3. Generate one segment first, check voice/lip-sync, then batch (resumable)
python3 scripts/generate.py projects/my-video/tasks.json --project my-video --limit 1

# 4. QC the segment
python3 scripts/qc_check.py projects/my-video/assets/video/s1.mp4 "your spoken line"

# 5. Assemble all segments (audio padded to video length, −16 LUFS)
python3 scripts/assemble.py projects/my-video/script.json projects/my-video/assets/video --out final.mp4

# 6. Captions + packaging + BGM mix (edit the copy for your project)
bash projects/my-video/finalize.sh
```

## Project structure

```
persona/persona.json        presenter definition (look / voice / pacing / prompt template)
scripts/build_tasks.py      segmentation + cost estimation
scripts/generate.py         batch generation (cost-guarded, resumable, logs billed model)
scripts/qc_check.py         per-segment duration / VAD / spec QC
scripts/assemble.py         audio-padded concatenation + loudnorm
scripts/transcribe_words.py faster-whisper word-level timestamps
scripts/make_captions.py    caption layer + SRT (Chinese-aware line breaking)
scripts/make_packaging.py   hook-card overlay layer
scripts/pick_bgm.py         Pixabay BGM search + download
projects/dh-demo/           fully worked example (script → final video)
```

## Known limitations (honest ones)

- **Identity is text-anchored, not image-anchored.** Photoreal face reference images get blocked by the video-gateway filter (probabilistically), so segments are generated via text prompts with consistent identity descriptors. Short videos (1–5 segments) look consistent; longer pieces may show mild facial drift between segments. Style-avatared (CG/illustrative) reference images pass the filter — roadmap item.
- **Lip-sync precision** is dialogue-driven T2V: overall aligned, but frame-level mouth accuracy is below dedicated lip-sync models.
- Local `talking_head`/`lip_sync` (SadTalker/Wav2Lip) need CUDA — not viable on Apple Silicon; cloud lip-sync (Kling) works if you add `KLING_API_KEY` to `.env`.

## Responsible use

- Only use faces/voices you own or have **explicit permission** to use. Never impersonate a real person.
- This project does not burn an "AI digital human" badge into the video — **disclose AI-generated content in your platform's publishing flow instead** (e.g. the "AI-generated" checkbox on Douyin/Shipinhao/Xiaohongshu/YouTube).
- No fabricated numbers, prices, or reviews in output videos.

## References

- [digital-human-koubo](https://github.com/andyhuo520/digital-human-koubo) by Berryxia (MIT) — the original workflow this project re-implements without third-party MCP credits. Its Remotion edit templates and 48-component packaging research remain valuable references.
- [OpenMontage](https://github.com/) — the instruction-driven video production system whose tool layer (Seedance / gpt-image-2 / registry / cost guards) OpenKoubo drives.
- Captions via [faster-whisper](https://github.com/SYSTRAN/faster-whisper); overlay rendering via HyperFrames; demo BGM from Pixabay (free license).

## License

MIT © 2026 taoxee
