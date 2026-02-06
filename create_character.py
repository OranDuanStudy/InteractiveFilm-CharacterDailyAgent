#!/usr/bin/env python3
"""
角色档案创建脚本

用法:
    # 从模板创建角色

    # 列出所有可用模板
    python create_character.py --list-templates

    # 查看已创建的角色
    python create_character.py --list-characters

    # 查看角色详情
    python create_character.py --show leona_001
    
    # 创建角色
    python create_character.py leon_001 --template leona
"""
import argparse
import json
import sys
from pathlib import Path

# 添加src到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.storage.context_manager import CharacterContextManager
from src.storage.template_loader import TemplateLoader


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


def list_templates():
    """列出所有可用模板"""
    print("="*60)
    print("可用角色模板 Available Character Templates")
    print("="*60)

    loader = TemplateLoader("assets/templates")
    template_ids = loader.list_available_templates()

    # 模板信息映射
    template_info = {
        "leona": ("莱昂娜", "出道练习生，街舞女孩，ENFJ"),
        "rick": ("Rick", "神秘教父，ENTJ，冷峻/毒舌"),
        "auntie": ("Auntie Baa Baa", "便利店老板，ESFJ，智慧/冷静"),
        "glo": ("GLO", "时尚博主，ESFP，戏剧/情感"),
        "link": ("Link", "锐评网红，ENFP，混乱/能量"),
        "poto": ("Poto", "薯饼人，ISFP，抽象/进化"),
        "rank": ("Rank", "汽修老哥，ISTP，暴躁/技术"),
        "tos": ("Tos", "吐司打工人，ISTJ，死板/幽默"),
        "mac": ("Mac", "游戏高手，ESTP，游戏/速通"),
        "wolly": ("Wolly", "醉酒蛙，INFP，悲伤/哲学"),
        "ham": ("Ham", "汉堡大王，ENTJ，自恋/喜剧"),
        "chip": ("Chip", "零食小宝，ISFP，温柔/分享"),
        "blink": ("Blink", "弹唱星星，INFP，治愈/笨拙"),
    }

    for template_id in template_ids:
        if template_id in template_info:
            name_cn, desc = template_info[template_id]
            print(f"  {template_id:12} - {name_cn:20} ({desc})")
        else:
            print(f"  {template_id:12} - 未知模板")

    print()
    print(f"共 {len(template_ids)} 个模板可用")
    print("使用方法: python create_character.py <character_id> --template <template_id>")


def list_characters():
    """列出所有已创建的角色"""
    manager = CharacterContextManager()
    characters = manager.list_characters()

    if not characters:
        print("尚未创建任何角色档案。")
        print("使用方法: python create_character.py <character_id> --template <template_id>")
        return

    print("="*60)
    print(f"已创建的角色 Created Characters ({len(characters)})")
    print("="*60)

    for character_id in characters:
        # 读取角色信息
        context = manager.load(character_id)
        print(f"  {character_id:20} - {context.character_dna.name} ({context.character_dna.name_en})")
        print(f"    MBTI: {context.character_dna.mbti.value}, Energy: {context.actor_state.energy}/100")


def show_character(character_id: str):
    """显示角色详细信息"""
    manager = CharacterContextManager()

    if not manager.exists(character_id):
        print(f"✗ 角色 '{character_id}' 不存在！")
        print(f"   使用 --list-characters 查看已创建的角色")
        return

    context = manager.load(character_id)

    print("="*60)
    print(f"角色档案 Character Profile: {character_id}")
    print("="*60)

    dna = context.character_dna
    print(f"\n【基本信息 Basic Info】")
    print(f"  姓名 Name: {dna.name} ({dna.name_en})")
    print(f"  种族 Species: {dna.species}")
    print(f"  性别 Gender: {dna.gender}")
    print(f"  年龄 Age: {dna.age}")
    print(f"  MBTI: {dna.mbti.value}")
    print(f"  阵营 Alignment: {dna.alignment.value}")

    print(f"\n【外观 Appearance】")
    print(f"  {dna.appearance}")

    print(f"\n【性格 Personality】")
    for trait in dna.personality:
        print(f"  • {trait}")

    print(f"\n【目标 Goals】")
    print(f"  短期 Short-term: {dna.short_term_goal}")
    print(f"  中期 Mid-term: {dna.mid_term_goal}")
    print(f"  长期 Long-term: {dna.long_term_goal}")

    if dna.skills:
        print(f"\n【技能 Skills】")
        for skill in dna.skills:
            print(f"  • {skill}")

    if dna.relationships:
        print(f"\n【关系 Relationships】")
        for name, relation in dna.relationships.items():
            print(f"  • {name}: {relation}")

    if dna.secret_levels:
        print(f"\n【秘密等级 Secret Levels】")
        for level, secrets in dna.secret_levels.items():
            print(f"  {level}:")
            for secret in secrets:
                print(f"    • {secret}")

    print(f"\n【当前状态 Current State】")
    print(f"  能量 Energy: {context.actor_state.energy}/100")
    print(f"  心情 Mood: {context.actor_state.mood}")
    print(f"  位置 Location: {context.actor_state.location}")

    print(f"\n【物品 Items】")
    if dna.items:
        for item in dna.items:
            print(f"  • {item}")
    else:
        print(f"  无")

    print(f"\n【金钱 Money】")
    print(f"  {dna.money}")

    print(f"\n【档案位置】")
    print(f"  {manager._get_context_path(character_id)}")


def create_character(character_id: str, template_id: str, force: bool = False):
    """创建角色档案"""
    manager = CharacterContextManager()

    # 检查是否已存在
    if manager.exists(character_id) and not force:
        print(f"✗ 角色 '{character_id}' 已存在！")
        print(f"   使用 --force 强制覆盖，或使用其他角色ID")
        print(f"   使用 --show {character_id} 查看角色详情")
        return False

    # 检查模板
    if template_id not in AVAILABLE_TEMPLATES:
        print(f"✗ 未知模板: {template_id}")
        print(f"   使用 --list-templates 查看可用模板")
        return False

    print(f"正在创建角色 '{character_id}' (模板: {template_id})...")

    # 从模板创建
    context = manager.create_from_template(character_id, template_id)

    # 保存角色
    manager.save(character_id, context)

    save_path = manager._get_context_path(character_id)
    print(f"✓ 角色创建成功！")
    print(f"  ID: {character_id}")
    print(f"  姓名: {context.character_dna.name} ({context.character_dna.name_en})")
    print(f"  MBTI: {context.character_dna.mbti.value}")
    print(f"  能量: {context.actor_state.energy}/100")
    print(f"  保存位置: {save_path}")

    return True


def main():
    parser = argparse.ArgumentParser(
        description="角色档案创建工具 Character Profile Creator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例 Examples:
  # 从模板创建角色
  python create_character.py leona_001 --template leona
  python create_character.py rick_001 --template rick

  # 强制覆盖已存在的角色
  python create_character.py leona_001 --template leona --force

  # 列出所有可用模板
  python create_character.py --list-templates

  # 列出所有已创建的角色
  python create_character.py --list-characters

  # 查看角色详情
  python create_character.py --show leona_001

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
        """
    )

    parser.add_argument("character_id", nargs="?", help="角色ID（如 leona_001, rick_001）")
    parser.add_argument("--template", "-t", choices=AVAILABLE_TEMPLATES, help="使用角色模板创建")
    parser.add_argument("--force", "-f", action="store_true", help="强制覆盖已存在的角色")
    parser.add_argument("--list-templates", action="store_true", help="列出所有可用模板")
    parser.add_argument("--list-characters", action="store_true", help="列出所有已创建的角色")
    parser.add_argument("--show", metavar="CHAR_ID", help="查看角色详情")

    args = parser.parse_args()

    # 列出模板
    if args.list_templates:
        list_templates()
        return

    # 列出角色
    if args.list_characters:
        list_characters()
        return

    # 显示角色详情
    if args.show:
        show_character(args.show)
        return

    # 创建角色
    if not args.character_id:
        parser.print_help()
        return

    if not args.template:
        print("✗ 请指定模板 --template <template_id>")
        print(f"   使用 --list-templates 查看可用模板")
        return

    create_character(args.character_id, args.template, args.force)


if __name__ == "__main__":
    main()
