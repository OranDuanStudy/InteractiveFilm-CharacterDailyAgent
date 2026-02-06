#!/usr/bin/env python3
"""
Interactive Film Character Daily Agent - 主流程脚本

串联完整的工作流程：
1. 角色创建/加载
2. 日程规划 (Schedule)
3. SR事件创立 (SR Event)
4. 导演模式 (Director)

用法:
    python main.py run <character_id> [--template judy|leona] [--force]
    python main.py run <character_id> --use-existing
    python main.py run <character_id> --schedule-only
    python main.py run <character_id> --sr-only
    python main.py run <character_id> --director-only
"""
import argparse
import json
import sys
from tqdm import tqdm
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import (
    ScheduleAgent,
    ScheduleOutputFormatter,
    EventPlanner,
    DirectorAgent,
    FullInputContext,
    CharacterContextManager,
    load_config,
)
from src.core.agent import ScheduleOutput
from src.storage import Config


# ==================== 模板映射 ====================
# 所有可用的角色模板ID
# 注意：这些ID必须与 assets/templates/*.json 文件中的 template_id 字段匹配
AVAILABLE_TEMPLATES = [
    "leona",      # 1 - 出道练习生 Leona
    "rick",       # 2 - 神秘教父 Rick
    "auntie",     # 3 - 便利店老板 Auntie Baa Baa
    "glo",        # 4 - 时尚情感博主 GLO
    "link",       # 5 - 嘴臭锐评网红 Link
    "poto",       # 6 - 抽象薯饼人 Poto
    "rank",       # 7 - 暴躁汽修老哥 Rank
    "tos",        # 8 - 吐司打工人 Tos
    "mac",        # 9 - 游戏高手 Mac
    "wolly",      # 10 - 悲伤醉酒蛙 Wolly
    "ham",        # 11 - 汉堡大王 Ham
    "chip",       # 12 - 零食小宝 Chip
    "blink",      # 13 - 弹唱星星 Blink
]


# ==================== 阶段1: 角色创建/加载 ====================

def ensure_character(
    character_id: str,
    template: str = None,
    force: bool = False,
    use_existing: bool = False
) -> FullInputContext:
    """
    确保角色存在，如果不存在则从模板创建

    Args:
        character_id: 角色ID
        template: 模板ID (leona/rick/glo/link等)
        force: 强制覆盖已存在的角色
        use_existing: 仅使用已存在的角色

    Returns:
        FullInputContext: 角色上下文
    """
    context_manager = CharacterContextManager()

    # 如果 use-existing，角色必须已存在
    if use_existing:
        if not context_manager.exists(character_id):
            print(f"✗ Character '{character_id}' does not exist!")
            print(f"   Use --template <template_id> to create from template")
            print(f"   Available templates: {', '.join(AVAILABLE_TEMPLATES)}")
            sys.exit(1)
        print(f"✓ Using existing character: {character_id}")
        return context_manager.load(character_id)

    # 检查角色是否已存在
    if context_manager.exists(character_id) and not force:
        print(f"✓ Character '{character_id}' already exists, loading...")
        return context_manager.load(character_id)

    # 创建新角色
    if template:
        if template not in AVAILABLE_TEMPLATES:
            print(f"✗ Unknown template: {template}")
            print(f"   Available templates: {', '.join(AVAILABLE_TEMPLATES)}")
            sys.exit(1)

        context = context_manager.create_from_template(character_id, template)
        print(f"✓ Created from template: {template}")
    else:
        # 使用默认模板
        context = context_manager._create_default_context(character_id)
        print(f"✓ Created from default template")

    # 不再保存context，属性变化将输出到schedule/events中
    print(f"✓ Character '{character_id}' ready (context not saved)")

    print(f"  Name: {context.character_dna.name} ({context.character_dna.name_en})")
    print(f"  Energy: {context.actor_state.energy}/100")
    print(f"  Mood: {context.actor_state.mood}")

    return context


# ==================== 阶段2: 日程规划 ====================

def run_schedule_generation(
    character_id: str,
    context: FullInputContext,
    output_path: str = None,
    streaming: bool = True
) -> str:
    """
    生成日程规划

    Args:
        character_id: 角色ID
        context: 角色上下文
        output_path: 输出文件路径
        streaming: 是否使用多轮对话模式

    Returns:
        str: 生成的日程文件路径
    """
    print(f"\n{'='*60}")
    print(f"STAGE 2: Schedule Generation")
    print(f"{'='*60}")

    agent = ScheduleAgent()
    config = load_config()

    print(f"Model: {config.model}")
    print(f"Mode: {'Multi-turn (streaming)' if streaming else 'Single-shot'}")
    print(f"Date: {context.world_context.date}")
    print(f"Weather: {context.world_context.weather.value}")
    print(f"Intimacy Level: {context.user_profile.intimacy_level}")
    print()

    # 选择生成模式
    if streaming:
        print(f"Generating schedule with multi-turn conversation...")
        output = agent.generate_streaming(context)
    else:
        print(f"Generating schedule in single-shot mode...")
        output = agent.generate(context)

    # 确定输出路径
    if output_path is None:
        output_dir = Path(__file__).parent / "data" / "schedule"
        output_dir.mkdir(parents=True, exist_ok=True)
        date = context.world_context.date
        output_path = str(output_dir / f"{character_id}_schedule_{date}.json")

    # 格式化为JSON
    formatter = ScheduleOutputFormatter()
    result = formatter.format_json(output, context)

    # 保存
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"✓ Schedule saved to: {output_path}")
    print(f"✓ Attribute changes included in schedule JSON (not applied to context)")

    return output_path


# ==================== 阶段3: SR/R事件创立 ====================

def run_sr_event_generation(
    schedule_path: str,
    character_path: str,
    output_path: str = None
) -> str:
    """
    从日程生成SR和R事件

    Args:
        schedule_path: 日程文件路径
        character_path: 角色上下文文件路径
        output_path: 输出文件路径

    Returns:
        str: 生成的SR/R事件文件路径
    """
    print(f"\n{'='*60}")
    print(f"STAGE 3: SR/R Event Generation")
    print(f"{'='*60}")

    # 加载日程文件
    print(f"Loading schedule: {schedule_path}")
    with open(schedule_path, 'r', encoding='utf-8') as f:
        schedule = json.load(f)

    # 查找R和SR事件（需要生成prompts的事件）
    r_events = [e for e in schedule.get("events", []) if e.get("event_type") == "R"]
    sr_events = [e for e in schedule.get("events", []) if e.get("event_type") == "SR"]

    if not r_events and not sr_events:
        print("⚠️ No R/SR events found in schedule!")
        return None

    print(f"Found {len(r_events)} R event(s), {len(sr_events)} SR event(s)")

    # 加载角色上下文
    print(f"Loading character context: {character_path}")
    with open(character_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    context = FullInputContext.from_dict(data)

    # 确定输出路径
    if output_path is None:
        character_id = context.actor_state.character_id
        date = schedule.get("date", "unknown_date")
        output_dir = Path(__file__).parent / "data" / "events"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{character_id}_events_{date}.json")

    # 生成SR/R事件
    config = load_config()
    planner = EventPlanner(config)

    results = []

    # 先处理R事件（使用简化策划）
    for i, event in enumerate(r_events):
        print(f"\n--- R Event {i+1}/{len(r_events)} ---")
        print(f"Time Slot: {event.get('time_slot')}")
        print(f"Event Name: {event.get('event_name')}")

        plot_summary = event.get("summary", event.get("event_name", ""))

        # 使用统一的planner，指定event_type="R"
        card = planner.plan_event(
            plot_summary=plot_summary,
            context=context,
            event_type="R",
            time_slot=event.get("time_slot", "")
        )

        # 转换为字典格式
        card_data = card.to_dict()
        card_data["time_slot"] = event.get("time_slot", "")
        card_data["event_name"] = event.get("event_name", "")
        card_data["event_type"] = "R"
        results.append(card_data)

        print(f"✓ Generated R event card")

    # 再处理SR事件（使用完整策划）
    for i, event in enumerate(sr_events):
        print(f"\n--- SR Event {i+1}/{len(sr_events)} ---")
        print(f"Time Slot: {event.get('time_slot')}")
        print(f"Event Name: {event.get('event_name')}")

        plot_summary = event.get("summary", event.get("event_name", ""))

        # 使用统一的planner，指定event_type="SR"
        card = planner.plan_event(
            plot_summary=plot_summary,
            context=context,
            event_type="SR",
            time_slot=event.get("time_slot", "")
        )

        # 转换为字典格式
        card_data = card.to_dict()
        card_data["time_slot"] = event.get("time_slot", "")
        card_data["event_name"] = event.get("event_name", "")
        card_data["event_type"] = "SR"
        results.append(card_data)

        print(f"✓ Generated SR event card")

    # 保存结果
    output_data = {
        "schedule_info": {
            "character": schedule.get("character"),
            "date": schedule.get("date"),
            "total_r_events": len(r_events),
            "total_sr_events": len(sr_events),
        },
        "events": results
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    print(f"\n✓ SR/R events saved to: {output_path}")

    return output_path


# ==================== 阶段4: 导演模式 ====================

def run_director_generation(
    sr_events_path: str,
    character_path: str,
    output_path: str = None
) -> str:
    """
    为SR/R事件生成导演输出

    Args:
        sr_events_path: SR/R事件文件路径
        character_path: 角色上下文文件路径
        output_path: 输出文件路径

    Returns:
        str: 生成的导演输出文件路径
    """
    print(f"\n{'='*60}")
    print(f"STAGE 4: Director Generation")
    print(f"{'='*60}")

    # 检查是否有 SR/R 事件
    if sr_events_path is None:
        print("⚠️ No SR/R events to process, skipping director generation.")
        return None

    # 加载SR/R事件
    print(f"Loading SR/R events: {sr_events_path}")
    with open(sr_events_path, 'r', encoding='utf-8') as f:
        sr_data = json.load(f)

    events = sr_data.get("events", [])
    if not events:
        print("⚠️ No SR/R events found!")
        return None

    # 统计R和SR事件数量
    r_count = sum(1 for e in events if e.get("event_type") == "R")
    sr_count = sum(1 for e in events if e.get("event_type") == "SR")
    print(f"Processing {r_count} R event(s), {sr_count} SR event(s)")

    # 加载角色上下文
    print(f"Loading character context: {character_path}")
    with open(character_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    context = FullInputContext.from_dict(data)

    # 确定输出路径
    if output_path is None:
        character_id = context.actor_state.character_id
        date = sr_data.get("schedule_info", {}).get("date", "unknown_date")
        output_dir = Path(__file__).parent / "data" / "director"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{character_id}_director_{date}.json")

    # 生成导演输出
    config = load_config()
    director = DirectorAgent(config)

    # 添加event_index到events（用于生成event_id）
    r_event_count = 0
    sr_event_count = 0
    for event in events:
        if event.get("event_type") == "R":
            r_event_count += 1
            event["event_index"] = r_event_count
        elif event.get("event_type") == "SR":
            sr_event_count += 1
            event["event_index"] = sr_event_count

    results = []
    for i, event in enumerate(events):
        event_type = event.get("event_type", "SR")
        print(f"\n--- {event_type} Event {i+1}/{len(events)} ---")
        print(f"Time Slot: {event.get('time_slot')}")
        print(f"Event Name: {event.get('event_name')}")

        output = director.elaborate_sr_event(event, context)
        output_dict = output.to_dict()
        # event_type已经在DirectorAgent中设置，这里不再覆盖
        results.append(output_dict)

        print(f"✓ Generated {len(output.scenes)} scene(s)")

    # 保存结果
    schedule_info = sr_data.get("schedule_info", {})
    final_output = {
        "schedule_info": schedule_info,
        "director_outputs": results,
    }

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(final_output, f, indent=2, ensure_ascii=False)

    print(f"\n✓ Director output saved to: {output_path}")

    return output_path


# ==================== 主流程 ====================

def run_full_pipeline(
    character_id: str,
    template: str = None,
    force: bool = False,
    use_existing: bool = False,
    schedule_only: bool = False,
    sr_only: bool = False,
    director_only: bool = False,
    streaming: bool = True
):
    """
    运行完整流程

    Args:
        character_id: 角色ID
        template: 角色模板 (judy/leona)
        force: 强制覆盖已存在的角色
        use_existing: 仅使用已存在的角色
        schedule_only: 只运行日程规划
        sr_only: 只运行SR事件生成
        director_only: 只运行导演生成
        streaming: 使用多轮对话模式
    """
    print(f"\n{'='*60}")
    print(f"Interactive Film Character Daily Agent - Full Pipeline")
    print(f"{'='*60}")
    print(f"Character ID: {character_id}")

    # 路径定义
    context_manager = CharacterContextManager()
    context_path = context_manager._get_context_path(character_id)
    data_dir = Path(__file__).parent / "data"

    # 如果是 --director-only，需要先检查中间文件是否存在
    if director_only:
        schedule_path = data_dir / "schedule" / f"{character_id}_schedule_*.json"
        sr_events_path = data_dir / "events" / f"{character_id}_events_*.json"

        # 查找实际文件
        import glob
        schedule_files = glob.glob(str(schedule_path))
        sr_files = glob.glob(str(sr_events_path))

        if not schedule_files:
            print(f"✗ Schedule file not found for '{character_id}'")
            print(f"   Run without --director-only first")
            sys.exit(1)
        if not sr_files:
            print(f"✗ SR events file not found for '{character_id}'")
            print(f"   Run without --director-only first")
            sys.exit(1)

        schedule_path = schedule_files[-1]  # 使用最新的
        sr_events_path = sr_files[-1]

        print(f"Using existing schedule: {schedule_path}")
        print(f"Using existing SR events: {sr_events_path}")

        run_director_generation(sr_events_path, context_path)
        return

    # 阶段1: 角色创建/加载
    context = ensure_character(character_id, template, force, use_existing)

    # 阶段2: 日程规划
    if sr_only:
        # 只运行SR生成，需要已有日程文件
        schedule_path = data_dir / "schedule" / f"{character_id}_schedule_*.json"
        import glob
        schedule_files = glob.glob(str(schedule_path))
        if not schedule_files:
            print(f"✗ Schedule file not found for '{character_id}'")
            print(f"   Run without --sr-only first")
            sys.exit(1)
        schedule_path = schedule_files[-1]
        print(f"Using existing schedule: {schedule_path}")
    else:
        schedule_path = run_schedule_generation(character_id, context, streaming=streaming)

    if schedule_only:
        print(f"\n✓ Pipeline stopped after schedule generation")
        return

    # 阶段3: SR事件创立
    sr_events_path = run_sr_event_generation(schedule_path, context_path)

    if sr_only:
        print(f"\n✓ Pipeline stopped after SR event generation")
        return

    # 阶段4: 导演模式
    run_director_generation(sr_events_path, context_path)

    print(f"\n{'='*60}")
    print(f"✓ Full Pipeline Complete!")
    print(f"{'='*60}")
    print(f"Generated files:")
    print(f"  - Schedule: {schedule_path}")
    print(f"  - SR Events: {sr_events_path}")
    print(f"  - Director Output: {data_dir}/director/{character_id}_director_*.json")


# ==================== 命令行接口 ====================

def main():
    parser = argparse.ArgumentParser(
        description="Interactive Film Character Daily Agent - 完整工作流程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
工作流程 Workflow:
  完整流程: 角色创建/加载 → 日程规划 → SR事件创立 → 导演模式

示例 Examples:
  # 完整流程（使用模板创建新角色）
  python main.py run leona_001 --template leona
  python main.py run rick_001 --template rick

  # 完整流程（使用已存在的角色）
  python main.py run leona_001 --use-existing

  # 只生成日程
  python main.py run leona_001 --use-existing --schedule-only

  # 只生成SR事件（需要已有日程）
  python main.py run leona_001 --sr-only

  # 只生成导演输出（需要已有日程和SR事件）
  python main.py run leona_001 --director-only

  # 使用单次生成模式（而非多轮对话）
  python main.py run leona_001 --template leona --no-streaming

可用模板 Available Templates:
  leona          - 莱昂娜（街舞女孩，ENFJ，成长/音乐类型）
  rick           - Rick（神秘教父，ENTJ，冷峻/毒舌）
  auntie         - Auntie Baa Baa（便利店老板，ESFJ，智慧/冷静）
  glo            - GLO（时尚博主，ESFP，戏剧/情感）
  link           - Link（锐评网红，ENFP，混乱/能量）
  poto           - Poto（薯饼人，ISFP，抽象/进化）
  rank           - Rank（汽修老哥，ISTP，暴躁/技术）
  tos            - Tos（吐司打工人，ISTJ，死板/幽默）
  mac            - Mac（游戏高手，ESTP，游戏/速通）
  wolly          - Wolly（醉酒蛙，INFP，悲伤/哲学）
  ham            - Ham（汉堡大王，ENTJ，自恋/喜剧）
  chip           - Chip（零食小宝，ISFP，温柔/分享）
  blink          - Blink（弹唱星星，INFP，治愈/笨拙）

输出文件 Output Files:
  data/characters/{character_id}_context.json      # 角色上下文
  data/schedule/{character_id}_schedule_{date}.json # 日程规划
  data/events/{character_id}_events_{date}.json    # SR事件
  data/director/{character_id}_director_{date}.json # 导演输出
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # run 命令
    parser_run = subparsers.add_parser("run", help="运行完整流程或指定阶段")
    parser_run.add_argument("character_id", help="角色ID（如 leona_001, rick_001）")
    parser_run.add_argument("--template", "-t", choices=AVAILABLE_TEMPLATES, help=f"使用角色模板创建")
    parser_run.add_argument("--force", "-f", action="store_true", help="强制覆盖已存在的角色")
    parser_run.add_argument("--use-existing", "-e", action="store_true", help="仅使用已存在的角色")
    parser_run.add_argument("--schedule-only", action="store_true", help="只运行日程规划阶段")
    parser_run.add_argument("--sr-only", action="store_true", help="只运行SR事件生成阶段")
    parser_run.add_argument("--director-only", action="store_true", help="只运行导演生成阶段")
    parser_run.add_argument("--no-streaming", action="store_true", help="使用单次生成模式（默认为多轮对话模式）")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "run":
        run_full_pipeline(
            character_id=args.character_id,
            template=args.template,
            force=args.force,
            use_existing=args.use_existing,
            schedule_only=args.schedule_only,
            sr_only=args.sr_only,
            director_only=args.director_only,
            streaming=not args.no_streaming
        )


if __name__ == "__main__":
    main()
