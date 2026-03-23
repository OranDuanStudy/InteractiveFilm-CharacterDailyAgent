<div align="center">

# 🎬 Interactive Film Character Daily Agent

**AI-Driven Character Schedule Planning & Video Performance Generation**

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-5.1.0-orange.svg)](CHANGELOG.md)

**[English](README.md)** | **[中文](README_ZH.md)**

</div>

An AI-driven system that implements a complete workflow from **character creation** → **schedule planning** → **event planning** → **director script** → **video performance generation**. Supports interactive storytelling with branching narratives, multiple image/video generation models, and both CLI and Web interaction modes.

---

## 🎮 Demo

**Event Script Example:**

<pre style="width: 100%; overflow: auto; max-height: 400px; font-size: 11px;">{
  "time_slot": "07:00-09:00",
  "event_name": "Morning Coffee Visit",
  "summary": "Alex drops by Luna's apartment with coffee while she stretches, sharing a quiet moment before his work.",
  "image_prompt": "Medium shot of Luna and Alex in Luna's small, art-filled apartment...",
  "sora_prompt": "Shot 1: Medium shot. Luna sits on floor stretching... [Cut to] Shot 2: Alex handing coffee...",
  "event_type": "N",
  "involved_characters": ["Luna", "Alex"]
}</pre>

**Story Performances:**

<table>
<tr>
<td align="center"><b>Time Slot</b></td>
<td align="center"><b>03:00-05:00</b><br/>Peaceful Exhaustion</td>
<td align="center"><b>07:00-09:00</b><br/>Morning Coffee Visit</td>
<td align="center"><b>09:00-11:00</b><br/>Solo Canvas Study</td>
</tr>
<tr>
<td align="center"><b>First Frame</b></td>
<td align="center"><img src="assets/03-00-05-00_N_09.png" width="100%" /></td>
<td align="center"><img src="assets/07-00-09-00_N_01.png" width="100%" /></td>
<td align="center"><img src="assets/09-00-11-00_N_02.png" width="100%" /></td>
</tr>
<tr>
<td align="center"><b>Full Video</b></td>
<td align="center"><img src="assets/03-00-05-00_N_09.gif" width="100%" /></td>
<td align="center"><img src="assets/07-00-09-00_N_01.gif" width="100%" /></td>
<td align="center"><img src="assets/09-00-11-00_N_02.gif" width="100%" /></td>
</tr>
</table>

**Interactive WebUI:**

<table>
<tr>
<td><img src="assets/webui-1.gif" width="100%" alt="WebUI 1" /></td>
<td><img src="assets/webui-2.gif" width="100%" alt="WebUI 2" /></td>
</tr>
</table>

---

## ✨ Core Features

- 🤖 **AI Schedule Planning** — Gemini 2.5 Pro driven, with smart energy & mood system
- 🎭 **Interactive Event System** — R-level (simple choices) & SR-level (multi-stage branching narratives)
- 🎬 **Director Script Generation** — Cinema-grade shot-by-shot output with dialogue & camera design
- 🎥 **Multi-Model Video Generation** — nano_banana / seedream (image) + sora2 / kling (video)
- 📱 **Mobile-First WebUI** — 9:16 portrait mode, 12 iPhone size support, floating transparent UI
- 🔄 **Real-Time Attributes** — Energy (0-100), Mood, Intimacy (L1-L5 Soulmate)
- 🔁 **Auto Retry** — Built-in timeout recovery for generation tasks

---

## 🚀 Quick Start

### 1. Setup

```bash
conda create --name zoo_agent python=3.10 && conda activate zoo_agent
pip install -r requirements.txt
```

### 2. Configure

Edit `config.ini` — set your API keys and endpoints:

```ini
[api]
api_key = YOUR_API_KEY_HERE
base_url = YOUR_API_BASE_URL
model = gemini-2.5-pro

[image_models.nano_banana]
key = YOUR_NANO_BANANA_KEY

[video_models.sora2]
key = YOUR_SORA2_KEY

[video_models.kling]
key = YOUR_KLING_KEY
```

> 📖 Full configuration reference: [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)

### 3. Run

```bash
# One-click full pipeline
./run_pipeline.sh luna_001 2026-01-26 --template luna

# Or step by step
python main.py run luna_001 --template luna           # Schedule + Director
python generate_performance.py -c luna_001 -t 2026-01-26  # Video generation
python web_interactive_demo.py                        # Launch WebUI
```

### 4. Try Demo Data

[[📥 Download Demo Data]](https://drive.google.com/drive/folders/1jBIoYJRGgOwfAJfNKK0B42bAcojVCMd_?usp=sharing)

Extract to `data/`, then run `python web_interactive_demo.py` to try immediately.

---

## 📂 Project Structure

```
├── src/
│   ├── core/          # Agent modules (scheduler, director, event planner)
│   ├── models/        # Data models
│   ├── storage/       # Config & context management
│   └── video/         # Video generation (unified API, scene processor)
├── data/              # Characters, schedules, events, performances
├── assets/templates/  # 13 preset character templates
├── templates/         # HTML templates (editor + user mode)
├── main.py            # Complete workflow
├── generate_performance.py
├── interactive_cli.py
├── web_interactive_demo.py
├── run_pipeline.sh
├── config.ini
└── requirements.txt
```

---

## 🎭 Character Templates

| Template | Character | MBTI | Style |
|----------|-----------|------|-------|
| `luna` | Luna | INFP | Artistic / Dreamy — Aspiring artist |
| `alex` | Alex | ENTJ | Leader / Driven — Tech startup founder |
| `maya` | Maya | ESFP | Free Spirit — Street musician |
| `daniel` | Daniel | ISFJ | Quiet / Observer — Bookstore owner |

---

## 🎬 Video Generation Models

| Image Model | Provider | Video Model | Provider |
|-------------|----------|-------------|----------|
| nano_banana | Wuyin Tech | sora2 | Wuyin Tech |
| seedream | Volcano Engine | kling | Kling AI |

Supports 4 combinations, concurrent processing, auto timeout retry.

---

## 🔧 Command Reference

> 📖 Full CLI documentation: [`docs/COMMANDS.md`](docs/COMMANDS.md)

| Script | Description |
|--------|-------------|
| `./run_pipeline.sh <id> <date>` | One-click full workflow |
| `python main.py run <id>` | Schedule + director generation |
| `python generate_performance.py -c <id> -t <date>` | Video generation |
| `python web_interactive_demo.py` | Launch WebUI |
| `python interactive_cli.py <id> <date> --gui` | CLI interactive mode |
| `./start-tunnel.sh` | Cloudflare Tunnel deployment |

---

## 📜 License

This project is licensed under the [MIT License](LICENSE).

---

<div align="center">

**AI Character Content Generation System**

</div>
