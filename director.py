#!/usr/bin/env python3
"""
导演 Agent - SR 事件输出生成脚本

读取 sr_events.json，为每个 SR 事件生成导演输出

用法:
    python director.py --input <sr_events.json> --character <character_context.json>
"""
import argparse
import json
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import (
    DirectorAgent,
    FullInputContext,
)
from src.storage import load_config


def load_sr_events(input_path: str) -> dict:
    """加载 SR 事件 JSON 文件"""
    print(f"[debug] 正在加载 SR 事件文件: {input_path}")
    path = Path(input_path)
    if not path.exists():
        print(f"❌ SR 事件文件不存在: {input_path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"[debug] SR 事件文件已加载")
    print(f"[debug] 日程信息: 角色={data.get('schedule_info', {}).get('character')}, 日期={data.get('schedule_info', {}).get('date')}")
    print(f"[debug] SR 事件数量: {len(data.get('sr_events', []))}")

    return data


def load_character_context(character_path: str) -> FullInputContext:
    """加载人物上下文 JSON 文件"""
    print(f"[debug] 正在加载人物上下文: {character_path}")
    path = Path(character_path)
    if not path.exists():
        print(f"❌ 人物上下文文件不存在: {character_path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    context = FullInputContext.from_dict(data)
    print(f"[debug] 人物上下文已加载: {context.character_dna.name}")
    return context


def format_scene_output(scene: dict) -> str:
    """格式化单个场景输出"""
    lines = []
    lines.append("=" * 60)
    lines.append(f"{scene['scene_title']}")
    lines.append("=" * 60)
    lines.append("")

    # 剧情简述、台词与镜头设计
    lines.append("【剧情简述、台词与镜头设计】")
    lines.append(scene['narrative'])
    lines.append("")

    # 首帧生图 Prompt
    lines.append("【首帧生图 Prompt (First Frame Image)】")
    lines.append(scene['image_prompt'])
    lines.append("")

    # 角色档案 Profile
    if scene.get('character_profile'):
        lines.append("【角色档案 (Character Profile)】")
        lines.append(scene['character_profile'])
        lines.append("")

    # Sora 视频生成提示词
    lines.append("【Sora 视频生成提示词 (Multi-Shot Prompt + Tags)】")
    lines.append(scene['sora_prompt'])
    lines.append("")

    # 风格标签
    if scene.get('style_tags'):
        lines.append("【风格标签 (Style Tags)】")
        lines.append(scene['style_tags'])
        lines.append("")

    # BGM Prompt
    if scene.get('bgm_prompt'):
        lines.append("【Suno BGM 生成提示词】")
        lines.append(scene['bgm_prompt'])
        lines.append("")

    return "\n".join(lines)


def generate_director_output(
    sr_events_path: str,
    character_path: str,
    output_path: str = None
) -> dict:
    """
    为 SR 事件生成导演输出

    Args:
        sr_events_path: SR 事件 JSON 文件路径
        character_path: 人物上下文 JSON 文件路径
        output_path: 输出文件路径（可选）

    Returns:
        dict: 导演输出数据
    """
    print("[debug] generate_director_output() 被调用")
    print(f"[debug] SR 事件文件: {sr_events_path}")
    print(f"[debug] 人物文件: {character_path}")

    # 加载数据
    sr_data = load_sr_events(sr_events_path)
    character_context = load_character_context(character_path)

    sr_events = sr_data.get("sr_events", [])
    if not sr_events:
        print("⚠️ 没有找到 SR 事件!")
        return {}

    # 加载配置
    print("[debug] 正在加载配置...")
    config = load_config()
    print("[debug] 配置已加载")

    # 为每个 SR 事件生成导演输出
    results = []
    director = DirectorAgent(config)

    for i, sr_event in enumerate(sr_events):
        print(f"\n{'='*60}")
        print(f"[debug] 正在处理第 {i+1}/{len(sr_events)} 个 SR 事件")
        print(f"[debug] 时间段: {sr_event.get('time_slot')}")
        print(f"[debug] 事件名: {sr_event.get('event_name')}")

        # 生成导演输出
        print("[debug] 正在生成导演输出...")
        output = director.elaborate_sr_event(sr_event, character_context)
        print("[debug] 导演输出已生成")

        # 转换为字典并保存
        output_dict = output.to_dict()
        results.append(output_dict)

        print(f"✅ SR 事件 {i+1} 导演输出已生成")
        print(f"   场景数量: {len(output.scenes)}")

    # 组装输出数据
    schedule_info = sr_data.get("schedule_info", {})

    final_output = {
        "schedule_info": schedule_info,
        "director_outputs": results,
    }

    # 保存结果
    if output_path is None:
        # 标准化输出路径: data/director/{character_id}_director_{date}.json
        character_id = character_context.actor_state.character_id
        date = schedule_info.get("date", "unknown_date")
        output_dir = Path(__file__).parent / "data" / "director"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{character_id}_director_{date}.json")

    print(f"\n[debug] 正在保存导演输出到: {output_path}")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print(f"✅ 导演输出已保存到: {output_path}")

    return final_output


def main():
    print("[debug] SR 事件导演脚本启动...")
    parser = argparse.ArgumentParser(
        description="SR 事件导演输出生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 为 SR 事件生成导演输出
  python director.py --input data/events/schedule_sr_events.json --character data/characters/judy_001_context.json

  # 指定输出文件
  python director.py -i data/events/my_event.json -c data/characters/judy_001_context.json -o data/director/director_output.json

注意: 配置会自动从 config.ini 加载
        """
    )

    parser.add_argument(
        "--input", "-i",
        type=str,
        required=True,
        help="SR 事件 JSON 文件路径"
    )

    parser.add_argument(
        "--character", "-c",
        type=str,
        required=True,
        help="人物上下文 JSON 文件路径"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help="输出 JSON 文件路径 (默认: data/director/{character_id}_director_{date}.json)"
    )

    args = parser.parse_args()
    print(f"[debug] 解析参数: input={args.input}, character={args.character}, output={args.output}")

    generate_director_output(
        sr_events_path=args.input,
        character_path=args.character,
        output_path=args.output
    )

    print("[debug] SR 事件导演脚本结束")


if __name__ == "__main__":
    main()
