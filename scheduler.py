#!/usr/bin/env python3
"""
Interactive Film Character Daily Agent - 角色日程规划系统

基于角色编导体系的完整实现
使用 z.ai 的 GLM-4.7 模型生成角色日程规划（五列表格格式）

用法:
    python scheduler.py create <character_id> [--template judy|luna|default] [--force]
    python scheduler.py generate <character_id> [options]
    python scheduler.py characters
"""
import argparse
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import (
    ScheduleAgent,
    ScheduleOutputFormatter,
    PromptExporter,
    load_config,
    show_config,
    get_luna_example_schedule,
    FullInputContext,
    CharacterContextManager,
)


def cmd_generate(args):
    """生成日程规划（角色必须存在）"""
    context_manager = CharacterContextManager()
    character_id = args.character_id

    # 检查角色是否存在
    if not context_manager.exists(character_id):
        print(f"✗ Character '{character_id}' does not exist!")
        print()
        print("Create the character first using main.py:")
        print(f"  python main.py run {character_id} --template <template_id>")
        print()
        print("Available characters:")
        characters = context_manager.list_characters()
        if characters:
            for c in characters:
                print(f"  - {c}")
        else:
            print("  (none)")
        sys.exit(1)

    # 加载角色上下文
    print(f"Loading context for: {character_id}")
    context = context_manager.load(character_id)
    print(f"  Character: {context.character_dna.name} ({context.character_dna.name_en})")
    print(f"  Energy: {context.actor_state.energy}/100")
    print(f"  Mood: {context.actor_state.mood}")
    print()

    # 创建Agent
    print(f"Initializing Schedule Agent...")
    agent = ScheduleAgent()

    # 生成日程
    print(f"Generating daily schedule for {context.world_context.date}...")
    print(f"Weather: {context.world_context.weather.value}")
    print(f"Intimacy Level: {context.user_profile.intimacy_level}")
    print()

    # 选择生成模式
    if args.streaming:
        print(f"Mode: Multi-turn conversation (streaming)")
        print(f"  - Generating 12 time slots sequentially")
        print(f"  - Maintaining conversation history for consistency")
        print()
        print(f"Calling {agent.config.model} API...")
        print()
        generate_func = agent.generate_streaming
    else:
        print(f"Mode: Single-shot generation")
        print(f"  - Generating all 12 time slots at once")
        print()
        print(f"Calling {agent.config.model} API...")
        print()
        generate_func = agent.generate

    try:
        output = generate_func(context)

        # 格式化输出
        formatter = ScheduleOutputFormatter()

        if args.format == "markdown":
            result = formatter.format_markdown(output, context)
        elif args.format == "detailed":
            result = formatter.format_detailed(output, context)
        elif args.format == "json":
            result = formatter.format_json(output, context)
        else:
            result = formatter.format_markdown(output, context)

        # 输出结果
        print(result)

        # 保存到文件
        output_path = args.output
        if output_path is None:
            # 标准化输出路径: data/schedule/{character_id}_schedule_{date}.{ext}
            date = context.world_context.date
            ext = "json" if args.format == "json" else "md"
            output_dir = Path(__file__).parent / "data" / "schedule"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = str(output_dir / f"{character_id}_schedule_{date}.{ext}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
        print()
        print(f"✓ Output saved to: {output_path}")

        # 导出Prompts
        if args.export_prompts:
            PromptExporter.export_prompts(output, args.export_prompts)
            print(f"✓ Prompts exported to: {args.export_prompts}")

        # 属性变化已包含在JSON输出中（不更新context）
        print()
        print(f"✓ Attribute changes included in schedule JSON (not applied to context)")

    except Exception as e:
        print(f"✗ Error: {e}")
        print()
        print("Please check:")
        print("1. Your API key is correctly set in config.ini or .env")
        print("2. You have network access to open.bigmodel.cn")
        print("3. Your API account has sufficient quota")
        sys.exit(1)


def cmd_characters(args):
    """列出所有角色或显示角色详情"""
    context_manager = CharacterContextManager()
    characters = context_manager.list_characters()

    if not characters:
        print("No characters found. Create one by running:")
        print("  python scheduler.py create <character_id> [--template judy|luna]")
        return

    if args.info:
        # 显示特定角色的详细信息
        character_id = args.info
        if character_id not in characters:
            print(f"✗ Character '{character_id}' not found.")
            print(f"Available characters: {', '.join(characters)}")
            return

        context = context_manager.load(character_id)
        print(f"=== Character Details: {character_id} ===")
        print()
        print(f"Name: {context.character_dna.name} ({context.character_dna.name_en})")
        print(f"Species: {context.character_dna.species}")
        print(f"MBTI: {context.character_dna.mbti.value}")
        print()
        print("--- Current State ---")
        print(f"Energy: {context.actor_state.energy}/100")
        print(f"Mood: {context.actor_state.mood}")
        print(f"Location: {context.actor_state.location}")
        print(f"Recent Memories: {len(context.actor_state.recent_memories)} entries")
        print()
        print("--- User Profile ---")
        print(f"Intimacy Points: {context.user_profile.intimacy_points}")
        print(f"Intimacy Level: {context.user_profile.intimacy_level}")
        print()
        print(f"Context file: {context_manager._get_context_path(character_id)}")
    else:
        # 列出所有角色
        print("Available characters:")
        print()
        for character_id in characters:
            context = context_manager.load(character_id)
            print(f"  - {character_id}: {context.character_dna.name} ({context.character_dna.name_en})")
        print()
        print(f"Total: {len(characters)} character(s)")
        print()
        print("Use --info <character_id> to view details")


def cmd_config(args):
    """配置管理"""
    if args.show:
        show_config()


def cmd_example(args):
    """输出示例日程（莱昂娜案例，不调用语言模型）"""
    print("Loading Luna example schedule from PDF case...")
    print("(No API call - using pre-built example data)")
    print()

    # 获取示例数据
    output = get_luna_example_schedule()
    context = create_luna_context()

    # 格式化输出
    formatter = ScheduleOutputFormatter()

    if args.format == "markdown":
        result = formatter.format_markdown(output, context)
    elif args.format == "detailed":
        result = formatter.format_detailed(output, context)
    elif args.format == "json":
        result = formatter.format_json(output, context)
    else:
        result = formatter.format_markdown(output, context)

    # 输出结果
    print(result)
    print()

    # 保存到文件
    output_path = args.output
    if output_path is None:
        # 标准化输出路径: data/schedule/{character_id}_schedule_{date}.{ext}
        character_id = context.actor_state.character_id
        date = context.world_context.date
        ext = "json" if args.format == "json" else "md"
        output_dir = Path(__file__).parent / "data" / "schedule"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{character_id}_schedule_{date}.{ext}")

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)
    print(f"✓ Output saved to: {output_path}")

    # 导出Prompts
    if args.export_prompts:
        PromptExporter.export_prompts(output, args.export_prompts)
        print(f"✓ Prompts exported to: {args.export_prompts}")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive Film Character Daily Agent - 角色日程规划系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
工作流程 Workflow:
  1. 创建角色:     python main.py run <character_id> --template <template_id>
  2. 生成日程:     python scheduler.py generate <character_id> [options]
  3. 查看角色:     python scheduler.py characters [--info <character_id>]

示例 Examples:
  # 创建角色（使用main.py）
  python main.py run luna_001 --template luna
  python main.py run alex_001 --template alex

  # 生成日程
  python scheduler.py generate luna_001
  python scheduler.py generate alex_001 --format detailed --output schedule.md

  # 查看所有角色
  python scheduler.py characters

  # 查看角色详情
  python scheduler.py characters --info luna_001

可用角色模板 Available Templates:
  luna, alex, maya, daniel

API Key Configuration:
  配置文件 config.ini (优先级最高):
    [api]
    api_key = your_api_key_here

  环境变量:
    export ZAI_API_KEY=your_key

  .env 文件:
    ZAI_API_KEY=your_key
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # generate 命令
    parser_generate = subparsers.add_parser("generate", help="生成日程规划（角色必须存在）")
    parser_generate.add_argument("character_id", help="角色ID")
    parser_generate.add_argument("--format", choices=["markdown", "detailed", "json"], default="markdown", help="输出格式")
    parser_generate.add_argument("--output", "-o", help="输出文件路径 (默认: data/schedule/{character_id}_schedule_{date}.{ext})")
    parser_generate.add_argument("--export-prompts", help="导出所有Prompt到文件")
    parser_generate.add_argument("--streaming", "-s", action="store_true", help="使用多轮对话模式（逐时间段生成，保持上下文连贯）")

    # characters 命令
    parser_characters = subparsers.add_parser("characters", help="列出所有角色")
    parser_characters.add_argument("--info", "-i", help="显示指定角色的详细信息", metavar="CHARACTER_ID")

    # config 命令
    parser_config = subparsers.add_parser("config", help="配置管理")
    parser_config.add_argument("--show", action="store_true", help="显示当前配置")

    # example 命令
    parser_example = subparsers.add_parser("example", help="输出莱昂娜示例日程（不调用API）")
    parser_example.add_argument("--format", choices=["markdown", "detailed", "json"], default="markdown", help="输出格式")
    parser_example.add_argument("--output", "-o", help="输出文件路径 (默认: data/schedule/{character_id}_schedule_{date}.{ext})")
    parser_example.add_argument("--export-prompts", help="导出所有Prompt到文件")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # 执行命令
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "characters":
        cmd_characters(args)
    elif args.command == "config":
        cmd_config(args)
    elif args.command == "example":
        cmd_example(args)


if __name__ == "__main__":
    main()
