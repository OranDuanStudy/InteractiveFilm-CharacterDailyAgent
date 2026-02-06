#!/usr/bin/env python3
"""
生成交互式 JSON 数据
用于重新生成已存在的 performance 目录的 interactive_data.json
"""

import sys
import os
import json
import argparse
from src.video.performance_generator import PerformanceGenerator


def main():
    parser = argparse.ArgumentParser(
        description="生成交互式 JSON 数据（不重新生成视频）"
    )
    parser.add_argument(
        "--character", "-c",
        required=True,
        help="角色ID (如: luna_001)"
    )
    parser.add_argument(
        "--date", "-d",
        required=True,
        help="日期 (如: 2026-01-27)"
    )
    parser.add_argument(
        "--config",
        default="config.ini",
        help="配置文件路径"
    )

    args = parser.parse_args()

    # 构建文件路径
    schedule_path = f"data/schedule/{args.character}_schedule_{args.date}.json"
    director_path = f"data/director/{args.character}_director_{args.date}.json"
    events_path = f"data/events/{args.character}_events_{args.date}.json"
    output_dir = f"data/performance/{args.character}_{args.date}"

    # 检查文件是否存在
    if not os.path.exists(schedule_path):
        print(f"错误: 日程文件不存在: {schedule_path}")
        sys.exit(1)

    if not os.path.exists(director_path):
        print(f"错误: 导演脚本文件不存在: {director_path}")
        sys.exit(1)

    if not os.path.exists(events_path):
        print(f"错误: 事件文件不存在: {events_path}")
        sys.exit(1)

    if not os.path.exists(output_dir):
        print(f"错误: 输出目录不存在: {output_dir}")
        sys.exit(1)

    # 检查是否有 generation_report.json
    report_path = os.path.join(output_dir, "generation_report.json")
    if not os.path.exists(report_path):
        print(f"错误: 生成报告文件不存在: {report_path}")
        sys.exit(1)

    # 加载生成报告以获取已有的结果
    with open(report_path, 'r', encoding='utf-8') as f:
        results = json.load(f)

    print(f"正在生成交互式数据: {args.character}_{args.date}")
    print(f"  日程文件: {schedule_path}")
    print(f"  导演脚本: {director_path}")
    print(f"  事件文件: {events_path}")
    print(f"  生成报告: {report_path}")
    print(f"  输出目录: {output_dir}")

    # 创建 PerformanceGenerator 实例（只用于访问 _save_interactive_json 方法）
    generator = PerformanceGenerator(
        config_path=args.config,
        image_model=None,
        video_model=None
    )

    # 调用 _save_interactive_json 方法
    generator._save_interactive_json(
        output_dir=output_dir,
        results=results,
        schedule_path=schedule_path,
        events_path=events_path,
        time_slots=None
    )

    # 检查生成的文件
    interactive_path = os.path.join(output_dir, "interactive_data.json")
    if os.path.exists(interactive_path):
        with open(interactive_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"\n生成成功！")
        print(f"  输出文件: {interactive_path}")
        print(f"  事件数量: {len(data.get('events', []))}")
    else:
        print(f"\n错误: 生成的文件不存在: {interactive_path}")


if __name__ == "__main__":
    main()
