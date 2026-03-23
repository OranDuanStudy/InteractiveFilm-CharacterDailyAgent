<div align="center">

# 🎬 Interactive Film Character Daily Agent

**AI-Driven Character Schedule Planning & Video Performance Generation System**

Complete Character Director System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-5.1.0-orange.svg)](CHANGELOG.md)

**[English](README.md)** | **[中文](README_ZH.md)**

</div>

## 📖 Overview

An AI-driven character content generation system with a complete workflow: **character creation → schedule planning → event planning → director output → video performance generation**. Supports multiple image/video generation models with both CLI and Web UI modes.

**Event Scripts Example:**

```json
{
  "time_slot": "07:00-09:00",
  "event_name": "Morning Coffee Visit",
  "summary": "Alex drops by Luna's apartment with coffee while she stretches...",
  "event_type": "N",
  "involved_characters": ["Luna", "Alex"],
  "attribute_change": { "energy_change": -1, "mood_change": "Focused and productive" }
}
```

**Story Performances:**

<table>
<tr>
<td align="center" width="20%"><b>Time Slot</b></td>
<td align="center" width="20%"><b>03:00-05:00</b><br/>Peaceful Exhaustion</td>
<td align="center" width="20%"><b>05:00-07:00</b><br/>Dawn Sketch Review</td>
<td align="center" width="20%"><b>07:00-09:00</b><br/>Morning Coffee Visit</td>
<td align="center" width="20%"><b>09:00-11:00</b><br/>Solo Canvas Study</td>
</tr>
<tr>
<td align="center"><b>First Frame</b></td>
<td align="center"><img src="assets/03-00-05-00_N_09.png" width="100%" alt="Demo 1" /></td>
<td align="center"><img src="assets/05-00-07-00_N_10.png" width="100%" alt="Demo 2" /></td>
<td align="center"><img src="assets/07-00-09-00_N_01.png" width="100%" alt="Demo 3" /></td>
<td align="center"><img src="assets/09-00-11-00_N_02.png" width="100%" alt="Demo 4" /></td>
</tr>
<tr>
<td align="center"><b>Full Video</b></td>
<td align="center"><img src="assets/03-00-05-00_N_09.gif" width="100%" alt="Demo 1" /></td>
<td align="center"><img src="assets/05-00-07-00_N_10.gif" width="100%" alt="Demo 2" /></td>
<td align="center"><img src="assets/07-00-09-00_N_01.gif" width="100%" alt="Demo 3" /></td>
<td align="center"><img src="assets/09-00-11-00_N_02.gif" width="100%" alt="Demo 4" /></td>
</tr>
</table>

**Interactive WebUI:**

<table>
<tr>
<td><img src="assets/webui-1.gif" width="100%" alt="WebUI Demo 1" /></td>
<td><img src="assets/webui-2.gif" width="100%" alt="WebUI Demo 2" /></td>
</tr>
</table>

---

## ✨ Core Features

- 🤖 **AI Schedule Planning** — Gemini 2.5 Pro driven daily schedule with energy/mood management
- 🎮 **Interactive Event System** — N/R/SR-level events with branching storylines
- 🎬 **Director Script Generation** — Cinema-grade shot-by-shot director output
- 🎥 **Multi-Model Video Generation** — Image (nano_banana, seedream) + Video (sora2, kling)
- 📊 **Real-Time Attribute System** — Energy, Mood, Intimacy tracking across events
- 🔁 **Auto Retry Mechanism** — Built-in timeout recovery for generation tasks
- 📱 **User Immersion Mode** — 9:16 portrait, floating UI, 12 iPhone sizes supported

---

## 🚀 Quick Start

### 1. Setup

```bash
conda create --name zoo_agent python=3.10
conda activate zoo_agent
pip install -r requirements.txt
```

### 2. Configure

Copy `config.ini.example` to `config.ini` and fill in your API keys:

```ini
[api]
api_key = YOUR_API_KEY_HERE
base_url = http://YOUR_SERVER/v1/chat/completions
model = gemini-2.5-pro

[image_models.nano_banana]
url = https://api.wuyinkeji.com/api/img/nanoBanana-pro
key = YOUR_NANO_BANANA_KEY

[video_models.sora2]
url = https://api.wuyinkeji.com/api/sora2-new/submit
key = YOUR_SORA2_KEY
```

### 3. Run

```bash
# Complete pipeline (recommended)
./run_pipeline.sh luna_001 2026-01-26 --template luna

# Step by step
python main.py run luna_001 --template luna          # Schedule + Director
python generate_performance.py -c luna_001 -t 2026-01-26  # Video generation
python web_interactive_demo.py                        # Web interactive UI
```

---

## 🎮 Interactive System

| Event Type | Interaction | Decision Points | Endings |
|------------|------------|-----------------|---------|
| **N Events** | Auto-play | — | — |
| **R Events** | Simplified choice | 1 | 2 |
| **SR Events** | Multi-stage branching | 3+ × 2-3 options | 3 |

**Real-time attributes:**
- ⚡ **Energy**: 0-100 — affects character status
- 😊 **Mood**: Text description — current emotion
- 💕 **Intimacy**: Points + Level (L1 Stranger → L5 Soulmate)

---

## 🎭 Character Templates

| ID | Name | MBTI | Type |
|----|------|------|------|
| `luna` | Luna | INFP | Artistic / Dreamy |
| `alex` | Alex | ENTJ | Leader / Driven |
| `maya` | Maya | ESFP | Free Spirit |
| `daniel` | Daniel | ISFJ | Quiet / Observer |

---

## 📂 Project Structure

```
├── src/
│   ├── core/          # Agent modules (scheduler, director, event planner)
│   ├── models/        # Data models
│   ├── storage/       # Config & context management
│   └── video/         # Video generation (multi-model support)
├── data/              # Characters, schedules, events, performances
├── assets/templates/  # 13 preset character templates
├── templates/         # HTML templates (editor mode + user mode)
├── main.py            # Complete workflow
├── generate_performance.py   # Video generation
├── interactive_cli.py        # CLI interactive system
├── web_interactive_demo.py   # Web UI
├── run_pipeline.sh            # One-click run
└── config.ini                 # API configuration
```

---

## 📜 Command Reference

### Pipeline & Generation

```bash
# One-click pipeline
./run_pipeline.sh <character> <date> --template <template>

# Schedule only (skip video)
./run_pipeline.sh luna_001 2026-01-26 --template luna --schedule-only

# Specific time slots
python generate_performance.py -c luna_001 -t 2026-01-26 --time-slot "09:00-11:00,14:00-16:00"

# Query video generation status
python query_videos.py data/performance/luna_001_2026-01-26/generation_report.json
```

### Web UI

```bash
python web_interactive_demo.py                        # Default
python web_interactive_demo.py --port 8080            # Custom port
python web_interactive_demo.py --public-url https://cdn.example.com/videos
```

### Deployment

```bash
./start-tunnel.sh    # Start Flask + Cloudflare Tunnel
./stop-all.sh        # Stop all services
./view-logs.sh       # View colored logs
```

> 📋 For full command details and configuration reference, see [docs/COMMANDS.md](docs/COMMANDS.md).

---

## 🔧 Supported Models

| Image Model | Provider | Video Model | Provider |
|-------------|----------|-------------|----------|
| nano_banana | Wuyin Tech | sora2 | Wuyin Tech |
| seedream | Volcano Engine | kling | Kling AI |

4 combinations supported: `nano_banana+sora2` (default), `nano_banana+kling`, `seedream+sora2`, `seedream+kling`

---

## 📄 Citation

```bibtex
@misc{interactivefilm2026,
  title = {Interactive Film Character Daily Agent: AI-Driven Character Content Generation System},
  author = {Oran Duan},
  year = {2026},
  url = {https://github.com/OranDuanStudy/InteractiveFilm-CharacterDailyAgent}
}
```

---

## 📜 License

This project is licensed under the [MIT License](LICENSE) - see the [LICENSE](LICENSE) file for details.
