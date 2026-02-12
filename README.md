<div align="center">

# Interactive Film Character Daily Agent

**Character Schedule Planning & Video Performance Generation System**

Complete Character Director System

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-5.1.0-orange.svg)](CHANGELOG.md)

**[English](README.md)** | **[中文](README_ZH.md)**

</div>

---

<div align="center">

**Events Scripts**
</div>

```json
{
  "time_slot": "01:00-03:00",
  "event_name": "Restless Visions",
  "summary": "Unable to sleep, Luna gets up to sketch a fleeting idea, working by the dim light of her desk lamp.",
  "event_type": "N",
  "event_location": "Small apartment",
  "involved_characters": ["Luna"],
  "attribute_change": {
    "energy_change": 5,
    "mood_change": "Peaceful and rested"
  }
}
```

<div align="center">

**Story Performances**
<br/>
<img src="assets/03-00-05-00_N_09.png" width="23%" alt="Story 1" />
<img src="assets/05-00-07-00_N_10.png" width="23%" alt="Story 2" />
<img src="assets/07-00-09-00_N_01.png" width="23%" alt="Story 3" />
<img src="assets/09-00-11-00_N_02.png" width="23%" alt="Story 4" />
<br/>

[![Story 1](assets/03-00-05-00_N_09.mp4)](assets/03-00-05-00_N_09.mp4)
[![Story 2](assets/05-00-07-00_N_10.mp4)](assets/05-00-07-00_N_10.mp4)
[![Story 3](assets/07-00-09-00_N_01.mp4)](assets/07-00-09-00_N_01.mp4)
[![Story 4](assets/09-00-11-00_N_02.mp4)](assets/09-00-11-00_N_02.mp4)

<br/>

**Interactive WebUI**
<table>
<tr>
<td><img src="assets/webui-1.gif" width="100%" alt="WebUI Demo 1" /></td>
<td><img src="assets/webui-2.gif" width="100%" alt="WebUI Demo 2" /></td>
</tr>
</table>

</div>

## Project Overview

Interactive Film Character Daily Agent is an AI-driven character content generation system that implements a complete workflow from character creation, schedule planning, event planning, director output to video performance generation. The system supports multiple image and video generation models, providing both CLI and Web interaction modes.

**Core Capabilities:**
- AI-driven character schedule planning (based on Gemini 2.5 Pro model)
- Interactive event system (R-level, SR-level events)
- Cinema-grade director script generation
- Multi-model video performance generation (image + video)
- Real-time attribute system (energy, mood, intimacy)
- Automatic timeout retry mechanism for improved generation success rate
- **NEW: User Mode - Immersive Interactive Experience**
- **NEW: Multi-device Adaptation - 12 iPhone Size Support**

---

## Version History

| Version | Changes |
|---------|---------|
| **5.1.0** | **NEW:** User immersive mode, 12 iPhone size adaptation, floating transparent UI, tunnel deployment scripts optimization, color log support |
| **5.0.0** | Added timeout retry mechanism, Web GUI selector, image upload, event character count configuration |
| **4.0.0** | Added video performance generation, interactive system, Web demo |
| **3.1.0** | Added complete workflow integration, multi-turn dialogue mode, smart energy system |
| **3.0.0** | Added SR event planning and director output generation |
| **2.0.0** | Refactored version, integrated schedule planning |
| **1.0.0** | Initial version |

---

## Features

### 1. Schedule Planning Generator (Scheduler)

AI-driven daily schedule planning based on character's 5 dimensions:

- Multi-turn dialogue mode (generate time slots progressively, maintain context coherence)
- Smart energy management system (automatically recover/consume based on activities)
- Output includes: time slot, event name, event type, event summary, image generation prompt, video prompt
- Supports three event types:
  - **N Events**: Normal daily events
  - **R Events**: Single interactive decision events
  - **SR Events**: Multi-stage interactive climax events

### 2. Event Planning Generator (Event Planner)

Unified handling of R-level and SR-level interactive event planning:

| Event Type | Interaction Depth | Decision Points | Endings |
|------------|-------------------|-----------------|---------|
| **R Events** | Simplified | 1 time | 2 |
| **SR Events** | Full | 3+ stages × 2-3 options | 3 |

Complete attribute change system: energy, mood, intimacy

### 3. Director Output Generator (Director Agent)

Generate detailed director output for R/SR events:

- Multi-turn dialogue mode for scene-by-scene generation
- Includes: story summary, lines & camera design, first frame image prompt, video generation prompt
- Generate independent scenes for each option branch

### 4. Video Performance Generator

Supports flexible combinations of multiple image and video generation models:

| Image Model | Provider | Video Model | Provider |
|-------------|----------|-------------|----------|
| nano_banana | Wuyin Tech | sora2 | Wuyin Tech |
| seedream | Volcano Engine | kling | Kling AI |

**Features:**
- Concurrent processing, independent generation for each scene
- Automatically handles N/R/SR three event type video generation workflows
- Supports image upload to cloud
- **Automatic timeout retry mechanism**: Automatically resubmit after video/image generation timeout
- Supports specifying time slot generation (`--time-slot` parameter)
- Continuous query mode: no limit on query count until generation completes or fails

### 5. Interactive System

Supports GUI-enabled video story player (Web mode):

- **N Events**: Auto-play and apply attribute changes
- **R Events**: Preview video → Selection → Branch video → Ending
- **SR Events**: Preview video → Multi-stage selection → Path video → Ending

Real-time attribute system:
- **Energy**: 0-100, affects character status
- **Mood**: Text description, character's current emotion
- **Intimacy**: Points + Level (L1-L5)

**Web Interactive Demo New Features:**
- **Character/Date Selector**: Select character and date in browser GUI, no command line arguments needed
- **Public Video Support**: Load videos from public CDN (`--public-url` parameter)
- **Event Backtracking**: Replay completed events
- **Timeline Display**: Show complete schedule event list

**User Immersion Mode:**
- **9:16 Portrait Optimization**: Portrait experience designed for mobile
- **Floating Transparent UI**: Status bar and progress indicator float above video with transparent blurred background
- **12 iPhone Size Support**: Covering iPhone 4 to iPhone 15 Pro Max full series
- **Video First Mode**: Adaptive height, display complete video without scrolling
- **Bottom-right Size Menu**: Quick switch between different device preview sizes

Supported Device Sizes:
| Size Option | Resolution | Compatible Devices |
|-------------|------------|---------------------|
| iPhone 4/5 | 320x568 | iPhone 4, 4S, 5, 5S, 5C, SE |
| iPhone 6/7/8 | 375x667 | iPhone 6, 7, 8 (standard) |
| iPhone 6/7/8 Plus | 414x736 | iPhone 6+, 7+, 8+ |
| iPhone X/11/12/13 | 390x844 | iPhone X, XS, 11 Pro, 12, 13, 14 |
| iPhone XR/11 | 428x926 | iPhone XR, 11, 12, 13, 14 (Plus) |
| iPhone 14 Pro/15 | 393x852 | iPhone 14 Pro, 15, 15 Pro |
| iPhone 14 Pro Max | 430x932 | iPhone 14 Pro Max |
| iPhone 15 Plus | 430x932 | iPhone 15 Plus |
| iPhone 15 Pro Max | 430x932 | iPhone 15 Pro Max |
| Android S | 360x800 | Android standard portrait |
| Video First | Auto | Fit video, no scrolling |

---

## Quick Start

### 1. Environment Setup

```bash
# Create virtual environment
conda create --name zoo_agent python=3.10
conda activate zoo_agent

# Install dependencies
pip install -r requirements.txt

# Or install only basic features (without video generation)
pip install requests tqdm
```

### 2. Configure API Key

Edit `config.ini` file:

```ini
[api]
api_key = YOUR_API_KEY_HERE
base_url = http://192.154.241.225:3000/v1/chat/completions
model = gemini-2.5-pro
temperature = 0.7
max_tokens = 65536
timeout = 800
parse_error_retries = 3

# Image generation config
[image_models.nano_banana]
url = https://api.wuyinkeji.com/api/img/nanoBanana-pro
query_url = https://api.wuyinkeji.com/api/img/drawDetail
key = YOUR_NANO_BANANA_KEY
aspect_ratio = 9:16
image_size = 2K

# Video generation config
[video_models.sora2]
url = https://api.wuyinkeji.com/api/sora2-new/submit
query_url = https://api.wuyinkeji.com/api/sora2/detail
key = YOUR_SORA2_KEY
aspect_ratio = 9:16
duration = 15
size = small

[video_models.kling]
url = https://api-beijing.klingai.com/v1/videos/image2video
key = YOUR_KLING_KEY
model = kling-v2-6
mode = pro
duration = 10
cfg_scale = 0.5
sound = off

# Video generation common config
[video_generation]
default_image_model = nano_banana
default_video_model = sora2
max_workers = 50
poll_interval = 10
video_timeout_seconds = 1800
image_timeout_seconds = 600
max_retry_on_timeout = 3
timeout_retry_enabled = true
```

### 3. (Optional) Download Demo Data

Download example character schedules and performance data to try the WebUI immediately:

[**Download Demo Data**](https://drive.google.com/drive/folders/1jBIoYJRGgOwfAJfNKK0B42bAcojVCMd_?usp=sharing)

The demo data includes:
- Complete character schedules
- Event planning data
- Director scripts
- Generated performance videos

After downloading, extract to the `data/` directory, then run the WebUI:

```bash
# Start WebUI with demo data
python web_interactive_demo.py
```

### 4. Run Complete Workflow

```bash
# Method 1: Using shell script (recommended)
./run_pipeline.sh leona_001 2026-01-26 --template leona

# Method 2: Step-by-step execution
# Step 1: Generate schedule and director script
python main.py run leona_001 --template leona

# Step 2: Generate video performance
python generate_performance.py -c leona_001 -t 2026-01-26

# Step 3: Run interactive system

# CLI mode (command line interaction)
python interactive_cli.py leona_001 2026-01-26 --gui

# Web mode (recommended, supports browser GUI character/date selection)
python web_interactive_demo.py

# Web mode with specified port and public video URL
python web_interactive_demo.py --port 8080 --public-url https://cdn.example.com/videos

# Query and download videos
python query_videos.py data/performance/leona_001_2026-01-26/generation_report.json
```

---

## Project Structure

```
Interactive_Film_Character_Agent/
├── src/                               # Source code directory
│   ├── core/                          # Core Agent modules
│   │   ├── agent.py                   # Schedule planning Agent
│   │   ├── director_agent.py          # Director Agent
│   │   ├── event_planner.py           # Event planning Agent
│   │   ├── formatter.py               # Output formatter
│   │   └── interactive_session.py     # Interactive session system
│   ├── models/                        # Data models
│   │   └── models.py                  # Character and event data models
│   ├── storage/                       # Storage and config management
│   │   ├── config.py                  # Config loading
│   │   ├── context_manager.py         # Character context management
│   │   ├── template_loader.py         # Character template loading
│   │   ├── image_uploader.py          # Image upload module
│   │   └── create_character_contexts.py
│   └── video/                         # Video generation module
│       ├── unified_api_client.py      # Unified API client
│       ├── scene_processor.py         # Scene processor
│       ├── performance_generator.py   # Performance generator
│       └── video_task_query.py        # Video task query
├── data/                              # Data storage directory
│   ├── characters/                    # Character context files
│   ├── schedule/                      # Schedule planning files
│   ├── events/                        # Event planning files
│   ├── director/                      # Director output files
│   ├── performance/                   # Video performance data
│   └── history/                       # Selection history records
├── assets/                            # Static resources
│   ├── templates/                     # 13 preset character templates
│   └── pics/                          # Image resources
├── templates/                         # HTML templates
│   ├── interactive_demo.html          # Interactive demo page (editor mode)
│   └── user_mode.html                 # User immersive mode (9:16 portrait)
├── main.py                            # Complete workflow main script
├── generate_performance.py            # Video performance generation script
├── interactive_cli.py                 # Interactive system CLI
├── web_interactive_demo.py            # Web interactive demo (supports GUI selector)
├── run_pipeline.sh                    # One-click run script
├── start-tunnel.sh                    # Cloudflare Tunnel startup script
├── stop-all.sh                        # Service shutdown script
├── view-logs.sh                       # Log viewing script
├── create_character.py                # Character creation tool
├── director.py                        # Director generation tool
├── scheduler.py                       # Schedule generation tool
├── sr_event.py                        # SR event generation tool
├── query_videos.py                    # Video query and download tool
├── config.ini                         # API config file
├── requirements.txt                   # Python dependencies list
└── README.md                          # Project documentation
```

---

## Command Reference

Note: The number after the character corresponds to different user numbers. Each user should create all related characters, then generate schedules and videos for a single character combined with other character profiles.

### run_pipeline.sh - One-click Run Script

```bash
./run_pipeline.sh <character_id> <date> [options]

Options:
  --template TEMPLATE   Use character template
  --force, -f           Force overwrite existing character
  --use-existing, -e    Only use existing character
  --schedule-only       Only generate schedule and director script
  --skip-video          Skip video generation
  --image-model MODEL   Image model (nano_banana, seedream)
  --video-model MODEL   Video model (sora2, kling)
  --log-level LEVEL     Log level (DEBUG, INFO, WARNING, ERROR)
  --config FILE         Config file path

Examples:
./run_pipeline.sh leona_001 2026-01-26 --template leona
./run_pipeline.sh auntie_005 2026-01-26 --use-existing --schedule-only
```

### main.py - Complete Workflow

```bash
python main.py run <character_id> [options]

Options:
  --template TEMPLATE   Use character template
  --force, -f           Force overwrite
  --use-existing, -e    Use existing character
  --schedule-only       Only run schedule planning
  --sr-only             Only run SR event generation
  --director-only       Only run director generation
  --no-streaming        Use single-shot generation mode
```

### generate_performance.py - Video Performance Generation

```bash
python generate_performance.py --character <id> --date <date> [options]

Options:
  --schedule, -s        Schedule JSON file path
  --director, -d        Director script JSON file path
  --image-model, -im    Image model (nano_banana, seedream)
  --video-model, -vm    Video model (sora2, kling)
  --time-slot, -ts      Specify time slot, only generate videos within this slot
                        Support multiple slots separated by comma, e.g.: '09:00-11:00,14:00-16:00'
  --log-level, -l       Log level

Examples:
python generate_performance.py -c leona_001 -t 2026-01-26
python generate_performance.py -c leona_001 -t 2026-01-26 -im seedream -vm kling
python generate_performance.py -c leona_001 -t 2026-01-26 --time-slot "09:00-11:00"
python generate_performance.py -c leona_001 -t 2026-01-26 --time-slot "09:00-11:00,14:00-16:00"
```

### interactive_cli.py - Interactive System

```bash
python interactive_cli.py <character_id> <date> [options]

Options:
  --gui                 Enable GUI mode (recommended)
  --preset JSON         Preset selections JSON string
  --preset-file PATH    Preset selections JSON file
  --data-dir PATH       Data directory path
  --no-save             Don't save results to file

Examples:
python interactive_cli.py leona_001 2026-01-26 --gui
python interactive_cli.py leona_001 2026-01-26 --preset '{"09:00-11:00": ["A"]}'
```

### create_character.py - Create Character

```bash
python create_character.py <character_id> --template <template>

Options:
  --force, -f           Force overwrite existing character

Examples:
python create_character.py leona_001 --template leona
```

### web_interactive_demo.py - Web Interactive Demo

```bash
python web_interactive_demo.py [options]

Options:
  --host HOST           Server address (default: 0.0.0.0)
  --port PORT           Server port (default: 5000)
  --public-url URL      Public video URL prefix (for loading videos from internet)
  --data-dir PATH       Data directory path (default: data)

Examples:
# Start with default config
python web_interactive_demo.py

# Specify port
python web_interactive_demo.py --port 8080

# Use public videos
python web_interactive_demo.py --public-url https://cdn.example.com/videos

# Combine options
python web_interactive_demo.py --port 8080 --public-url https://cdn.example.com/videos

Note: Character and date can be selected in the browser interface top-left selector, no command line arguments needed.
```

### query_videos.py - Video Query and Download

```bash
python query_videos.py <report_path> [options]

Parameters:
  report_path           Generation report JSON file path

Options:
  -o, --output PATH    Video output directory (default: same as report directory)
  -w, --workers NUM   Max concurrent threads (default: 5)
  -k, --api-key KEY    Wuyin Tech API key (default: read from config.ini)

Examples:
python query_videos.py data/performance/leona_001_2026-01-26/generation_report.json
python query_videos.py data/performance/leona_001_2026-01-26/generation_report.json -o videos/
python query_videos.py data/performance/leona_001_2026-01-26/generation_report.json -w 10
```

### Deployment Scripts (穿透部署脚本)

**start-tunnel.sh** - One-click Service Startup (Cloudflare Tunnel)

```bash
# Start all services (Flask + Cloudflare Tunnel)
./start-tunnel.sh

# Get public access URL
tail -50 /tmp/cloudflared.log | grep 'https://'
```

**Features:**
- Auto-detect working directory, supports running from any cloned directory
- No pre-configured systemd service needed
- Preserve colored log output (FORCE_COLOR + PYTHONUNBUFFERED)
- Auto-generate temporary public URL

**stop-all.sh** - Stop All Services

```bash
# Stop Flask and Cloudflare Tunnel
./stop-all.sh
```

**view-logs.sh** - View Colored Logs

```bash
./view-logs.sh

# Options:
# 1) Flask real-time access log
# 2) Cloudflare Tunnel real-time log
# 3) Flask recent 50 access records
# 4) Current online access statistics
# 5) Exit
```

**Log Output Locations:**
- Flask log: `/tmp/zooo-agent.log`
- Cloudflare log: `/tmp/cloudflared.log`

---

## Available Character Templates

| Template ID | Character | MBTI | Type | Description |
|-------------|-----------|------|------|-------------|
| luna | Luna | INFP | Artistic/Dreamy | Aspiring artist, finds beauty in everyday moments |
| alex | Alex | ENTJ | Leader/Driven | Tech startup founder, ambitious and caring |
| maya | Maya | ESFP | Free Spirit | Street musician, lives in the moment |
| daniel | Daniel | ISFJ | Quiet/Observer | Bookstore owner, thoughtful and reliable |

---

## Intimacy Level System

```
L5 - Soulmate      (200+)      Soulmates
L4 - Deep Bond     (150-199)   Deep bond
L3 - Close Friend  (100-149)   Close friend
L2 - Friend        (50-99)     Friend
L1 - Stranger      (0-49)      Acquaintance
```

---

## Output File Structure

```
data/
├── characters/
│   └── {character_id}_context.json           # Character context
├── schedule/
│   └── {character_id}_schedule_{date}.json   # Schedule planning
├── events/
│   └── {character_id}_events_{date}.json     # Event planning (R/SR)
├── director/
│   └── {character_id}_director_{date}.json   # Director output
├── performance/
│   └── {character_id}_{date}/                # Video performance data
│       ├── *.mp4                            # Generated video files
│       ├── *.jpg                            # Generated image files
│       └── generation_report.json            # Generation report
└── history/                                  # Selection history
    └── {character_id}_choices_{date}.json
```

---

## Dependencies

### Basic Dependencies (Required)

```
requests>=2.32.0
tqdm>=4.66.0
```

### Optional Dependencies

```bash
# Image generation (Seedream)
volcengine-python-sdk[ark]>=1.0.0

# GUI video playback
opencv-python>=4.8.0
pillow>=10.0.0
```

---

## Configuration File Details

### [api] - AI Model Config

```ini
api_key              = YOUR_API_KEY
base_url             = http://192.154.241.225:3000/v1/chat/completions
model                = gemini-2.5-pro
temperature          = 0.7
max_tokens           = 65536
timeout              = 800
parse_error_retries  = 3          # Parse error retry count
```

### [image_models.*] - Image Generation Config

Supports two image models: `nano_banana`, `seedream`

```ini
[image_models.nano_banana]
url             = https://api.wuyinkeji.com/api/img/nanoBanana-pro
aspect_ratio    = 9:16
image_size      = 2K
```

### [video_models.*] - Video Generation Config

Supports two video models: `sora2`, `kling`

```ini
[video_models.sora2]
url             = https://api.wuyinkeji.com/api/sora2-new/submit
query_url       = https://api.wuyinkeji.com/api/sora2/detail
aspect_ratio    = 9:16
duration        = 15               # 15 or 25 (sora2pro)
size            = small

[video_models.kling]
url             = https://api-beijing.klingai.com/v1/videos/image2video
model           = kling-v2-6        # kling-v1, kling-v1-5, kling-v1-6, kling-v2-master, kling-v2-1, kling-v2-5-turbo, kling-v2-6
mode            = pro                # std (standard) or pro (expert/high quality)
duration        = 10                # 5 or 10
cfg_scale       = 0.5               # Range [0, 1]
sound           = off                # on or off (V2.6+ only)
```

### [video_generation] - Video Generation Common Config

```ini
default_image_model       = nano_banana
default_video_model      = sora2
max_workers              = 50
poll_interval            = 10

# Timeout retry config
video_timeout_seconds    = 1800      # Video generation query timeout (seconds)
image_timeout_seconds    = 600       # Image generation query timeout (seconds)
max_retry_on_timeout    = 3          # Max retry count after timeout
timeout_retry_enabled   = true       # Enable timeout retry
```

### [image_upload] - Image Upload Config (local image -> cloud URL)

```ini
url                 = YOUR_UPLOAD_API_URL
user_id             = 2
authorization       = YOUR_TOKEN
platform            = android
device_id           = 1
app_version         = 1.0.4.1
upload_type         = DAILY_AGENT
```

### [daily_event_count] - Daily Event Count Config

```ini
daily_r_events   = 2       # Daily R-type event count (fixed)
daily_sr_events  = 1       # Daily SR-type event count (fixed)
```

### [event_character_count] - Event Character Count Probability Config

```ini
# N-type events: min_prob=0.9 -> 0.9 probability for 1 person, 0.1 for 2
n_min_count  = 1
n_max_count  = 2
n_min_prob   = 0.9

# R-type events: min_prob=0.7 -> 0.7 probability for 2 people, 0.3 for 3
r_min_count  = 2
r_max_count  = 3
r_min_prob   = 0.7

# SR-type events: min_prob=0.5 -> 0.5 probability for 3 people, 0.5 for 4
sr_min_count = 3
sr_max_count = 4
sr_min_prob  = 0.5
```

---

## FAQ

### Q: How to choose image and video model combinations?

A: Currently supports 4 combinations:
- `nano_banana + sora2` (default)
- `nano_banana + kling`
- `seedream + sora2`
- `seedream + kling`

### Q: What to do if video generation fails or times out?

A: Built-in automatic timeout retry mechanism, no manual handling needed. To check status, use `query_videos.py`:

```bash
python query_videos.py data/performance/leona_001_2026-01-26/generation_report.json
```

### Q: How to generate videos only for specific time slots?

A: Use `--time-slot` parameter to specify time slots:

```bash
# Generate single time slot
python generate_performance.py -c leona_001 -t 2026-01-26 --time-slot "09:00-11:00"

# Generate multiple time slots (comma separated)
python generate_performance.py -c leona_001 -t 2026-01-26 --time-slot "09:00-11:00,14:00-16:00"
```

### Q: How to generate schedule only without videos?

A: Use `--schedule-only` option:

```bash
./run_pipeline.sh leona_001 2026-01-26 --template leona --schedule-only
```

### Q: How does Web demo load videos from internet?

A: Specify `--public-url` parameter when starting:

```bash
python web_interactive_demo.py --public-url https://cdn.example.com/videos
```

### Q: How to configure daily event count?

A: Modify `[daily_event_count]` config in `config.ini`:

```ini
[daily_event_count]
daily_r_events   = 2
daily_sr_events  = 1
```

---

## Tech Stack

- **Language**: Python 3.10+
- **AI Model**: Gemini 2.5 Pro
- **Concurrency**: ThreadPoolExecutor
- **Data Format**: JSON
- **Image Generation**: nano_banana (Wuyin Tech), seedream (Volcano Engine)
- **Video Generation**: sora2 (Wuyin Tech), kling (Kling AI)

---

<div align="center">

**AI Character Content Generation System**

</div>
