#!/usr/bin/env python3
"""
视频生成命令行工具
根据角色日程和导演脚本生成视频
支持多种图片和视频生成模型的独立选择
"""

import sys
import os
import argparse
import logging

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.video import PerformanceGenerator


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """设置日志"""
    level = getattr(logging, log_level.upper(), logging.INFO)

    handlers = [logging.StreamHandler()]

    if log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        handlers.append(logging.FileHandler(log_file, encoding='utf-8'))

    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers
    )


def get_output_dir(config_path: str, character_id: str, date: str) -> str:
    """获取输出目录路径"""
    import configparser
    config = configparser.ConfigParser()
    config.read(config_path, encoding='utf-8')

    output_base_dir = config.get("performance", "output_dir", fallback="data/performance")
    return os.path.join(output_base_dir, f"{character_id}_{date}")


def main():
    parser = argparse.ArgumentParser(
        description="根据角色日程和导演脚本生成视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:

  # 使用默认模型
  python generate_performance.py -c luna_001 -t 2026-01-16

  # 指定图片和视频模型
  python generate_performance.py -c luna_001 -t 2026-01-16 -im seedream -vm kling

  # 只生成特定时间段（单个时间段）
  python generate_performance.py -c alex_001 -t 2026-01-16 --time-slot "09:00-11:00"

  # 只生成特定时间段（多个时间段）
  python generate_performance.py -c maya_001 -t 2026-01-16 --time-slot "09:00-11:00,14:00-16:00"

  # 模型选择
    图片模型: nano_banana (无引科技) | seedream (火山引擎)
    视频模型: sora2 (无引科技) | kling (可灵AI)

  # 自由组合
  python generate_performance.py -c daniel_001 -t 2026-01-16 -im seedream -vm kling
  python generate_performance.py -c luna_001 -t 2026-01-16 -im nano_banana -vm sora2
  python generate_performance.py -c alex_001 -t 2026-01-16 -im nano_banana -vm kling

  python generate_performance.py -c maya_001 -t 2026-01-16 -im seedream -vm sora2
  python generate_performance.py -c daniel_001 -t 2026-01-16 --time-slot "09:00-11:00" -im seedream -vm kling
        """
    )

    parser.add_argument(
        "--schedule", "-s",
        help="日程JSON文件路径"
    )
    parser.add_argument(
        "--director", "-d",
        help="导演脚本JSON文件路径"
    )
    parser.add_argument(
        "--character", "-c",
        required=True,
        help="角色ID (如: luna_001)"
    )
    parser.add_argument(
        "--date", "-t",
        required=True,
        help="日期 (如: 2026-01-16)"
    )
    parser.add_argument(
        "--log-level", "-l",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别"
    )
    parser.add_argument(
        "--config",
        default="config.ini",
        help="配置文件路径"
    )
    parser.add_argument(
        "--image-model", "-im",
        default=None,
        choices=["nano_banana", "seedream"],
        help="图片生成模型 (nano_banana, seedream)"
    )
    parser.add_argument(
        "--video-model", "-vm",
        default=None,
        choices=["sora2", "kling"],
        help="视频生成模型 (sora2, kling)"
    )
    parser.add_argument(
        "--time-slot", "-ts",
        default=None,
        help="指定时间段，只生成该时间段内的视频。支持多个时间段，用逗号分隔，如: '09:00-11:00' 或 '09:00-11:00,14:00-16:00'"
    )

    args = parser.parse_args()

    # 处理时间段参数
    time_slots = None
    if args.time_slot:
        # 支持逗号分隔的多个时间段
        time_slots = [ts.strip() for ts in args.time_slot.split(',') if ts.strip()]

    # 构建文件路径
    if args.schedule is None:
        args.schedule = f"data/schedule/{args.character}_schedule_{args.date}.json"

    if args.director is None:
        args.director = f"data/director/{args.character}_director_{args.date}.json"

    # 检查文件是否存在
    if not os.path.exists(args.schedule):
        print(f"错误: 日程文件不存在: {args.schedule}")
        sys.exit(1)

    if not os.path.exists(args.director):
        print(f"错误: 导演脚本文件不存在: {args.director}")
        sys.exit(1)

    # 获取输出目录并设置日志
    output_dir = get_output_dir(args.config, args.character, args.date)
    os.makedirs(output_dir, exist_ok=True)
    log_file = os.path.join(output_dir, "generation.log")

    setup_logging(args.log_level, log_file)
    logger = logging.getLogger(__name__)

    # 检查配置文件
    if not os.path.exists(args.config):
        logger.warning(f"配置文件不存在: {args.config}，将使用默认配置")

    # 开始生成
    logger.info("=" * 60)
    logger.info("视频生成工具")
    logger.info("=" * 60)
    logger.info(f"角色: {args.character}")
    logger.info(f"日期: {args.date}")
    logger.info(f"日程文件: {args.schedule}")
    logger.info(f"导演脚本: {args.director}")
    logger.info(f"输出目录: {output_dir}")
    logger.info(f"日志文件: {log_file}")
    if time_slots:
        logger.info(f"指定时间段: {', '.join(time_slots)}")
    logger.info("=" * 60)

    try:
        generator = PerformanceGenerator(
            config_path=args.config,
            image_model=args.image_model,
            video_model=args.video_model
        )

        # 打印模型选择信息
        print(f"\n图片模型: {generator.image_model}")
        print(f"视频模型: {generator.video_model}\n")

        results = generator.generate(
            schedule_path=args.schedule,
            director_path=args.director,
            character_id=args.character,
            date=args.date,
            time_slots=time_slots
        )

        # 打印结果摘要
        if results.get("summary"):
            summary = results["summary"]
            print("\n" + "=" * 60)
            print("生成完成！")
            print("=" * 60)

            print("\nN类事件（单幕场景）:")
            n_summary = summary["n_events"]
            print(f"  总数: {n_summary['total']}")
            print(f"  生成图片: {n_summary['images_generated']}")
            print(f"  生成视频: {n_summary['videos_generated']}")

            print("\nR类事件（多幕场景）:")
            r_summary = summary["r_events"]
            print(f"  总数: {r_summary['total']}")
            print(f"  场景数: {r_summary['scenes']}")
            print(f"  生成图片: {r_summary['images_generated']}")
            print(f"  生成视频: {r_summary['videos_generated']}")

            print("\nSR类事件（多幕场景）:")
            sr_summary = summary["sr_events"]
            print(f"  总数: {sr_summary['total']}")
            print(f"  场景数: {sr_summary['scenes']}")
            print(f"  生成图片: {sr_summary['images_generated']}")
            print(f"  生成视频: {sr_summary['videos_generated']}")

            total = summary["total"]
            print("\n总计:")
            print(f"  生成图片: {total['images']}")
            print(f"  生成视频: {total['videos']}")

            print(f"\n输出目录: {results['output_dir']}")
            print(f"日志文件: {log_file}")
            print("=" * 60)

        sys.exit(0)

    except Exception as e:
        logger.error(f"生成过程出错: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
