#!/usr/bin/env python3
"""
视频任务查询和下载CLI
从生成报告查询任务状态并下载完成的视频
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from src.video import query_and_download_videos
from src.storage.config import load_video_model_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='查询视频任务状态并下载完成的视频',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
示例用法:
  # 使用默认配置查询
  python query_videos.py data/performance/luna_002_2026-01-16/generation_report.json

  # 指定输出目录
  python query_videos.py data/performance/luna_002_2026-01-16/generation_report.json -o videos/

  # 指定并发数
  python query_videos.py data/performance/luna_002_2026-01-16/generation_report.json -w 10
        '''
    )

    parser.add_argument(
        'report',
        help='生成报告JSON文件路径'
    )

    parser.add_argument(
        '-o', '--output',
        dest='output_dir',
        help='视频输出目录（默认与报告同目录）'
    )

    parser.add_argument(
        '-w', '--workers',
        type=int,
        default=5,
        help='最大并发线程数（默认5）'
    )

    parser.add_argument(
        '-k', '--api-key',
        dest='api_key',
        help='无引科技API密钥（默认从config.ini读取）'
    )

    args = parser.parse_args()

    # 检查报告文件是否存在
    report_path = args.report
    if not Path(report_path).exists():
        logger.error(f"报告文件不存在: {report_path}")
        return 1

    # 获取API密钥
    api_key = args.api_key
    if not api_key:
        # 从配置文件读取
        try:
            config = load_video_model_config()
            api_key = config.sora2_key
        except Exception as e:
            logger.error(f"读取配置失败: {e}")
            return 1

    if not api_key:
        logger.error("未找到API密钥，请通过 -k 参数指定或在 config.ini 中配置")
        return 1

    # 执行查询和下载
    logger.info(f"报告文件: {report_path}")
    logger.info(f"输出目录: {args.output_dir or '与报告同目录'}")
    logger.info(f"并发线程数: {args.workers}")
    logger.info("")

    try:
        result = query_and_download_videos(
            report_path=report_path,
            api_key=api_key,
            output_dir=args.output_dir,
            max_workers=args.workers
        )

        # 打印结果
        print()
        print("=" * 60)
        print("处理完成!")
        print("=" * 60)
        print(f"总计: {result['total']}")
        print(f"成功: {result['success']}")
        print(f"失败: {result['failed']}")
        print(f"超时: {result['timeout']}")
        print(f"耗时: {result['elapsed_time']:.1f}秒")
        print("=" * 60)

        return 0 if result['success'] > 0 else 1

    except Exception as e:
        logger.error(f"执行失败: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
