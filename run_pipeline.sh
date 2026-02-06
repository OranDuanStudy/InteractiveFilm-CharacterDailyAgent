#!/bin/bash

###############################################################################
# Interactive Film Character Daily Agent - 完整工作流程脚本
#
# 功能：串联 main.py 和 generate_performance.py，完成从日程生成到视频生成的完整流程
#
# 用法：
#   ./run_pipeline.sh <character_id> <date> [options]
#
# 示例：
#   ./run_pipeline.sh luna_001 2026-01-26
#   ./run_pipeline.sh alex_005 2026-01-26 --template alex
#   ./run_pipeline.sh maya_001 2026-01-26 --use-existing
#
###############################################################################

clear
cat << "EOF"

▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

 _____   ____  ____  ____     ____        _ __     
/__  /  / __ \/ __ \/ __ \   / __ \____ _(_) /_  __
  / /  / / / / / / / / / /  / / / / __ `/ / / / / /
 / /__/ /_/ / /_/ / /_/ /  / /_/ / /_/ / / / /_/ / 
/____/\____/\____/\____/  /_____/\__,_/_/_/\__, /  
                                          /____/   
    ___                    __ 
   /   | ____ ____  ____  / /_
  / /| |/ __ `/ _ \/ __ \/ __/
 / ___ / /_/ /  __/ / / / /_  
/_/  |_\__, /\___/_/ /_/\__/  
      /____/ 

▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

EOF

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印函数
print_header() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_step() {
    echo -e "${GREEN}▶ $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ 错误: $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ 警告: $1${NC}"
}

# 显示帮助信息
show_help() {
    cat << EOF
用法: $0 <character_id> <date> [options]

参数:
  character_id          角色ID (如: luna_001, alex_005, maya_001)
  date                  日期 (如: 2026-01-26)

选项:
  --template TEMPLATE    使用角色模板创建 (可选: example_character, luna, alex, maya, daniel)
  --force, -f            强制覆盖已存在的角色
  --use-existing, -e     仅使用已存在的角色
  --schedule-only        只运行日程规划 + 导演生成，跳过视频生成
  --skip-video           跳过视频生成阶段
  --image-model MODEL    图片生成模型 (nano_banana, seedream)
  --video-model MODEL    视频生成模型 (sora2, kling)
  --log-level LEVEL      日志级别 (DEBUG, INFO, WARNING, ERROR)
  --config FILE          配置文件路径 (默认: config.ini)
  --no-streaming         main.py 使用单次生成模式
  -h, --help             显示此帮助信息

示例:
  # 完整流程（新角色）
  $0 luna_001 2026-01-26 --template luna

  # 完整流程（已存在角色）
  $0 alex_005 2026-01-26 --use-existing

  # 只生成日程和导演脚本，不生成视频
  $0 maya_001 2026-01-26 --use-existing --schedule-only

  # 指定图片和视频模型
  $0 daniel_001 2026-01-26 --use-existing --image-model seedream --video-model kling

EOF
}

# 默认参数
TEMPLATE=""
USE_EXISTING=false
FORCE=false
SCHEDULE_ONLY=false
SKIP_VIDEO=false
IMAGE_MODEL=""
VIDEO_MODEL=""
LOG_LEVEL="INFO"
CONFIG="config.ini"
NO_STREAMING=""

# 解析参数
if [ $# -lt 2 ]; then
    show_help
    exit 1
fi

CHARACTER_ID="$1"
DATE="$2"
shift 2

while [[ $# -gt 0 ]]; do
    case $1 in
        --template|-t)
            TEMPLATE="$2"
            shift 2
            ;;
        --force|-f)
            FORCE=true
            shift
            ;;
        --use-existing|-e)
            USE_EXISTING=true
            shift
            ;;
        --schedule-only)
            SCHEDULE_ONLY=true
            shift
            ;;
        --skip-video)
            SKIP_VIDEO=true
            shift
            ;;
        --image-model)
            IMAGE_MODEL="$2"
            shift 2
            ;;
        --video-model)
            VIDEO_MODEL="$2"
            shift 2
            ;;
        --log-level|-l)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --config)
            CONFIG="$2"
            shift 2
            ;;
        --no-streaming)
            NO_STREAMING="--no-streaming"
            shift
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac
done

# 验证日期格式
if [[ ! $DATE =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    print_error "日期格式错误，应为 YYYY-MM-DD 格式"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

###############################################################################
# 阶段 1: 角色创建/加载 + 日程规划 + SR事件创立 + 导演模式
###############################################################################

print_header "阶段 1: 日程和导演脚本生成"

MAIN_ARGS="run $CHARACTER_ID"

if [ "$USE_EXISTING" = true ]; then
    MAIN_ARGS="$MAIN_ARGS --use-existing"
elif [ -n "$TEMPLATE" ]; then
    MAIN_ARGS="$MAIN_ARGS --template $TEMPLATE"
fi

if [ "$FORCE" = true ]; then
    MAIN_ARGS="$MAIN_ARGS --force"
fi

if [ -n "$NO_STREAMING" ]; then
    MAIN_ARGS="$MAIN_ARGS $NO_STREAMING"
fi

print_step "执行 main.py 生成日程和导演脚本..."
echo "命令: python main.py $MAIN_ARGS"

if python main.py $MAIN_ARGS; then
    print_success "日程和导演脚本生成完成"
else
    print_error "main.py 执行失败"
    exit 1
fi

###############################################################################
# 阶段 2: 视频生成
###############################################################################

if [ "$SCHEDULE_ONLY" = true ] || [ "$SKIP_VIDEO" = true ]; then
    print_header "跳过视频生成阶段"
    print_warning "已指定 --schedule-only 或 --skip-video，不执行视频生成"
    print_success "流程完成！"
    echo ""
    echo "输出文件位置:"
    echo "  日程文件: data/schedule/${CHARACTER_ID}_schedule_${DATE}.json"
    echo "  导演文件: data/director/${CHARACTER_ID}_director_${DATE}.json"
    exit 0
fi

print_header "阶段 2: 视频生成"

# 检查文件是否存在
SCHEDULE_FILE="data/schedule/${CHARACTER_ID}_schedule_${DATE}.json"
DIRECTOR_FILE="data/director/${CHARACTER_ID}_director_${DATE}.json"

if [ ! -f "$SCHEDULE_FILE" ]; then
    print_error "日程文件不存在: $SCHEDULE_FILE"
    exit 1
fi

if [ ! -f "$DIRECTOR_FILE" ]; then
    print_error "导演文件不存在: $DIRECTOR_FILE"
    exit 1
fi

PERF_ARGS="--character $CHARACTER_ID --date $DATE"

if [ -n "$IMAGE_MODEL" ]; then
    PERF_ARGS="$PERF_ARGS --image-model $IMAGE_MODEL"
fi

if [ -n "$VIDEO_MODEL" ]; then
    PERF_ARGS="$PERF_ARGS --video-model $VIDEO_MODEL"
fi

if [ -n "$LOG_LEVEL" ]; then
    PERF_ARGS="$PERF_ARGS --log-level $LOG_LEVEL"
fi

PERF_ARGS="$PERF_ARGS --config $CONFIG"

print_step "执行 generate_performance.py 生成视频..."
echo "命令: python generate_performance.py $PERF_ARGS"

if python generate_performance.py $PERF_ARGS; then
    print_success "视频生成完成"
else
    print_error "generate_performance.py 执行失败"
    exit 1
fi

###############################################################################
# 完成
###############################################################################

print_header "流程完成！"

echo ""
echo "输出文件位置:"
echo "  日程文件: $SCHEDULE_FILE"
echo "  导演文件: $DIRECTOR_FILE"
echo "  视频输出: data/performance/${CHARACTER_ID}_${DATE}/"
echo ""

print_success "所有任务已完成！"
