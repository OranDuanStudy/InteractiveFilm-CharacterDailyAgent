<div align="center">

# Interactive Film Character Daily Agent

**角色日程规划与视频表演生成系统**

基于角色编导体系的完整实现

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-5.1.0-orange.svg)](CHANGELOG.md)

**[English](README.md)** | **[中文](README_ZH.md)**

</div>

---

<div align="center">

**事件编排**
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

**故事演绎**
<br/>
<img src="assets/03-00-05-00_N_09.png" width="23%" alt="故事1" />
<img src="assets/05-00-07-00_N_10.png" width="23%" alt="故事2" />
<img src="assets/07-00-09-00_N_01.png" width="23%" alt="故事3" />
<img src="assets/09-00-11-00_N_02.png" width="23%" alt="故事4" />
<br/>

**可交互WebUI**
<table>
<tr>
<td><img src="assets/webui-1.gif" width="100%" alt="WebUI演示1" /></td>
<td><img src="assets/webui-2.gif" width="100%" alt="WebUI演示2" /></td>
</tr>
</table>

</div>

## 项目简介

Interactive Film Character Daily Agent 是一个 AI 驱动的角色内容生成系统，实现了从角色创建、日程规划、事件策划、导演输出到视频表演生成的完整工作流。系统支持多种图片和视频生成模型，提供 CLI 和 Web 两种交互模式。

**核心能力：**
- AI 驱动的角色日程规划（基于 Gemini 2.5 Pro 模型）
- 交互式事件系统（R级、SR级事件）
- 电影级导演脚本生成
- 多模型视频表演生成（图片+视频）
- 实时属性系统（能量、心情、亲密度）
- 超时自动重试机制，提升生成成功率
- **NEW: 用户模式 - 沉浸式影游体验**
- **NEW: 多设备适配 - 12种 iPhone 尺寸支持**

---

## 版本历史

| 版本 | 更新内容 |
|------|---------|
| **5.1.0** | **NEW:** 用户沉浸模式、12种iPhone尺寸适配、悬浮透明UI、穿透部署脚本优化、彩色日志支持 |
| **5.0.0** | 新增超时重试机制、Web GUI选择器、图片上传、事件角色数量配置 |
| **4.0.0** | 新增视频表演生成、交互系统、Web演示 |
| **3.1.0** | 添加完整流程串联、多轮对话模式、智能能量系统 |
| **3.0.0** | 添加SR事件策划和导演输出生成功能 |
| **2.0.0** | 重构版本，整合日程规划 |
| **1.0.0** | 初始版本 |

---

## 功能特性

### 1. 日程规划生成 (Scheduler)

基于角色5大维度输入系统，生成 AI 驱动的每日日程规划：

- 多轮对话模式（逐时间段生成，保持上下文连贯）
- 智能能量管理系统（根据活动自动恢复/消耗）
- 输出包含：时间段、事件名称、事件类型、事件梗概、生图Prompt、视频Prompt
- 支持三种事件类型：
  - **N事件**：普通日常事件
  - **R事件**：单次交互决策事件
  - **SR事件**：多阶段互动的高潮事件

### 2. 事件策划生成 (Event Planner)

统一处理 R级 和 SR级 交互事件策划：

| 事件类型 | 交互深度 | 决策点 | 结局数 |
|---------|---------|--------|--------|
| **R事件** | 简化版 | 1次 | 2个 |
| **SR事件** | 完整版 | 3+阶段×2-3选项 | 3个 |

完整的属性变化系统：能量、心情、亲密度

### 3. 导演输出生成 (Director Agent)

为 R/SR 事件生成详细的导演输出：

- 多轮对话模式逐场景生成
- 包含：剧情简述、台词与镜头设计、首帧生图Prompt、视频生成提示词
- 为每个选项分支生成独立的场景

### 4. 视频表演生成 (Video Performance)

支持多种图片和视频生成模型的自由组合：

| 图片模型 | 提供商 | 视频模型 | 提供商 |
|---------|--------|---------|--------|
| nano_banana | 无引科技 | sora2 | 无引科技 |
| seedream | 火山引擎 | kling | 可灵AI |

**特点：**
- 并发处理，每个场景独立生成
- 自动处理 N/R/SR 三种事件类型的视频生成流程
- 支持图片上传到云端
- **超时自动重试机制**：视频/图片生成超时后自动重新提交，提升成功率
- 支持指定时间段生成（`--time-slot` 参数）
- 持续查询模式：无次数限制，直到生成完成或失败

### 5. 交互系统 (Interactive System)

支持带 GUI 的视频剧情播放器（Web 模式）：

- **N事件**：自动播放并应用属性变化
- **R事件**：前置视频 → 选择 → 分支视频 → 结局
- **SR事件**：前置视频 → 多阶段选择 → 对应路径视频 → 结局

实时属性系统：
- **能量 (Energy)**：0-100，影响角色状态
- **心情 (Mood)**：文本描述，角色当前情绪
- **亲密度 (Intimacy)**：点数 + 等级 (L1-L5)

**Web 交互演示新特性：**
- **角色/日期选择器**：在浏览器 GUI 中选择角色和日期，无需命令行参数
- **公网视频支持**：支持从公网 CDN 加载视频（`--public-url` 参数）
- **事件回溯功能**：可以回溯到已完成的事件重新播放
- **时间线展示**：展示完整日程事件列表

**用户沉浸模式 (User Mode)：**
- **9:16竖屏优化**：专为移动端设计的竖屏体验
- **悬浮透明UI**：状态栏和进度指示器悬浮在视频上方，背景透明带模糊效果
- **12种iPhone尺寸支持**：涵盖 iPhone 4 到 iPhone 15 Pro Max 全系列
- **视频优先模式**：自适应高度，完整显示视频无需滚动
- **右下角尺寸菜单**：快速切换不同设备预览尺寸

支持的设备尺寸：
| 尺寸选项 | 分辨率 | 适用设备 |
|---------|--------|----------|
| iPhone 4/5 | 320x568 | iPhone 4, 4S, 5, 5S, 5C, SE |
| iPhone 6/7/8 | 375x667 | iPhone 6, 7, 8 (常规版) |
| iPhone 6/7/8 Plus | 414x736 | iPhone 6+, 7+, 8+ |
| iPhone X/11/12/13 | 390x844 | iPhone X, XS, 11 Pro, 12, 13, 14 |
| iPhone XR/11 | 428x926 | iPhone XR, 11, 12, 13, 14 (Plus版) |
| iPhone 14 Pro/15 | 393x852 | iPhone 14 Pro, 15, 15 Pro |
| iPhone 14 Pro Max | 430x932 | iPhone 14 Pro Max |
| iPhone 15 Plus | 430x932 | iPhone 15 Plus |
| iPhone 15 Pro Max | 430x932 | iPhone 15 Pro Max |
| Android S | 360x800 | Android 标准竖屏 |
| Video First | 自动 | 贴合视频，无需滚动 |

---

## 快速开始

### 1. 环境准备

```bash
# 创建虚拟环境
conda create --name zoo_agent python=3.10
conda activate zoo_agent

# 安装依赖
pip install -r requirements.txt

# 或仅安装基础功能（不含视频生成）
pip install requests tqdm
```

### 2. 配置 API Key

编辑 `config.ini` 文件：

```ini
[api]
api_key = YOUR_API_KEY_HERE
base_url = http://192.154.241.225:3000/v1/chat/completions
model = gemini-2.5-pro
temperature = 0.7
max_tokens = 65536
timeout = 800
parse_error_retries = 3

# 图片生成配置
[image_models.nano_banana]
url = https://api.wuyinkeji.com/api/img/nanoBanana-pro
query_url = https://api.wuyinkeji.com/api/img/drawDetail
key = YOUR_NANO_BANANA_KEY
aspect_ratio = 9:16
image_size = 2K

# 视频生成配置
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

# 视频生成通用配置
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

### 3. （可选）下载演示数据

下载示例角色日程和表演数据，立即体验 WebUI：

[**下载演示数据**](https://drive.google.com/drive/folders/1jBIoYJRGgOwfAJfNKK0B42bAcojVCMd_?usp=sharing)

演示数据包含：
- 完整的角色日程
- 事件策划数据
- 导演脚本
- 已生成的表演视频

下载后解压到 `data/` 目录，然后启动 WebUI：

```bash
# 使用演示数据启动 WebUI
python web_interactive_demo.py
```

### 4. 一键运行完整流程

```bash
# 方式一：使用 shell 脚本（推荐）
./run_pipeline.sh leona_001 2026-01-26 --template leona

# 方式二：分步执行
# 步骤1：生成日程和导演脚本
python main.py run leona_001 --template leona

# 步骤2：生成视频表演
python generate_performance.py -c leona_001 -t 2026-01-26

# 步骤3：运行交互系统

# CLI模式（命令行交互）
python interactive_cli.py leona_001 2026-01-26 --gui

# Web模式（推荐，支持浏览器GUI选择角色和日期）
python web_interactive_demo.py

# Web模式，指定端口和公网视频URL
python web_interactive_demo.py --port 8080 --public-url https://cdn.example.com/videos

# 查询和下载视频
python query_videos.py data/performance/leona_001_2026-01-26/generation_report.json
```

---

## 项目结构

```
Interactive_Film_Character_Agent/
├── src/                               # 源代码目录
│   ├── core/                          # 核心 Agent 模块
│   │   ├── agent.py                   # 日程规划 Agent
│   │   ├── director_agent.py          # 导演 Agent
│   │   ├── event_planner.py           # 事件策划 Agent
│   │   ├── formatter.py               # 输出格式化器
│   │   └── interactive_session.py     # 交互会话系统
│   ├── models/                        # 数据模型
│   │   └── models.py                  # 角色和事件数据模型
│   ├── storage/                       # 存储和配置管理
│   │   ├── config.py                  # 配置加载
│   │   ├── context_manager.py         # 角色上下文管理
│   │   ├── template_loader.py         # 角色模板加载
│   │   ├── image_uploader.py          # 图片上传模块
│   │   └── create_character_contexts.py
│   └── video/                         # 视频生成模块
│       ├── unified_api_client.py      # 统一API客户端
│       ├── scene_processor.py         # 场景处理器
│       ├── performance_generator.py   # 演出生成器
│       └── video_task_query.py        # 视频任务查询
├── data/                              # 数据存储目录
│   ├── characters/                    # 角色上下文文件
│   ├── schedule/                      # 日程规划文件
│   ├── events/                        # 事件策划文件
│   ├── director/                      # 导演输出文件
│   ├── performance/                   # 视频表演数据
│   └── history/                       # 选择历史记录
├── assets/                            # 静态资源
│   ├── templates/                     # 13个预设角色模板
│   └── pics/                          # 图片资源
├── templates/                         # HTML模板
│   ├── interactive_demo.html          # 交互演示页面（编辑模式）
│   └── user_mode.html                 # 用户沉浸模式（9:16竖屏）
├── main.py                            # 完整流程主脚本
├── generate_performance.py            # 视频表演生成脚本
├── interactive_cli.py                 # 交互系统 CLI
├── web_interactive_demo.py            # Web交互演示（支持GUI选择器）
├── run_pipeline.sh                    # 一键运行脚本
├── start-tunnel.sh                    # Cloudflare Tunnel 启动脚本
├── stop-all.sh                        # 服务关闭脚本
├── view-logs.sh                       # 日志查看脚本
├── create_character.py                # 角色创建工具
├── director.py                        # 导演生成工具
├── scheduler.py                       # 日程生成工具
├── sr_event.py                        # SR事件生成工具
├── query_videos.py                    # 视频查询与下载工具
├── config.ini                         # API配置文件
├── requirements.txt                   # Python依赖列表
└── README.md                          # 项目文档
```

---

## 命令说明

注：角色后面的编号对应不同用户编号，每个用户应该创建全部相关角色，然后结合其他角色的档案针对单一角色生成日程和视频。

### run_pipeline.sh - 一键运行脚本

```bash
./run_pipeline.sh <character_id> <date> [options]

选项:
  --template TEMPLATE   使用角色模板创建
  --force, -f           强制覆盖已存在的角色
  --use-existing, -e    仅使用已存在的角色
  --schedule-only       只生成日程和导演脚本
  --skip-video          跳过视频生成
  --image-model MODEL   图片模型 (nano_banana, seedream)
  --video-model MODEL   视频模型 (sora2, kling)
  --log-level LEVEL     日志级别 (DEBUG, INFO, WARNING, ERROR)
  --config FILE         配置文件路径

示例:
./run_pipeline.sh leona_001 2026-01-26 --template leona
./run_pipeline.sh auntie_005 2026-01-26 --use-existing --schedule-only
```

### main.py - 完整流程

```bash
python main.py run <character_id> [options]

选项:
  --template TEMPLATE   使用角色模板
  --force, -f           强制覆盖
  --use-existing, -e    使用已存在角色
  --schedule-only       只运行日程规划
  --sr-only             只运行SR事件生成
  --director-only       只运行导演生成
  --no-streaming        使用单次生成模式
```

### generate_performance.py - 视频表演生成

```bash
python generate_performance.py --character <id> --date <date> [options]

选项:
  --schedule, -s        日程JSON文件路径
  --director, -d        导演脚本JSON文件路径
  --image-model, -im    图片模型 (nano_banana, seedream)
  --video-model, -vm    视频模型 (sora2, kling)
  --time-slot, -ts      指定时间段，只生成该时间段内的视频
                        支持多个时间段，用逗号分隔，如: '09:00-11:00,14:00-16:00'
  --log-level, -l       日志级别

示例:
python generate_performance.py -c leona_001 -t 2026-01-26
python generate_performance.py -c leona_001 -t 2026-01-26 -im seedream -vm kling
python generate_performance.py -c leona_001 -t 2026-01-26 --time-slot "09:00-11:00"
python generate_performance.py -c leona_001 -t 2026-01-26 --time-slot "09:00-11:00,14:00-16:00"
```

### interactive_cli.py - 交互系统

```bash
python interactive_cli.py <character_id> <date> [options]

选项:
  --gui                 启用GUI模式（推荐）
  --preset JSON         预设选择的JSON字符串
  --preset-file PATH    预设选择的JSON文件
  --data-dir PATH       数据目录路径
  --no-save             不保存结果到文件

示例:
python interactive_cli.py leona_001 2026-01-26 --gui
python interactive_cli.py leona_001 2026-01-26 --preset '{"09:00-11:00": ["A"]}'
```

### create_character.py - 创建角色

```bash
python create_character.py <character_id> --template <template>

选项:
  --force, -f           强制覆盖已存在的角色

示例:
python create_character.py leona_001 --template leona
```

### web_interactive_demo.py - Web交互演示

```bash
python web_interactive_demo.py [options]

选项:
  --host HOST           服务器地址 (默认: 0.0.0.0)
  --port PORT           服务器端口 (默认: 5000)
  --public-url URL      公网视频URL前缀 (用于从公网加载视频)
  --data-dir PATH       数据目录路径 (默认: data)

示例:
# 使用默认配置启动
python web_interactive_demo.py

# 指定端口
python web_interactive_demo.py --port 8080

# 使用公网视频
python web_interactive_demo.py --public-url https://cdn.example.com/videos

# 组合使用
python web_interactive_demo.py --port 8080 --public-url https://cdn.example.com/videos

注意：角色和日期请在浏览器界面左上角的选择器中选择，无需命令行参数。
```

### query_videos.py - 视频查询与下载

```bash
python query_videos.py <report_path> [options]

参数:
  report_path           生成报告JSON文件路径

选项:
  -o, --output PATH    视频输出目录（默认与报告同目录）
  -w, --workers NUM   最大并发线程数（默认5）
  -k, --api-key KEY    无引科技API密钥（默认从config.ini读取）

示例:
python query_videos.py data/performance/leona_001_2026-01-26/generation_report.json
python query_videos.py data/performance/leona_001_2026-01-26/generation_report.json -o videos/
python query_videos.py data/performance/leona_001_2026-01-26/generation_report.json -w 10
```

### 穿透部署脚本 (Deployment Scripts)

**start-tunnel.sh** - 一键启动服务（Cloudflare Tunnel 穿透）

```bash
# 启动所有服务（Flask + Cloudflare Tunnel）
./start-tunnel.sh

# 获取公网访问地址
tail -50 /tmp/cloudflared.log | grep 'https://'
```

**特性：**
- 自动检测工作目录，支持任意克隆目录直接运行
- 无需预配置 systemd 服务
- 保留彩色日志输出（FORCE_COLOR + PYTHONUNBUFFERED）
- 自动生成临时公网地址

**stop-all.sh** - 关闭所有服务

```bash
# 停止 Flask 和 Cloudflare Tunnel
./stop-all.sh
```

**view-logs.sh** - 查看彩色日志

```bash
./view-logs.sh

# 选项：
# 1) Flask 实时访问日志
# 2) Cloudflare Tunnel 实时日志
# 3) Flask 最近 50 条访问记录
# 4) 当前在线访问统计
# 5) 退出
```

**日志输出位置：**
- Flask 日志：`/tmp/zooo-agent.log`
- Cloudflare 日志：`/tmp/cloudflared.log`

---

## 可用角色模板

| 模板ID | 角色 | MBTI | 类型 | 描述 |
|--------|------|------|------|------|
| luna | 露娜 | INFP | 艺术/梦幻 | 怀抱梦想的年轻艺术家，在日常生活中发现美 |
| alex | 亚历克斯 | ENTJ | 领袖/进取 | 科技创业公司创始人，野心勃勃且关心团队 |
| maya | 玛雅 | ESFP | 自由/奔放 | 街头音乐人，活在当下，充满魅力 |
| daniel | 丹尼尔 | ISFJ | 安静/观察者 | 书店老板，体贴周到，默默关心社区 |

---

## 亲密度等级系统

```
L5 - Soulmate      (200+)      灵魂伴侣
L4 - Deep Bond     (150-199)   深度羁绊
L3 - Close Friend  (100-149)   亲密好友
L2 - Friend        (50-99)     普通朋友
L1 - Stranger      (0-49)      陌生相识
```

---

## 输出文件结构

```
data/
├── characters/
│   └── {character_id}_context.json           # 角色上下文
├── schedule/
│   └── {character_id}_schedule_{date}.json   # 日程规划
├── events/
│   └── {character_id}_events_{date}.json     # 事件策划 (R/SR)
├── director/
│   └── {character_id}_director_{date}.json   # 导演输出
├── performance/
│   └── {character_id}_{date}/                # 视频表演数据
│       ├── *.mp4                            # 生成的视频文件
│       ├── *.jpg                            # 生成的图片文件
│       └── generation_report.json            # 生成报告
└── history/                                  # 选择历史
    └── {character_id}_choices_{date}.json
```

---

## 依赖说明

### 基础依赖（必需）

```
requests>=2.32.0
tqdm>=4.66.0
```

### 可选依赖

```bash
# 图片生成（Seedream）
volcengine-python-sdk[ark]>=1.0.0

# GUI视频播放
opencv-python>=4.8.0
pillow>=10.0.0
```

---

## 配置文件详解

### [api] - AI模型配置

```ini
api_key              = YOUR_API_KEY
base_url             = http://192.154.241.225:3000/v1/chat/completions
model                = gemini-2.5-pro
temperature          = 0.7
max_tokens           = 65536
timeout              = 800
parse_error_retries  = 3          # 解析错误重试次数
```

### [image_models.*] - 图片生成配置

支持两种图片模型：`nano_banana`、`seedream`

```ini
[image_models.nano_banana]
url             = https://api.wuyinkeji.com/api/img/nanoBanana-pro
aspect_ratio    = 9:16
image_size      = 2K
```

### [video_models.*] - 视频生成配置

支持两种视频模型：`sora2`、`kling`

```ini
[video_models.sora2]
url             = https://api.wuyinkeji.com/api/sora2-new/submit
query_url       = https://api.wuyinkeji.com/api/sora2/detail
aspect_ratio    = 9:16
duration        = 15               # 15 或 25 (sora2pro)
size            = small

[video_models.kling]
url             = https://api-beijing.klingai.com/v1/videos/image2video
model           = kling-v2-6        # kling-v1, kling-v1-5, kling-v1-6, kling-v2-master, kling-v2-1, kling-v2-5-turbo, kling-v2-6
mode            = pro                # std (标准) 或 pro (专家/高品质)
duration        = 10                # 5 或 10
cfg_scale       = 0.5               # 取值范围 [0, 1]
sound           = off                # on 或 off (仅V2.6+支持)
```

### [video_generation] - 视频生成通用配置

```ini
default_image_model       = nano_banana
default_video_model      = sora2
max_workers              = 50
poll_interval            = 10

# 超时重试配置
video_timeout_seconds    = 1800      # 视频生成问询超时时间（秒）
image_timeout_seconds    = 600       # 图片生成问询超时时间（秒）
max_retry_on_timeout    = 3          # 超时后最大重试次数
timeout_retry_enabled   = true       # 超时重试是否启用
```

### [image_upload] - 图片上传配置（本地图片 -> 云端URL）

```ini
url                 = YOUR_UPLOAD_API_URL
user_id             = 2
authorization       = YOUR_TOKEN
platform            = android
device_id           = 1
app_version         = 1.0.4.1
upload_type         = DAILY_AGENT
```

### [daily_event_count] - 每日事件数量配置

```ini
daily_r_events   = 2       # 每天R类事件数量（固定）
daily_sr_events  = 1       # 每天SR类事件数量（固定）
```

### [event_character_count] - 事件角色数量概率配置

```ini
# N类事件：min_prob=0.9 -> 0.9概率1人，0.1概率2人
n_min_count  = 1
n_max_count  = 2
n_min_prob   = 0.9

# R类事件：min_prob=0.7 -> 0.7概率2人，0.3概率3人
r_min_count  = 2
r_max_count  = 3
r_min_prob   = 0.7

# SR类事件：min_prob=0.5 -> 0.5概率3人，0.5概率4人
sr_min_count = 3
sr_max_count = 4
sr_min_prob  = 0.5
```

---

## 常见问题

### Q: 如何选择图片和视频模型组合？

A: 目前支持4种组合：
- `nano_banana + sora2`（默认）
- `nano_banana + kling`
- `seedream + sora2`
- `seedream + kling`

### Q: 视频生成失败或超时怎么办？

A: 系统内置超时自动重试机制，无需手动处理。如需查询状态，使用 `query_videos.py`：

```bash
python query_videos.py data/performance/leona_001_2026-01-26/generation_report.json
```

### Q: 如何只生成特定时间段的视频？

A: 使用 `--time-slot` 参数指定时间段：

```bash
# 生成单个时间段
python generate_performance.py -c leona_001 -t 2026-01-26 --time-slot "09:00-11:00"

# 生成多个时间段（逗号分隔）
python generate_performance.py -c leona_001 -t 2026-01-26 --time-slot "09:00-11:00,14:00-16:00"
```

### Q: 如何只生成日程不生成视频？

A: 使用 `--schedule-only` 选项：

```bash
./run_pipeline.sh leona_001 2026-01-26 --template leona --schedule-only
```

### Q: Web演示如何从公网加载视频？

A: 启动时指定 `--public-url` 参数：

```bash
python web_interactive_demo.py --public-url https://cdn.example.com/videos
```

### Q: 如何配置每日事件数量？

A: 在 `config.ini` 中修改 `[daily_event_count]` 配置：

```ini
[daily_event_count]
daily_r_events   = 2
daily_sr_events  = 1
```

---

## 技术栈

- **编程语言**: Python 3.10+
- **AI模型**: Gemini 2.5 Pro
- **并发处理**: ThreadPoolExecutor
- **数据格式**: JSON
- **图片生成**: nano_banana (无引科技)、seedream (火山引擎)
- **视频生成**: sora2 (无引科技)、kling (可灵AI)

---

<div align="center">

**AI角色内容生成系统**

</div>
