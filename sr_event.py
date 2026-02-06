"""
SR 事件生成器

用法:
    python sr_event.py --plot "剧情梗概"
    python sr_event.py --interactive
    python sr_event.py --schedule <日程文件.json> --character <人物上下文.json>
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

from src.core import EventPlanner
from src.models import (
    FullInputContext,
    CharacterNarrativeDNA,
    ActorDynamicState,
    UserProfile,
    WorldContext,
    MutexLock,
    MBTIType,
    Alignment,
    WeatherType,
    TimeOfDay,
)
from src.storage import load_config


# ==================== 文件加载函数 ====================

def load_schedule_file(schedule_path: str) -> Dict:
    """
    加载日程规划JSON文件

    Args:
        schedule_path: 日程文件路径

    Returns:
        dict: 日程数据
    """
    print(f"[Debug] 正在加载日程文件: {schedule_path}")
    path = Path(schedule_path)
    if not path.exists():
        print(f"❌ 日程文件不存在: {schedule_path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        schedule = json.load(f)

    print(f"[Debug] 日程已加载: 角色={schedule.get('character')}, 日期={schedule.get('date')}")
    return schedule


def load_character_context(context_path: str) -> FullInputContext:
    """
    加载人物上下文JSON文件

    Args:
        context_path: 人物上下文文件路径

    Returns:
        FullInputContext: 人物上下文对象
    """
    print(f"[Debug] 正在加载人物上下文: {context_path}")
    path = Path(context_path)
    if not path.exists():
        print(f"❌ 人物上下文文件不存在: {context_path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 从JSON重建FullInputContext对象
    context = FullInputContext.from_dict(data)
    print(f"[Debug] 人物上下文已加载: {context.character_dna.name}")
    return context


def find_sr_events(schedule: Dict) -> List[Dict]:
    """
    从日程中查找所有SR事件

    Args:
        schedule: 日程数据

    Returns:
        list: SR事件列表
    """
    print("[Debug] 正在查找日程中的SR事件...")
    sr_events = []

    for event in schedule.get("events", []):
        if event.get("event_type") == "SR":
            sr_events.append(event)

    print(f"[Debug] 找到 {len(sr_events)} 个SR事件")
    for i, event in enumerate(sr_events):
        print(f"[Debug]   SR事件 {i+1}: {event.get('time_slot')} - {event.get('event_name')}")

    return sr_events


def generate_sr_from_schedule(
    schedule_path: str,
    character_path: str,
    output_path: Optional[str] = None
) -> List[dict]:
    """
    从日程文件和人物文件生成SR卡

    Args:
        schedule_path: 日程文件路径
        character_path: 人物上下文文件路径
        output_path: 输出JSON文件路径（默认与日程文件同目录下按时间段命名）

    Returns:
        list: 生成的SR卡数据列表
    """
    print("[Debug] generate_sr_from_schedule() 被调用")
    print(f"[Debug] 日程文件: {schedule_path}")
    print(f"[Debug] 人物文件: {character_path}")

    # 加载文件
    schedule = load_schedule_file(schedule_path)
    context = load_character_context(character_path)

    # 查找SR事件
    sr_events = find_sr_events(schedule)

    if not sr_events:
        print("⚠️ 日程中没有找到SR事件!")
        return []

    # 确定输出文件路径
    if output_path is None:
        # 标准化输出路径: data/events/{character_id}_events_{date}.json
        character_id = context.actor_state.character_id
        date = schedule.get("date", "unknown_date")
        output_dir = Path(__file__).parent / "data" / "events"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{character_id}_events_{date}.json")
    else:
        # 用户指定的路径
        output_path = str(Path(output_path))
        # 确保输出目录存在
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # 加载配置
    print("[Debug] 正在加载配置...")
    config = load_config()
    print("[Debug] 配置已加载")

    # 为每个SR事件生成策划卡
    results = []
    planner = EventPlanner(config)

    for i, sr_event in enumerate(sr_events):
        print(f"\n{'='*60}")
        print(f"[Debug] 正在处理第 {i+1}/{len(sr_events)} 个SR事件")
        print(f"[Debug] 时间段: {sr_event.get('time_slot')}")
        print(f"[Debug] 事件名: {sr_event.get('event_name')}")

        # 使用SR事件的summary作为plot_summary
        plot_summary = sr_event.get("summary", sr_event.get("event_name", ""))
        print(f"[Debug] 剧情梗概: {plot_summary[:50]}...")

        # 生成策划卡
        print("[Debug] 正在生成SR策划卡...")
        card = planner.plan_sr_event(
            sr_plot_summary=plot_summary,
            context=context
        )
        print("[Debug] SR策划卡已生成")

        # 将时间区间信息添加到结果中
        card_data = card.to_dict()
        card_data["time_slot"] = sr_event.get("time_slot", "")
        card_data["event_name"] = sr_event.get("event_name", "")

        results.append(card_data)
        print(f"✅ SR事件 {i+1} 策划卡已生成")
        print(card.to_formatted_text())

    # 将所有SR事件保存到一个JSON文件
    print(f"\n[Debug] 正在保存 {len(results)} 个SR事件到: {output_path}")

    output_data = {
        "schedule_info": {
            "character": schedule.get("character"),
            "date": schedule.get("date"),
            "total_sr_events": len(sr_events)
        },
        "sr_events": results
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"✅ 所有SR事件已保存到: {output_path}")

    return results


# ==================== 原有函数 ====================

def create_sample_context() -> FullInputContext:
    """创建示例上下文"""
    print("[Debug] 正在创建示例上下文...")
    character = CharacterNarrativeDNA(
        name="Zooo",
        name_en="Zooo",
        gender="Male",
        species="Cat",
        mbti=MBTIType.ENFP,
        appearance="Orange tabby cat with green eyes, wears a small collar",
        personality=["curious", "lazy", "food-loving", "clumsy"],
        short_term_goal="Find the perfect napping spot",
        mid_term_goal="Become the neighborhood's favorite cat",
        long_term_goal="Achieve legendary status among all cats",
        residence="Cozy apartment",
        initial_energy=80,
        money=0,
        items=["small bell", "favorite toy mouse"],
        current_intent="Looking for snacks",
        profile_en="A curious orange cat who loves food and naps, but always gets into trouble.",
    )

    actor_state = ActorDynamicState(
        character_id="zooo_001",
        energy=80,
        mood="content",
        location="Living Room",
        recent_memories=[],
        long_term_memory="A happy house cat with many adventures"
    )

    user_profile = UserProfile(
        intimacy_points=100,
        intimacy_level="L3-Friend",
        gender="Unspecified",
        age_group="Adult",
        species="Human",
        preference="Balanced"
    )

    world_context = WorldContext(
        date="2024-01-15",
        time=TimeOfDay.AFTERNOON,
        weather=WeatherType.SUNNY,
        world_rules=["Animals can understand humans", "Magical events occur randomly"],
        locations={"kitchen": "A cozy kitchen with lots of treats"},
        public_events=[]
    )

    mutex_lock = MutexLock(locked_characters=[])

    print(f"[Debug] 示例上下文已创建: 角色={character.name}, 地点={actor_state.location}")
    return FullInputContext(
        character_dna=character,
        actor_state=actor_state,
        user_profile=user_profile,
        world_context=world_context,
        mutex_lock=mutex_lock
    )


def generate_sr_event(
    plot_summary: str,
    output_path: str = "sr_event_output.json",
    context: FullInputContext = None
) -> dict:
    """
    生成SR事件策划卡

    Args:
        plot_summary: SR剧情梗概
        output_path: 输出文件路径
        context: 完整上下文（可选，默认使用示例）

    Returns:
        dict: SR事件策划卡数据
    """
    print("[Debug] generate_sr_event() 被调用")
    print(f"[Debug] 剧情梗概: {plot_summary[:50]}..." if len(plot_summary) > 50 else f"[Debug] 剧情梗概: {plot_summary}")
    print(f"[Debug] 输出路径: {output_path}")
    print(f"[Debug] 是否提供上下文: {context is not None}")

    # 加载配置 (自动从 config.ini 读取)
    print("[Debug] 正在加载配置...")
    config = load_config()
    print("[Debug] 配置已加载")

    # 创建上下文
    if context is None:
        print("[Debug] 未提供上下文，正在创建示例上下文...")
        context = create_sample_context()
    else:
        print(f"[Debug] 使用提供的上下文: 角色={context.character_dna.name}")

    # 生成策划卡
    print("[Debug] 正在创建EventPlanner并规划事件...")
    planner = EventPlanner(config)
    card = planner.plan_sr_event(
        sr_plot_summary=plot_summary,
        context=context
    )
    print("[Debug] SR事件策划卡已生成")

    # 保存结果
    print(f"[Debug] 正在保存结果到 {output_path}...")
    result = card.to_dict()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("[Debug] 结果已保存")

    print(f"\n✅ SR事件策划卡已保存到: {output_path}")
    print("\n" + "=" * 60)
    print(card.to_formatted_text())

    return result


def interactive_mode():
    """交互模式"""
    print("[Debug] 正在启动交互模式...")
    print("=" * 60)
    print("🎬 SR事件策划器 - 交互模式")
    print("=" * 60)

    # 角色信息输入
    print("\n[角色信息]")
    name = input("姓名 (默认: Zooo): ").strip() or "Zooo"
    species = input("种族 (默认: Cat): ").strip() or "Cat"
    appearance = input("外观: ").strip() or "Orange tabby cat"

    personality_input = input("性格 (逗号分隔, 默认: curious,lazy): ").strip()
    if personality_input:
        personality = [p.strip() for p in personality_input.split(",")]
    else:
        personality = ["curious", "lazy"]

    # 剧情梗概
    print("\n[剧情梗概]")
    plot_summary = input("请输入SR剧情梗概: ").strip()

    print(f"[Debug] 用户输入 - 姓名: {name}, 种族: {species}, 剧情梗概: {plot_summary[:30]}...")

    if not plot_summary:
        print("❌ 剧情梗概不能为空!")
        sys.exit(1)

    # 创建上下文
    print("[Debug] 正在根据用户输入构建FullInputContext...")
    character = CharacterNarrativeDNA(
        name=name,
        name_en=name,
        gender="Unspecified",
        species=species,
        mbti=MBTIType.ENFP,
        appearance=appearance,
        personality=personality,
        short_term_goal="Live happily",
        mid_term_goal="Make friends",
        long_term_goal="Find purpose",
        residence="Unknown",
        initial_energy=70,
        profile_en=f"A {species.lower()} named {name}."
    )

    actor_state = ActorDynamicState(
        character_id=f"{name.lower()}_001",
        energy=70,
        mood="neutral",
        location="Unknown",
        recent_memories=[],
        long_term_memory=""
    )

    user_profile = UserProfile(
        intimacy_points=50,
        intimacy_level="L2-Acquaintance"
    )

    world_context = WorldContext(
        date="2024-01-15",
        time=TimeOfDay.NOON,
        weather=WeatherType.SUNNY
    )

    mutex_lock = MutexLock(locked_characters=[])

    context = FullInputContext(
        character_dna=character,
        actor_state=actor_state,
        user_profile=user_profile,
        world_context=world_context,
        mutex_lock=mutex_lock
    )

    print(f"[Debug] FullInputContext 构建成功")

    # 生成
    output_path = input("\n输出文件 (默认: sr_event_output.json): ").strip() or "sr_event_output.json"
    print(f"[Debug] 正在调用 generate_sr_event，输出路径={output_path}")

    generate_sr_event(
        plot_summary=plot_summary,
        output_path=output_path,
        context=context
    )


def main():
    print("[Debug] SR事件生成器启动...")
    parser = argparse.ArgumentParser(
        description="SR事件策划卡生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 使用示例上下文快速开始
  python sr_event.py --plot "小猫发现了一个神秘盒子"

  # 自定义输出文件
  python sr_event.py --plot "剧情梗概" --output my_event.json

  # 交互模式
  python sr_event.py --interactive

  # 从日程和人物文件生成SR卡
  python sr_event.py --schedule data/schedule/4.json --character data/characters/judy_001_context.json

  # 从日程和人物文件生成SR卡，并指定输出文件路径
  python sr_event.py --schedule data/schedule/4.json --character data/characters/judy_001_context.json --output data/events/my_event.json
注意: 配置会自动从 config.ini 加载
        """
    )

    parser.add_argument(
        "--plot", "-p",
        type=str,
        help="SR剧情梗概"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="输出JSON文件路径 (默认: data/events/{character_id}_events_{date}.json when using --schedule)"
    )

    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="交互模式"
    )

    parser.add_argument(
        "--schedule", "-s",
        type=str,
        help="日程JSON文件路径"
    )

    parser.add_argument(
        "--character", "-c",
        type=str,
        help="人物上下文JSON文件路径"
    )

    args = parser.parse_args()
    print(f"[Debug] 解析参数: plot={args.plot}, output={args.output}, interactive={args.interactive}, schedule={args.schedule}, character={args.character}")

    # 日程模式：需要同时提供 schedule 和 character 参数
    if args.schedule or args.character:
        if not args.schedule or not args.character:
            print("❌ 日程模式需要同时提供 --schedule 和 --character!")
            print("   示例: python sr_event.py --schedule data/schedule/4.json --character data/characters/judy_001_context.json")
            sys.exit(1)
        print("[Debug] 正在启动日程模式...")
        generate_sr_from_schedule(
            schedule_path=args.schedule,
            character_path=args.character,
            output_path=args.output
        )
    elif args.interactive:
        print("[Debug] 正在启动交互模式...")
        interactive_mode()
    elif args.plot:
        print("[Debug] 正在启动剧情模式...")
        generate_sr_event(
            plot_summary=args.plot,
            output_path=args.output
        )
    else:
        parser.print_help()
        print("\n❌ 请提供 --plot、--interactive 或 (--schedule + --character)")

    print("[Debug] SR事件生成器结束")


if __name__ == "__main__":
    main()
